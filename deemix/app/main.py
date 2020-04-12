import deemix.utils.localpaths as localpaths
from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads
from deemix.app.settings import initSettings
from os import system as execute
import os.path as path
from os import mkdir, rmdir

settings = {}

def getUser(dz):
	return dz.user

def initialize():
	global settings
	settings = initSettings()
	return {'settings': settings}

def shutdown(socket=None):
	print(getQueue())
	cancelAllDownloads(socket)
	if socket:
		socket.emit("toast", {'msg': "Server is closed."})

def mainSearch(dz, term):
	return dz.search_main_gw(term)

def search(dz, term, type, start, nb):
	return dz.search_gw(term, type, start, nb)

def addToQueue_link(dz, url, bitrate=None, socket=None):
	return addToQueue(dz, url, settings, bitrate, socket)

def removeFromQueue_link(uuid, socket=None):
	removeFromQueue(uuid, socket)

def downloadLink(url, bitrate=None):
	if settings['executeCommand'] != "":
		execute(settings['executeCommand'].replace("%folder%", folder))
