#!/usr/bin/env python3
import re

def getBitrateInt(txt):
	txt = str(txt)
	if txt in ['flac', 'lossless', '9']:
		return 9
	elif txt in ['mp3', '320', '3']:
		return 3
	elif txt in ['128']:
		return 1
	else:
		return None

def getIDFromLink(link, type):
	if '?' in link:
		link = link[:link.find('?')]

	if link.startswith("http") and 'open.spotify.com/' in link:
		if type == "spotifyplaylist":
			return link[link.find("/playlist/") + 10]
		if type == "spotifytrack":
			return link[link.find("/track/") + 7]
		if type == "spotifyalbum":
			return link[link.find("/album/") + 7]
	elif link.startswith("spotify:"):
		if type == "spotifyplaylist":
			return link[link.find("playlist:") + 9]
		if type == "spotifytrack":
			return link[link.find("track:") + 6]
		if type == "spotifyalbum":
			return link[link.find("album:") + 6]
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
