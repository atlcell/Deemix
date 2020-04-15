#!/usr/bin/env python3
import os.path as path
from os import mkdir, rmdir
import json

import deemix.utils.localpaths as localpaths

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

credentials = {}
spotifyEnabled = False

def getCredentials():
	global credentials
	global spotifyEnabled
	configFolder = localpaths.getConfigFolder()
	if not path.isdir(configFolder):
		mkdir(configFolder)
	if not path.isfile(path.join(configFolder, 'authCredentials.json')):
		with open(path.join(configFolder, 'authCredentials.json'), 'w') as f:
			json.dump({'clientId': "", 'clientSecret': ""}, f, indent=2)
	with open(path.join(configFolder, 'authCredentials.json'), 'r') as credentialsFile:
		credentials = json.load(credentialsFile)
	checkCredentials()

def checkCredentials():
	global credentials
	global spotifyEnabled
	if credentials['clientId'] == "" or credentials['clientSecret'] == "":
		spotifyEnabled = False
	else:
		spotifyEnabled = True

getCredentials()
if spotifyEnabled:
	client_credentials_manager = SpotifyClientCredentials(client_id=credentials['clientId'], client_secret=credentials['clientSecret'])
	sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def _convert_playlist_structure(spotify_obj):
	if len(spotify_obj['images']):
		url = spotify_obj['images'][0]['url']
	else:
		url = "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/75x75-000000-80-0-0.jpg"
	deezer_obj = {
		'checksum': spotify_obj['snapshot_id'],
		'collaborative': spotify_obj['collaborative'],
		'creation_date': "???-??-??",
		'creator': {'id': spotify_obj['owner']['id'], 'name': spotify_obj['owner']['display_name'], 'tracklist': spotify_obj['owner']['href'], 'type': "user"},
		'description': spotify_obj['description'],
		'duration': 0,
		'fans': spotify_obj['followers']['total'],
		'id': spotify_obj['id'],
		'is_loved_track': False,
		'link': spotify_obj['external_urls']['spotify'],
		'nb_tracks': spotify_obj['tracks']['total'],
		'picture': url,
		'picture_big': url,
		'picture_medium': url,
		'picture_small': url,
		'picture_xl': url,
		'public': spotify_obj['public'],
		'share': spotify_obj['external_urls']['spotify'],
		'title': spotify_obj['name'],
		'tracklist': spotify_obj['tracks']['href'],
		'type': "playlist"
	}
	return deezer_obj

def get_trackid_spotify(dz, track_id, fallbackSearch, spotifyTrack=None):
	global spotifyEnabled
	if not spotifyEnabled:
		return "Not Enabled"
	if not spotifyTrack:
		spotify_track = sp.track(track_id)
	else:
		spotify_track = spotifyTrack
	dz_track = 0
	if 'external_ids' in spotify_track and 'isrc' in spotify_track['external_ids']:
		try:
			dz_track = dz.get_track_by_ISRC(spotify_track['external_ids']['isrc'])
			dz_track = dz_track['id'] if 'id' in dz_track else 0
		except:
			dz_track = dz.get_track_from_metadata(spotify_track['artists'][0]['name'], spotify_track['name'], spotify_track['album']['name']) if fallbackSearch else 0
	elif fallbackSearch:
		dz_track = dz.get_track_from_metadata(spotify_track['artists'][0]['name'], spotify_track['name'], spotify_track['album']['name'])
	return dz_track

def get_albumid_spotify(dz, album_id):
	global spotifyEnabled
	if not spotifyEnabled:
		return "Not Enabled"
	spotify_album = sp.album(album_id)
	dz_album = 0
	if 'external_ids' in spotify_album and 'upc' in spotify_album['external_ids']:
		try:
			dz_album = dz.get_album_by_UPC(spotify_album['external_ids']['upc'])
			dz_album = dz_album['id'] if 'id' in dz_album else 0
		except:
			try:
				dz_album = dz.get_album_by_UPC(int(spotify_album['external_ids']['upc']))
				dz_album = dz_album['id'] if 'id' in dz_album else 0
			except:
				dz_album = 0
	return dz_album

def convert_spotify_playlist(dz, playlist_id, settings):
	global spotifyEnabled
	if not spotifyEnabled:
		return "Not Enabled"
	spotify_playlist = sp.playlist(playlist_id)
	result = {
		'title': spotify_playlist['name'],
		'artist': spotify_playlist['owner']['display_name'],
		'size': spotify_playlist['tracks']['total'],
		'downloaded': 0,
		'failed': 0,
		'progress': 0,
		'type': 'spotify_playlist',
		'settings': settings or {},
		'id': playlist_id
	}
	if len(spotify_playlist['images']):
		result['cover'] = spotify_playlist['images'][0]['url']
	else:
		result['cover'] = "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/75x75-000000-80-0-0.jpg"
	playlistAPI = _convert_playlist_structure(spotify_playlist)
	tracklist = spotify_playlist['tracks']['items']
	result['collection'] = []
	while spotify_playlist['tracks']['next']:
		spotify_playlist['tracks'] = sp.next(spotify_playlist['tracks'])
		tracklist += spotify_playlist['tracks']['items']
	totalSize = len(tracklist)
	for pos, track in enumerate(tracklist, start=1):
		trackID = get_trackid_spotify(dz, 0, settings['fallbackSearch'], track['track'])
		if trackID == 0:
			deezerTrack = {
				'SNG_ID': 0,
				'SNG_TITLE': track['track']['name'],
				'DURATION': 0,
				'MD5_ORIGIN': 0,
				'MEDIA_VERSION': 0,
				'FILESIZE': 0,
				'ALB_TITLE': track['track']['album']['name'],
				'ALB_PICTURE': "",
				'ART_ID': 0,
				'ART_NAME': track['track']['artists'][0]['name']
			}
		else:
			deezerTrack = dz.get_track_gw(trackID)
		deezerTrack['_EXTRA_PLAYLIST'] = playlistAPI
		deezerTrack['POSITION'] = pos
		deezerTrack['SIZE'] = totalSize
		deezerTrack['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
		result['collection'].append(deezerTrack)
	return result
