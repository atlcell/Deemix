#!/usr/bin/env python3
import json
import os.path as path
from os import mkdir

import deemix.utils.localpaths as localpaths

settings = {}
defaultSettings = {}


def initSettings():
    global settings
    global defaultSettings
    currentFolder = path.abspath(path.dirname(__file__))
    configFolder = localpaths.getConfigFolder()
    if not path.isdir(configFolder):
        mkdir(configFolder)
    with open(path.join(currentFolder, 'default.json'), 'r') as d:
        defaultSettings = json.load(d)
        defaultSettings['downloadLocation'] = path.join(localpaths.getHomeFolder(), 'deemix Music')
    if not path.isfile(path.join(configFolder, 'config.json')):
        with open(path.join(configFolder, 'config.json'), 'w') as f:
            json.dump(defaultSettings, f, indent=2)
    with open(path.join(configFolder, 'config.json'), 'r') as configFile:
        settings = json.load(configFile)
    settingsCheck()
    if settings['downloadLocation'] == "":
        settings['downloadLocation'] = path.join(localpaths.getHomeFolder(), 'deemix Music')
        saveSettings(settings)
    if not path.isdir(settings['downloadLocation']):
        mkdir(settings['downloadLocation'])
    return settings


def getSettings():
    global settings
    return settings


def getDefaultSettings():
    global defaultSettings
    return defaultSettings


def saveSettings(newSettings):
    global settings
    settings = newSettings
    with open(path.join(localpaths.getConfigFolder(), 'config.json'), 'w') as configFile:
        json.dump(settings, configFile, indent=2)
    return True


def settingsCheck():
    global settings
    global defaultSettings
    changes = 0
    for x in defaultSettings:
        if not x in settings or type(settings[x]) != type(defaultSettings[x]):
            settings[x] = defaultSettings[x]
            changes += 1
    for x in defaultSettings['tags']:
        if not x in settings['tags'] or type(settings['tags'][x]) != type(defaultSettings['tags'][x]):
            settings['tags'][x] = defaultSettings['tags'][x]
            changes += 1
    if changes > 0:
        saveSettings(settings)
