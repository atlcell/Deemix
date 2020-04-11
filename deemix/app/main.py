from deemix.api.deezer import Deezer
import deemix.utils.localpaths as localpaths
from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads
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

def shutdown(socket=None):
	print(getQueue())
	cancelAllDownloads(socket)
	if socket:
		socket.emit("toast", {'msg': "Server is closed."})

def mainSearch(term):
	return dz.search_main_gw(term)

def search(term, type, start, nb):
	return dz.search_gw(term, type, start, nb)

def addToQueue_link(url, bitrate=None, socket=None):
	addToQueue(dz, url, settings, bitrate, socket)

def removeFromQueue_link(uuid, socket=None):
	removeFromQueue(uuid, socket)

def downloadLink(url, bitrate=None):
	if settings['executeCommand'] != "":
		execute(settings['executeCommand'].replace("%folder%", folder))
