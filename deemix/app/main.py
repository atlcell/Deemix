from deemix.api.deezer import Deezer
import deemix.utils.localpaths as localpaths
from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt, isValidLink
from deemix.app.downloader import download_track, download_album, download_playlist, download_artist, download_spotifytrack, download_spotifyalbum
from deemix.app.settings import initSettings
from os import system as execute
import os.path as path
from os import mkdir, rmdir

dz = Deezer()
settings = {}

def requestValidArl():
	while True:
		arl = input("Paste here your arl:")
		if dz.login_via_arl(arl):
			break
	return arl

def login():
	configFolder = localpaths.getConfigFolder()
	if not path.isdir(configFolder):
		mkdir(configFolder)
	if path.isfile(path.join(configFolder, '.arl')):
		with open(path.join(configFolder, '.arl'), 'r') as f:
			arl = f.read()
		if not dz.login_via_arl(arl):
			arl = requestValidArl()
	else:
		arl = requestValidArl()
	with open(path.join(configFolder, '.arl'), 'w') as f:
		f.write(arl)

def initialize():
	global settings
	settings = initSettings()
	login()
	return True

def search(term, type):
	result = dz.search(term, type)
	print(result)
	return result

def mainSearch(term):
	if isValidLink(term):
		downloadLink(term)
		return {"message": "Downloaded!"}
	return dz.search_gw(term)

def downloadLink(url, bitrate=None):
	global settings
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
	elif type == "spotifytrack":
		folder = download_spotifytrack(dz, id, settings, forcedBitrate)
	elif type == "spotifyalbum":
		folder = download_spotifyalbum(dz, id, settings, forcedBitrate)
	else:
		print("URL not supported yet")
		return None
	if settings['executeCommand'] != "":
		execute(settings['executeCommand'].replace("%folder%", folder))
