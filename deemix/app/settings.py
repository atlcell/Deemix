#!/usr/bin/env python3
import os.path as path
from os import mkdir, rmdir
import json

import deemix.utils.localpaths as localpaths

settings = {}

def initSettings():
	global settings
	currentFolder = path.abspath(path.dirname(__file__))
	if not path.isdir(localpaths.getConfigFolder()):
		mkdir(localpaths.getConfigFolder())
	configFolder = localpaths.getConfigFolder()
	if not path.isfile(path.join(configFolder, 'config.json')):
		with open(path.join(configFolder, 'config.json'), 'w') as f:
			with open(path.join(currentFolder, 'default.json'), 'r') as d:
				f.write(d.read())
	with open(path.join(configFolder, 'config.json'), 'r') as configFile:
		settings = json.load(configFile)
	if settings['pathSettings']['downloadLocation'] == "":
		settings['pathSettings']['downloadLocation'] = path.join(localpaths.getHomeFolder(), 'deemix Music')
		saveSettings(settings)
	if not path.isdir(settings['pathSettings']['downloadLocation']):
		mkdir(settings['pathSettings']['downloadLocation'])
	return settings

def getSettings():
	global settings
	return settings

def saveSettings(newSettings):
	global settings
	settings = newSettings
	with open(path.join(localpaths.getConfigFolder(), 'config.json'), 'w') as configFile:
		json.dump(settings, configFile)
	return True
