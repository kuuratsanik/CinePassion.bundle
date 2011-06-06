#
# Plex Movie Metadata Agent using Ciné-passion database (French communauty)
# V1.6 and older By oncleben31 (http://oncleben31.cc) - 2011
# V1.7 and above By Botho since OncleBen decided to stop this developpement (https://github.com/botho/) - 2011
#

#TODO : Essayer de faire un Agent secondaire pour IMDB juste pour retrouver les informations de type text
#TODO : Améliorer la gestion du quota pour éviter les effets de cache


import datetime, unicodedata, re, urllib2, base64, sha

CP_AGENT_VER = 'v1.9.3'
CP_API_KEY = '8a7129b8f3edd95b7d969dfc2c8e9d9d'
# WARNING : If you want to use the Ciné-Passion DDB for your project, don't use this key but 
# ask a free one on this page : http://passion-xbmc.org/demande-clef-api-api-key-request/

CP_API_URL = 'http://passion-xbmc.org/scraper/API/1/'
CP_API_SEARCH = 'Movie.Search/%s/%s/Title/%s/XML/'
CP_API_INFO = 'Movie.GetInfo/%s/%s/ID/%s/XML/'
CP_API_QUOTA = 'User.GetQuota/%s/%s/%s/XML/'

GOOGLE_JSON_URL = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&userip=%s&rsz=large&q=%s'
BING_JSON_URL   = 'http://api.bing.net/json.aspx?AppId=BAFE92EAA23CD237BCDAA5AB39137036739F7357&Version=2.2&Query=%s&Sources=web&Web.Count=8&JsonType=raw'

CP_COEFF_YEAR = 3
CP_COEFF_TITLE = 2
CP_DATE_PENALITY = 25
CP_RESULT_POS_PENALITY = 1

CP_CACHETIME_CP_SEARCH = CACHE_1DAY
CP_CACHETIME_CP_FANART = CACHE_1MONTH

#default Plex UA : Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_4_11; fr-fr; rv:1.9.2.8) Gecko/20100805 Firefox/3.6.8
CP_AGENT_UA = 'Plex Metadata Agent Cine-Passion %s (Plex Media Server version %s)'
CP_MIN_PLEX_VERSION = '0923'
CP_RATING_SOURCE = ''


def Start():
	HTTP.CacheTime = CACHE_1DAY
	global isPlexVersionOK
	global currentPlexVersion
	isPlexVersionOK = False
	Log("[cine-passion Agent] Ciné-Passion Metadata Agent version %s started" %(CP_AGENT_VER))

	#Verify if Plex version is the good one (since 0.9.2.3, Plex don't refresh anymore every two weeks to preserve scraper database)
	versionURL = 'http://127.0.0.1:32400'
	try:
		XMLresult = XML.ElementFromURL(versionURL, cacheTime=1)
		currentPlexVersion = XMLresult.xpath('/MediaContainer')[0].get('version')
		Log("[cine-passion Agent] Detected Plex Version %s" %(currentPlexVersion))
		shortPlexVersion = currentPlexVersion.split('-')[0].replace('.','')
		shortPlexVersion = int("".join(shortPlexVersion))		
		if (shortPlexVersion >= int(CP_MIN_PLEX_VERSION)):
			isPlexVersionOK = True
			Log("[cine-passion Agent] Plex Version is compatible with this Ciné-Passion Metadata Agent")
		else:
			isPlexVersionOK = False
			Log.Error("[cine-passion Agent] You need minimum Plex version (0.9.2.3) to use Ciné-Passion Agent %s. Your actual Plex version is (%s). Ciné-Passion Metadata Agent will not work." %(CP_AGENT_VER, currentPlexVersion))
	except Exception, e :
		Log.Error("[cine-passion Agent] EXCEPT0 : " + str(e))
		isPlexVersionOK = False

	#Setting specific user agent for cine-passion scrapper (for statistics usage...)
	HTTP.Headers['User-agent'] = CP_AGENT_UA %(CP_AGENT_VER, currentPlexVersion)
	#resultUA = HTTP.Request('http://whatsmyuseragent.com/', cacheTime=1).content


