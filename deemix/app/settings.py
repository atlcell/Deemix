#!/usr/bin/env python3
import json
import os.path as path
from os import makedirs, listdir, remove
from deemix import __version__ as deemixVersion
import random
import string
import logging
import datetime
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

import deemix.utils.localpaths as localpaths

settings = {}
defaultSettings = {}
configDir = ""

def initSettings(localFolder = False, configFolder = None):
    global settings
    global defaultSettings
    global configDir
    currentFolder = path.abspath(path.dirname(__file__))
    if not configFolder:
        configFolder = localpaths.getConfigFolder()
    configDir = configFolder
    makedirs(configFolder, exist_ok=True)
    with open(path.join(currentFolder, 'default.json'), 'r') as d:
        defaultSettings = json.load(d)
        defaultSettings['downloadLocation'] = path.join(localpaths.getHomeFolder(), 'deemix Music')
    if not path.isfile(path.join(configFolder, 'config.json')):
        with open(path.join(configFolder, 'config.json'), 'w') as f:
            json.dump(defaultSettings, f, indent=2)
    with open(path.join(configFolder, 'config.json'), 'r') as configFile:
        settings = json.load(configFile)
    settingsCheck()

    if localFolder:
        settings['downloadLocation'] = randomString(12)
        logger.info("Using a local download folder: "+settings['downloadLocation'])
    elif settings['downloadLocation'] == "":
        settings['downloadLocation'] = path.join(localpaths.getHomeFolder(), 'deemix Music')
        saveSettings(settings)
    makedirs(settings['downloadLocation'], exist_ok=True)

    # logfiles
    # logfile name
    logspath = path.join(configFolder, 'logs')
    now = datetime.datetime.now()
    logfile = now.strftime("%Y-%m-%d_%H%M%S")+".log"
    makedirs(logspath, exist_ok=True)
    # add handler for logfile
    fh = logging.FileHandler(path.join(logspath, logfile))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] %(message)s'))
    logger.addHandler(fh)
    logger.info(f"{platform.platform(True, True)} - Python {platform.python_version()}, deemix {deemixVersion}")
    #delete old logfiles
    logslist = listdir(logspath)
    logslist.sort()
    if len(logslist)>5:
        for i in range(len(logslist)-5):
            remove(path.join(logspath, logslist[i]))

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
    with open(path.join(configDir, 'config.json'), 'w') as configFile:
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


def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))
