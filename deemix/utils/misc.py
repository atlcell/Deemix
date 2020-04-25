#!/usr/bin/env python3
import re


def getBitrateInt(txt):
    txt = str(txt)
    if txt in ['flac', 'lossless', '9']:
        return 9
    elif txt in ['mp3', '320', '3']:
        return 3
    elif txt in ['128', '1']:
        return 1
    elif txt in ['360', '360_hq', '15']:
        return 15
    elif txt in ['360_mq', '14']:
        return 14
    elif txt in ['360_lq', '13']:
        return 13
    else:
        return None


def changeCase(string, type):
    if type == "lower":
        return string.lower()
    elif type == "upper":
        return string.upper()
    elif type == "start":
        string = string.split(" ")
        res = []
        for index, value in enumerate(string):
            res.append(value[0].upper() + value[1:].lower())
        res = " ".join(res)
        return res
    elif type == "sentence":
        res = string[0].upper() + string[1:].lower()
        return res
    else:
        return string


def getIDFromLink(link, type):
    if '?' in link:
        link = link[:link.find('?')]
    if link.endswith("/"):
        link = link[:-1]

    if link.startswith("http") and 'open.spotify.com/' in link:
        if type == "spotifyplaylist":
            return link[link.find("/playlist/") + 10:]
        if type == "spotifytrack":
            return link[link.find("/track/") + 7:]
        if type == "spotifyalbum":
            return link[link.find("/album/") + 7:]
    elif link.startswith("spotify:"):
        if type == "spotifyplaylist":
            return link[link.find("playlist:") + 9:]
        if type == "spotifytrack":
            return link[link.find("track:") + 6:]
        if type == "spotifyalbum":
            return link[link.find("album:") + 6:]
    elif type == "artisttop":
        return re.search(r"\/artist\/(\d+)\/top_track", link)[1]
    else:
        return link[link.rfind("/") + 1:]


def getTypeFromLink(link):
    type = ''
    if 'spotify' in link:
        type = 'spotify'
        if 'playlist' in link:
            type += 'playlist'
        elif 'track' in link:
            type += 'track'
        elif 'album' in link:
            type += 'album'
    elif 'deezer' in link:
        if '/track' in link:
            type = 'track'
        elif '/playlist' in link:
            type = 'playlist'
        elif '/album' in link:
            type = 'album'
        elif re.search("\/artist\/(\d+)\/top_track", link):
            type = 'artisttop'
        elif '/artist' in link:
            type = 'artist'
    return type


def isValidLink(text):
    if text.lower().startswith("http"):
        if "deezer.com" in text.lower() or "open.spotify.com" in text.lower():
            return True
    elif text.lower().startswith("spotify:"):
        return True
    return False
