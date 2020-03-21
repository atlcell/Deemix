#!/usr/bin/env python3
from deemix.api.deezer import Deezer
from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt
from deemix.app.downloader import download_track, download_album, download_playlist, download_artist
from os import system as execute

dz = Deezer()

def downloadLink(url, settings, bitrate=None):
	forcedBitrate = getBitrateInt(bitrate)
	type = getTypeFromLink(url)
	id = getIDFromLink(url, type)
	folder = settings['downloadLocation']
	if type == None or id == None:
		print("URL not recognized")
	if type == "track":
		folder = download_track(dz, id, settings, forcedBitrate)
	elif type == "album":
		folder = download_album(dz, id, settings, forcedBitrate)
	elif type == "playlist":
		folder = download_playlist(dz, id, settings, forcedBitrate)
	elif type == "artist":
		download_artist(dz, id, settings, forcedBitrate)
	else:
		print("URL not supported yet")
		return None
	if settings['executeCommand'] != "":
		execute(settings['executeCommand'].replace("%folder%", folder))
