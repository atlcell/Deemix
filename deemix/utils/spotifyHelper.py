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

def get_trackid_spotify(dz, track_id, fallbackSearch):
	global spotifyEnabled
	if not spotifyEnabled:
		return "Not Enabled"
	spotify_track = sp.track(track_id)
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

def convert_spotify_playlist(dz, playlist_id):
	global spotifyEnabled
	if not spotifyEnabled:
		return "Not Enabled"
	spotify_playlist = sp.playlist(playlist_id)
	print(spotify_playlist)
