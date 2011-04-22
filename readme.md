# Plex metadata agent for Cine-Passion DB

This is a metadata agent for [Plex](http://plexapp.com) to use the CinŽ-Passion scrapper from [passion-xbmc.org](http://passion-xbmc.org/).
You need a valid account and be a donator to use it.

## Installation

Ths metadata agent is available in the Plex Online Store under section > More... > Metadata Agenst.
To install it manually for testing purpose (don't forget to edit info.plist file and assign to "1" PlexPluginDevMode key), you can clone this repository and copy the CinePassion.bundle to your `~/Library/Application Support/Plex Media Server/Plug-ins` folder.

## Todo

This can be found on the [Github issue tracker](https://github.com/botho/CinePassion.bundle/issues).

## Bugs

Please report them on the [Github issue tracker](https://github.com/botho/CinePassion.bundle/issues) for this project.

If you have a bug to report, please include the following information:

* **Version information for Plex and CinePassion.bundle.**
* logs message.

Logs can be found in the `~/Library/Logs/PMS Plugin Logs/com.plexapp.agents.cinepassion.log` files.
Better, you should use the [Plex Log Catcher](https://github.com/botho/CinePassion.bundle/wiki/Plex-Log-Catcher)

You may also fork this project on Github and send me a pull request.