class CinepassionAgent(Agent.Movies):
  name = 'Ciné-Passion'
  primary_provider = True
  languages = [Locale.Language.French, Locale.Language.English]
  accepts_from = ['com.plexapp.agents.localmedia', 'com.plexapp.agents.opensubtitles']

  def search(self, results, media, lang):
  
	if (isPlexVersionOK == True):
		#temporary special case for Disney's
		try: 
			m = re.match('N° [0-9]* ([0-9]*) Walt Disney (.*)$', media.name)
			if m:
			  new_name, new_yearString = (m.group(2), m.group(1))
			  Log.Debug('[cine-passion Agent] new_name : ' + new_name + ' | new_year : ' + new_yearString)
			  media.name = new_name
			  media.year = new_yearString
		except:
			Log.Error("[cine-passion Agent] Ciné-Passion Agent has return an error when managing the Disney Case")

	  	#Launch search on media name using name without accents.
		searchURL = CP_API_URL + CP_API_SEARCH % (base64.b64encode(Prefs["pref_user_login"]), sha.new(Prefs["pref_user_login"].lower()+Prefs["pref_user_passwd"]).hexdigest(), lang) + CP_API_KEY + '/' + String.Quote(self.stripAccents(media.name.encode('utf-8')), usePlus = True)
		try:
			searchXMLresult = XML.ElementFromURL(searchURL, cacheTime=CP_CACHETIME_CP_SEARCH)

			#Test if DDB have return an error
			hasError = self.checkErrors(searchXMLresult, media.name.encode('utf-8'))

		except Ex.HTTPError, e:
			Log.Error("[cine-passion Agent] HTTP return code is different of 200 : " + e)
		except Exception, e :
			Log.Error("[cine-passion Agent] EXCEPT1 : " + str(e))
			hasError = True
			Log.Error("[cine-passion Agent] Ciné-Passion Agent has return an unkown error wile retrieving search result for %s" %(media.name.encode('utf-8')))

		if (hasError ==  False):
			#Analyse the results
			self.scrapeXMLsearch(results, media, lang, searchXMLresult, skipCinePassion = False)
		else:
			#Analyse the results just with Google
			self.scrapeXMLsearch(results, media, lang, None, skipCinePassion = True)
	else:
		Log.Error("[cine-passion Agent] You need minimum Plex version (0.9.2.3) to use Ciné-Passion Agent %s. Your actual Plex version is (%s). Ciné-Passion Metadata Agent will not work." %(CP_AGENT_VER, currentPlexVersion))



  def update(self, metadata, media, lang):

  	if (isPlexVersionOK == True):
		try:
			#Ask for movie information
			# Cache management to avoid consuming Ciné-Passion database quotas (2011/03 : beware since scraps are not free anymore)
			pref_cache = Prefs["pref_cache"]
			if pref_cache == "1 jour/day" :
				CP_CACHETIME_CP_REQUEST = CACHE_1DAY
			elif pref_cache == "1 semaine/week":
				CP_CACHETIME_CP_REQUEST = CACHE_1WEEK
			elif pref_cache == "1 mois/month":
				CP_CACHETIME_CP_REQUEST = CACHE_1MONTH
			Log("[cine-passion Agent] requesting movie with ID (%s) with cache time set to : %s" %(metadata.id, str(CP_CACHETIME_CP_REQUEST)))
			updateXMLresult = XML.ElementFromURL(CP_API_URL + CP_API_INFO % (base64.b64encode(Prefs["pref_user_login"]), sha.new(Prefs["pref_user_login"].lower()+Prefs["pref_user_passwd"]).hexdigest(), lang) + CP_API_KEY + '/' + metadata.id, cacheTime=CP_CACHETIME_CP_REQUEST)

			#Test if DDB have return an error
			hasError = self.checkErrors(updateXMLresult, metadata.title)
		except Ex.HTTPError, e:
			Log.Error("[cine-passion Agent] HTTP return code is different of 200 : " + e)
		except Exception, e :
			Log.Error("[cine-passion Agent] EXCEPT2 : " + str(e))
			hasError = True
			if metadata.title != None:
				Log.Error("[cine-passion Agent] ERROR : Agent has return an unkown error wile retrieving information for %s" %(metadata.title))
			else:
				Log.Error("[cine-passion Agent] ERROR : Agent has return an unkown error wile retrieving information for ID (%s)" %(metadata.id))

		if (hasError == False):
			#genre
			cp_genres = updateXMLresult.findall('genres/genre')
			if cp_genres and len(cp_genres) > 0:
				metadata.genres.clear()
				for genre in cp_genres:
					if genre.text != None:
						metadata.genres.add(genre.text.strip())
						Log.Debug("[cine-passion Agent] Adding genre : %s" %(genre.text))
		
			#director
			cp_directors = updateXMLresult.findall('directors/director')
			if cp_directors and len(cp_directors) > 0:
				metadata.directors.clear()
				for director in cp_directors:
					if director.text != None:
						metadata.directors.add(director.text.strip())
						Log.Debug("[cine-passion Agent] Adding director : %s" %(director.text))
	
			#writers
			cp_writers = updateXMLresult.findall('credits/credit')
			if cp_writers and len(cp_writers) > 0:
				metadata.writers.clear()
				for writer in cp_writers:
					if writer.text != None:
						metadata.writers.add(writer.text.strip())
						Log.Debug("[cine-passion Agent] Adding writer : %s" %(writer.text))
			
			#countries
			cp_countries = updateXMLresult.findall('countries/country')
			if cp_countries and len(cp_countries) > 0:
				metadata.countries.clear()
				for country in cp_countries:
					if country.text != None:
						metadata.countries.add(country.text.strip())
						Log.Debug("[cine-passion Agent] Adding country : %s" %(country.text))
	
			#studios : Just the first one is taken. Plex didn't manage more than one
			cp_studio = updateXMLresult.findall('studios/studio')
			if cp_studio and len(cp_studio) > 0:
				if cp_studio[0].text != None:
					metadata.studio = cp_studio[0].text.strip()
					Log.Debug("[cine-passion Agent] Adding studio : %s" %(metadata.studio))
			
			#runtime
			cp_runtime = updateXMLresult.find('runtime')
			if cp_runtime != None and cp_runtime.text != None and self.IsInt(cp_runtime.text) == True:
				metadata.duration = int(cp_runtime.text.strip()) * 60 * 1000    
				Log.Debug("[cine-passion Agent] Adding duration : %s" %(str(metadata.duration)))
			
			#year and originally_available_at
			cp_year = updateXMLresult.find('year')
			if cp_year != None and cp_year.text != None and self.IsInt(cp_year.text) == True:
				metadata.year = int(cp_year.text.strip())
				#originally_available_at
				metadata.originally_available_at = Datetime.ParseDate(cp_year.text.strip()).date()
				Log.Debug("[cine-passion Agent] Adding year : %s" %(str(metadata.year)))
				Log.Debug("[cine-passion Agent] Adding originally available at : %s" %(str(metadata.originally_available_at)))
			
			#original_title
			cp_originalTitle = updateXMLresult.find('originaltitle')
			if cp_originalTitle != None and cp_originalTitle.text != None:
				metadata.original_title = cp_originalTitle.text.strip().replace('&#39;','\'')
				Log.Debug("[cine-passion Agent] Adding original title : %s" %(metadata.original_title))
			
			#title
			cp_title = updateXMLresult.find('title')
			if cp_title != None and cp_title.text != None:
				metadata.title = cp_title.text.strip().replace('&#39;','\'')
				Log.Debug("[cine-passion Agent] Adding title : %s" %(metadata.title))
			
			#title sort
			cp_title_sort = updateXMLresult.find('sorttitle')
			if cp_title_sort != None and cp_title_sort.text != None:
				metadata.title_sort = cp_title_sort.text.strip().replace('&#39;','\'')
				Log.Debug("[cine-passion Agent] Adding title sort : %s" %(metadata.title_sort))
			
			#summary
			cp_summary = updateXMLresult.find('plot')
			if cp_summary != None and cp_summary.text != None:
				metadata.summary = cp_summary.text.strip()
				Log.Debug("[cine-passion Agent] Adding summary : %s" %(metadata.summary))
			
			#trivia
			cp_information = updateXMLresult.find('information')
			if cp_information != None and cp_information.text != None:
				metadata.trivia = cp_information.text.strip()
				Log.Debug("[cine-passion Agent] Adding trivia : %s" %(metadata.trivia))
			
			#tagline tag should be ignored since there are not real tagline in Ciné-passion DDB : it's only the plot's begining
				#Pref file
				#{
				#"id":		"pref_ignore_tagline",
				#"label":	"Ignore Taglines",
				#"type":		"bool",
				#"default":	"true"
				#}
			#if Prefs["pref_ignore_tagline"] == False:
			#	cp_tagline = updateXMLresult.find('tagline')
			#	if cp_tagline != None and cp_tagline.text != None:
			#		metadata.tagline = cp_tagline.text.strip()
			#		Log.Debug("[cine-passion Agent] Adding tagline : %s" %(metadata.tagline))
			#else:
			#	metadata.tagline = ' '
			#	Log.Debug("[cine-passion Agent] Deleting tagline : %s" %(metadata.tagline))
				
			#quotes tag ignored since there are not real quotes in Ciné-passion DDB
			cp_quotes = updateXMLresult.find('quotes')
			if cp_quotes != None and cp_quotes.text != None:
				metadata.quotes = cp_quotes.text.strip()
				Log.Debug("[cine-passion Agent] Adding quotes : %s" %(metadata.quotes))

			#rating source selection done by pref pane.
			rating_source = Prefs["pref_rating_source"]
			if rating_source == "AlloCiné":
				CP_RATING_SOURCE = "allocine"
			elif rating_source == "IMDb":
				CP_RATING_SOURCE = "imdb"
			elif rating_source == "Ciné-Passion":
				CP_RATING_SOURCE = "cinepassion"
						
			cp_rating  = updateXMLresult.find("ratings/rating[@type='" + CP_RATING_SOURCE + "']")
			if cp_rating != None and cp_rating.text != None:
				metadata.rating = float(cp_rating.text.strip().replace(',','.'))
				Log.Debug("[cine-passion Agent] Adding rating : %s (source - %s)" %(str(metadata.rating), rating_source))

			#roles
			cp_roles = updateXMLresult.findall('casting/person')
			if cp_roles and len(cp_roles) > 0:
				metadata.roles.clear()
				for person in cp_roles:
					role = metadata.roles.new()
					role.role = person.get('character').strip()
					role.actor = person.get('name').strip()
					role.photo = person.get('thumb').strip()
					Log.Debug("[cine-passion Agent] Adding actor : %s (%s)" %(role.role, role.actor))
		
			#content_rating - Ciné-Passion manage France and USA ratings.
			content_rating_source = Prefs["pref_content_rating"]
			CP_content_rating = updateXMLresult.find("certifications/certification[@nation='" + content_rating_source + "']")
			if CP_content_rating != None and CP_content_rating.text != None:
				if content_rating_source == "France":
					metadata.content_rating = 'fr/' + CP_content_rating.text.strip()
				else:
					metadata.content_rating = CP_content_rating.text.strip()
				Log.Debug("[cine-passion Agent] certifications rating : %s (source - %s)"  %(metadata.content_rating, content_rating_source))				
			
			#collection
			if Prefs["pref_ignore_collection"] == False:
				cp_collection = updateXMLresult.find('saga')
				metadata.collections.clear()
				if cp_collection != None and cp_collection.text != None:
					metadata.collections.add(cp_collection.text.strip())
					Log.Debug("[cine-passion Agent] Adding collection : %s" %(cp_collection.text.strip()))

			#Posters and Fanarts
			@parallelize
			def LoopForArtsFetching():
				posters_valid_names = list()
				art_valid_names = list()
				
				images = updateXMLresult.findall("images/image[@size='preview']")
				indexImages = 1
				for image in images:
					@task
					def grapArts(metadata=metadata, image=image, indexImages=indexImages):
						thumbUrl = image.get('url')
						url = thumbUrl.replace("/preview/", "/main/")
					
						type = image.get('type')
						if (type == 'Poster'):
							try:
								#Check if main image exist
								f = urllib2.urlopen(url)
								test = f.info().gettype()
								metadata.posters[url] = Proxy.Preview(HTTP.Request(thumbUrl, cacheTime=CP_CACHETIME_CP_FANART), sort_order = indexImages)
								posters_valid_names.append(url)
							except	Exception, e :
								Log.Error("[cine-passion Agent] EXCEPT3 : " + str(e))
								Log.Error("[cine-passion Agent] ERROR when fetching Poster %s or %s" %(thumbUrl, url))
						elif (type == 'Fanart'):
							try:
								#Check if main image exist
								f = urllib2.urlopen(url)
								test = f.info().gettype()
								metadata.art[url] = Proxy.Preview(HTTP.Request(thumbUrl, cacheTime=CP_CACHETIME_CP_FANART), sort_order = indexImages)
								art_valid_names.append(url)
							except	Exception, e :
								Log.Error("[cine-passion Agent] EXCEPT4 : " + str(e))
								Log.Error("[cine-passion Agent] ERROR when fetching Fanart %s or %s" %(thumbUrl, url))
					indexImages = indexImages + 1
				
				#supress old unsued pictures
				metadata.posters.validate_keys(posters_valid_names)
				metadata.art.validate_keys(art_valid_names)
					
	else:
		Log.Error("[cine-passion Agent] You need minimum Plex version (0.9.2.3) to use Ciné-Passion Agent %s. Your actual Plex version is (%s). Ciné-Passion Metadata Agent will not work." %(CP_AGENT_VER, currentPlexVersion))

			
	### Tags not used
	#content_rating_age : not in DDB
	#banners : not in DDB
	#themes : not in DDB


  def scrapeXMLsearch(self, results, media, lang, XMLresult, skipCinePassion):
	# initialise score
	score = 99

	# Search in Ciné-Passion DDB
	if (skipCinePassion == False):
		# For any <movie> tag in XML response
		for movie in XMLresult.xpath("//movie"):
			#find movie information (id, title and year)
			id = movie.find('id').text
			name = movie.find('title').text.replace('&#39;','\'').replace('&#338;', 'Œ').replace('&amp;#338;', 'Œ') # Patch to suppress some HTML code in title.
			originalName = movie.find('originaltitle').text
			year = movie.find('year')
			if year != None and year.text != None and self.IsInt(year.text.strip()) == True:
				year = int(year.text.strip()) 
			else:
				year = None
			lang = lang

			finalScore = score - self.scoreResultPenalty(media, year, name, originalName)
			#The movie information are added to the result
			results.Append(MetadataSearchResult(id=id, name=name, year=year, lang=lang, score=finalScore))

			# First results should be more acruate.
			score = score - 1

	# Search on Google and BING to get Allociné ID (Big Thanks to IMDB Agent :-)
	if media.year:
	  searchYear = ' (' + str(media.year) + ')'
	else:
	  searchYear = ''

	normalizedName = self.stripAccents(media.name)
	GOOGLE_JSON_QUOTES = GOOGLE_JSON_URL % (self.getPublicIP(), String.Quote('"' + normalizedName + searchYear + '"', usePlus=True)) + '+site:allocine.fr/film/fichefilm_gen_cfilm'
	GOOGLE_JSON_NOQUOTES = GOOGLE_JSON_URL % (self.getPublicIP(), String.Quote(normalizedName + searchYear, usePlus=True)) + '+site:allocine.fr/film/fichefilm_gen_cfilm'
	BING_JSON = BING_JSON_URL % String.Quote(normalizedName + searchYear, usePlus=True) + '+site:allocine.fr/film'

	#Reinit classment score since CinePassion can shift good movies.
	score = 99

	for s in [GOOGLE_JSON_QUOTES, GOOGLE_JSON_NOQUOTES, BING_JSON]:
		if s == GOOGLE_JSON_QUOTES and (media.name.count(' ') == 0 or media.name.count('&') > 0 or media.name.count(' and ') > 0):
			# no reason to run this test, plus it screwed up some searches
			continue

		hasResults = False
		try:
			if s.count('bing.net') > 0:
				jsonObj = JSON.ObjectFromURL(s)['SearchResponse']['Web']
				if jsonObj['Total'] > 0:
					jsonObj = jsonObj['Results']
					hasResults = True
					urlKey = 'Url'
					titleKey = 'Title'
			elif s.count('googleapis.com') > 0:
				jsonObj = JSON.ObjectFromURL(s)
				if jsonObj['responseData'] != None:
					jsonObj = jsonObj['responseData']['results']
					if len(jsonObj) > 0:
						hasResults = True
						urlKey = 'unescapedUrl'
						titleKey = 'title'
		except Exception, e :
			Log.Error("[cine-passion Agent] EXCEPT5 " + str(e))
			Log.Error('[cine-passion Agent] ERROR when fetching ' + s)

		if hasResults :
			goodItem = 0
			for item in jsonObj:
				#Stop parsing search engin results after 3 matching.
				if goodItem > 3:
					continue

				url = item[urlKey]
				title = self.stripHTMLTags(item[titleKey])

				try: 
					m = re.match('(.*)[ ]+\(([12][0-9]{3})(/[A-Z]+)?\).*$', title)
					year = None
					if m:
					  name,yearString = (m.group(1), m.group(2))
					  if yearString != None and yearString != '' and self.IsInt(yearString) == True:
					  	year = int(yearString)

					m = re.match('http://www.allocine.fr/film/fichefilm_gen_cfilm=([0-9]*).html', url)
					if m:
						id = m.group(1)
		  			else:
						#If no id the results is not on allocine. skip it
						continue

					# No way to find original name so name is used two times.
					finalScore = score - self.scoreResultPenalty(media, year, name, name)
					results.Append(MetadataSearchResult(id =id, name=name, year=year, lang=lang, score=finalScore))

					# First results should be more acruate.
					score = score - CP_RESULT_POS_PENALITY
					goodItem = goodItem + 1

				except Exception, e :
					Log.Error("[cine-passion Agent] EXCEPT6 " + str(e))
					Log.Error("[cine-passion Agent] ERROR when parsing %s" %(url))
		
			Log.Debug("[cine-passion Agent] trouvé %s" %(str(goodItem-1)))

	# Finally, remove duplicate entries.
	results.Sort('score', descending=True)
	toWhack = []
	resultMap = {}
	for result in results:
	  if not resultMap.has_key(result.id):
	    resultMap[result.id] = True
	  else:
	    toWhack.append(result)

	for dupe in toWhack:
	  results.Remove(dupe)

	# Just for Log
	for result in results:
		Log("[cine-passion Agent] scraped results : %s | year = %s | id = %s | score = %s" %(result.name, str(result.year), result.id, str(result.score)))


  def checkQuota(self, XMLresult):
	# This function check the quota of the Ciné-passion DDB
	# For now just a Log in console. In the futur a popup warning to alert the user should be better
	try:
		hasError = False
		quota = XMLresult.find('quota')
		if quota != None:
			used = quota.get('use')
			authorized =  quota.get('authorize')
			resetDate = quota.get('reset_date')
			Log("[cine-passion Agent] : Quota : used: %s on %s | reset date: %s" %(used, authorized, resetDate))

		tagID = XMLresult.find('movie/id')
		#Double check because root element is different when quota reach.
		if tagID != None:
			if tagID.text == "-1":			
				Log("[cine-passion Agent] : WARNING : Quota reached, no more result before reset")
				hasError = True

	except Exception , e:
		Log.Error("[cine-passion Agent] EXCEPT7 : " + str(e))
		hasError = True

	return hasError


  def checkErrors(self, XMLresult, name):
	# This function check if the Ciné-passion have return an error
	try:
		hasError = False
		for i in XMLresult.findall('error'):
			Log("ERROR : Ciné-Passion API return the error when searching for %s : %s" %(name, i.text))
			hasError = True

		if hasError == False:
			#Verification du quotas
			hasError = self.checkQuota(XMLresult)

	except Exception , e:
		Log.Error("[cine-passion Agent] EXCEPT8 : " + str(e))
		hasError = True

	return hasError


  def stripAccents(self, str):
    nkfd_form = unicodedata.normalize('NFKD', unicode(str))
    only_ascii = nkfd_form.encode('ASCII', 'ignore')
    return only_ascii


  def stripHTMLTags(self, str):
	p = re.compile(r'<.*?>')
	return p.sub('', str)


  def scoreResultPenalty(self, media, year, name, originalName):
	# Penality if date is in futur
	# Penality proportional to distance between dates if available
	# Penality proportional to the Levenshtein distance between title. min of distance calculate for title and originalTitle is used.

	#Control to evaluate the result.
	scorePenalty = 0
	if year!=None and year > datetime.datetime.now().year:
		scorePenalty = CP_DATE_PENALITY

	#If there is a date in the video file name compute the difference
	if year!=None and media.year:
		scorePenalty = scorePenalty + abs(year - int(media.year)) * CP_COEFF_YEAR

	#Use String distance as penalty. Use accents
	#nameDist = Util.LevenshteinDistance(self.stripAccents(media.name.lower()), self.stripAccents(name.lower()))
	#originalNameDist = Util.LevenshteinDistance(self.stripAccents(media.name.lower()), self.stripAccents(originalName.lower()))
	nameDist = Util.LevenshteinDistance(media.name.lower(), name.lower())
	originalNameDist = Util.LevenshteinDistance(media.name.lower(), originalName.lower())
	minDist = min(nameDist, originalNameDist)
	scorePenalty = scorePenalty + minDist * CP_COEFF_TITLE
	return scorePenalty

  def IsInt(self, str):
  # Test if the given string an integer
	ret = True
	try:
		num = int(str)
	except ValueError:
		ret = False
	return ret

  def getPublicIP(self):
    ip = HTTP.Request('http://plexapp.com/ip.php').content.strip()
    return ip
