#!/usr/bin/env python3
from deemix.api.deezer import Deezer, APIError
from deemix.utils.taggers import tagID3, tagFLAC
import os.path
from urllib.error import HTTPError

dz = Deezer()

extensions = {
	9: '.flac',
	3: '.mp3',
	1: '.mp3',
	8: '.mp3',
	15: '.mp4',
	14: '.mp4',
	13: '.mp4'
}

def parseEssentialTrackData(track, trackAPI):
	track['id'] = trackAPI['SNG_ID']
	track['duration'] = trackAPI['DURATION']
	track['MD5'] = trackAPI['MD5_ORIGIN']
	track['mediaVersion'] = trackAPI['MEDIA_VERSION']
	if 'FALLBACK' in trackAPI:
		track['fallbackId'] = trackAPI['FALLBACK']['SNG_ID']
	else:
		track['fallbackId'] = 0
	track['filesize'] = {}
	track['filesize']['default'] = int(trackAPI['FILESIZE']) if 'FILESIZE' in trackAPI else None
	track['filesize']['mp3_128'] = int(trackAPI['FILESIZE_MP3_128']) if 'FILESIZE_MP3_128' in trackAPI else None
	track['filesize']['mp3_320'] = int(trackAPI['FILESIZE_MP3_320']) if 'FILESIZE_MP3_320' in trackAPI else None
	track['filesize']['flac'] = int(trackAPI['FILESIZE_FLAC']) if 'FILESIZE_FLAC' in trackAPI else None
	track['filesize']['mp4_ra1'] = int(trackAPI['FILESIZE_MP4_RA1']) if 'FILESIZE_MP4_RA1' in trackAPI else None
	track['filesize']['mp4_ra2'] = int(trackAPI['FILESIZE_MP4_RA2']) if 'FILESIZE_MP4_RA2' in trackAPI else None
	track['filesize']['mp4_ra3'] = int(trackAPI['FILESIZE_MP4_RA3']) if 'FILESIZE_MP4_RA3' in trackAPI else None

	return track

def getTrackData(trackAPI):
	if not 'MD5_ORIGIN' in trackAPI:
		trackAPI['MD5_ORIGIN'] = dz.get_track_md5(trackAPI['SNG_ID'])

	track = {}
	track['title'] = trackAPI['SNG_TITLE']
	if trackAPI['VERSION']:
		track['title'] += " " + trackAPI['VERSION']

	track = parseEssentialTrackData(track, trackAPI)

	if int(track['id']) < 0:
		track['filesize'] = trackAPI['FILESIZE']
		track['album'] = {}
		track['album']['id'] = 0
		track['album']['title'] = trackAPI['ALB_TITLE']
		if 'ALB_PICTURE' in trackAPI:
			track['album']['pic'] = trackAPI['ALB_PICTURE']
		track['mainArtist'] = {}
		track['mainArtist']['id'] = 0
		track['mainArtist']['name'] = trackAPI['ART_NAME']
		track['artistArray'] = [trackAPI['ART_NAME']]
		track['date'] = {
			'day': 0,
			'month': 0,
			'year': 0
		}
		track['localTrack'] = True
		return track

	if 'DISK_NUMBER' in trackAPI:
		track['discNumber'] = trackAPI['DISK_NUMBER']
	if 'EXPLICIT_LYRICS' in trackAPI:
		track['explicit'] = trackAPI['EXPLICIT_LYRICS'] != "0"
	if 'COPYRIGHT' in trackAPI:
		track['copyright'] = trackAPI['COPYRIGHT']
	track['replayGain'] = "{0:.2f} dB".format((float(trackAPI['GAIN']) + 18.4) * -1)
	track['ISRC'] = trackAPI['ISRC']
	track['trackNumber'] = trackAPI['TRACK_NUMBER']
	track['contributors'] = trackAPI['SNG_CONTRIBUTORS']

	track['lyrics'] = {}
	if 'LYRICS_ID' in trackAPI:
		track['lyrics']['id'] = trackAPI['LYRICS_ID']
	if "LYRICS" in trackAPI:
		if "LYRICS_TEXT" in trackAPI["LYRICS"]:
			track['lyrics']['unsync'] = trackAPI["LYRICS"]["LYRICS_TEXT"]
		if "LYRICS_SYNC_JSON" in trackAPI["LYRICS"]:
			track['lyrics']['sync'] = ""
			for i in range(len(trackAPI["LYRICS"]["LYRICS_SYNC_JSON"])):
				if "lrc_timestamp" in trackAPI["LYRICS"]["LYRICS_SYNC_JSON"][i]:
					track['lyrics']['sync'] += trackAPI["LYRICS"]["LYRICS_SYNC_JSON"][i]["lrc_timestamp"] + \
											   trackAPI["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"] + "\r\n"
				elif i + 1 < len(trackAPI["LYRICS"]["LYRICS_SYNC_JSON"]):
					track['lyrics']['sync'] += trackAPI["LYRICS"]["LYRICS_SYNC_JSON"][i + 1]["lrc_timestamp"] + \
											   trackAPI["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"] + "\r\n"

	track['mainArtist'] = {}
	track['mainArtist']['id'] = trackAPI['ART_ID']
	track['mainArtist']['name'] = trackAPI['ART_NAME']
	if 'ART_PICTURE' in trackAPI:
		track['mainArtist']['pic'] = trackAPI['ART_PICTURE']

	if 'PHYSICAL_RELEASE_DATE' in trackAPI:
		track['date'] = {
			'day': trackAPI["PHYSICAL_RELEASE_DATE"][8:10],
			'month': trackAPI["PHYSICAL_RELEASE_DATE"][5:7],
			'year': trackAPI["PHYSICAL_RELEASE_DATE"][0:4]
		}

	track['album'] = {}
	track['album']['id'] = trackAPI['ALB_ID']
	track['album']['title'] = trackAPI['ALB_TITLE']
	if 'ALB_PICTURE' in trackAPI:
		track['album']['pic'] = trackAPI['ALB_PICTURE']

	albumAPI = None
	albumAPI2 = None
	try:
		if 'ALBUM_EXTRA' in trackAPI:
			albumAPI = trackAPI['ALBUM_EXTRA']
		else:
			albumAPI = dz.get_album(track['album']['id'])
		track['album']['artist'] = {
			'id': albumAPI['artist']['id'],
			'name': albumAPI['artist']['name'],
			'pic': albumAPI['artist']['picture_small'][46:-24]
		}
		track['album']['trackTotal'] = albumAPI['nb_tracks']
		track['album']['recordType'] = albumAPI['record_type']
		track['album']['barcode'] = albumAPI['upc'] if 'upc' in albumAPI else "Unknown"
		track['album']['label'] = albumAPI['label'] if 'label' in albumAPI else "Unknown"
		if not 'pic' in track['album']:
			track['album']['pic'] = albumAPI['cover_small'][43:-24]
		if 'release_date' in albumAPI and not 'date' in track:
			track['date'] = {
				'day': albumAPI["release_date"][8:10],
				'month': albumAPI["release_date"][5:7],
				'year': albumAPI["release_date"][0:4]
			}
		track['album']['discTotal'] = albumAPI['nb_disk'] if 'nb_disk' in albumAPI else None
		track['copyright'] = albumAPI['copyright'] if 'copyright' in albumAPI else None
		track['album']['genre'] = []
		if 'genres' in albumAPI and 'data' in albumAPI['genres'] and len(albumAPI['genres']['data']) > 0:
			for genre in albumAPI['genres']['data']:
				track['album']['genre'].append(genre['name'])
	except APIError:
		albumAPI2 = dz.get_album_gw(track['album']['id'])
		track['album']['artist'] = {
			'id': albumAPI2['ART_ID'],
			'name': albumAPI2['ART_NAME']
		}
		track['album']['trackTotal'] = albumAPI2['NUMBER_TRACK']
		track['album']['discTotal'] = albumAPI2['NUMBER_DISK']
		track['album']['recordType'] = trackAPI['TYPE']
		track['album']['barcode'] = "Unknown"
		track['album']['label'] = albumAPI2['LABEL_NAME'] if 'LABEL_NAME' in albumAPI2 else "Unknown"
		if not 'pic' in track['album']:
			track['album']['pic'] = albumAPI2['ALB_PICTURE']
		if 'PHYSICAL_RELEASE_DATE' in albumAPI2 and not 'date' in track:
			track['date'] = {
				'day': albumAPI2["PHYSICAL_RELEASE_DATE"][8:10],
				'month': albumAPI2["PHYSICAL_RELEASE_DATE"][5:7],
				'year': albumAPI2["PHYSICAL_RELEASE_DATE"][0:4]
			}
		track['album']['genre'] = []

	trackAPI2 = dz.get_track(track['id'])
	track['bpm'] = trackAPI2['bpm']
	if not 'replayGain' in track:
		track['replayGain'] = "{0:.2f} dB".format((float(trackAPI2['gain']) + 18.4) * -1)
	if not 'explicit' in track:
		track['explicit'] = trackAPI2['explicit_lyrics']
	if not 'discNumber' in track:
		track['discNumber'] = trackAPI2['disk_number']
	track['artist'] = {}
	track['artists'] = []
	for artist in trackAPI2['contributors']:
		track['artists'].append(artist['name'])
		if not artist['role'] in track['artist']:
			track['artist'][artist['role']] = []
		track['artist'][artist['role']].append(artist['name'])

	if not 'discTotal' in track['album'] or not track['album']['discTotal']:
		if not albumAPI2:
			albumAPI2 = dz.get_album_gw(track['album']['id'])
		track['album']['discTotal'] = albumAPI2['NUMBER_DISK']
	if not 'copyright' in track or not track['copyright']:
		if not albumAPI2:
			albumAPI2 = dz.get_album_gw(track['album']['id'])
		track['copyright'] = albumAPI2['COPYRIGHT']
	return track


def downloadTrackObj(trackAPI, settings, overwriteBitrate=False, extraTrack=None):
	# Get the metadata
	if extraTrack:
		track = extraTrack
	else:
		track = getTrackData(trackAPI)
	print('Downloading: {} - {}'.format(track['mainArtist']['name'], track['title']))

	# Get the selected bitrate
	if overwriteBitrate:
		bitrate = overwriteBitrate
	else:
		bitrate = settings['maxBitrate']
	bitrateFound = False;
	if int(bitrate) == 9:
		track['selectedFormat'] = 9
		track['selectedFilesize'] = track['filesize']['flac']
		if track['filesize']['flac'] > 0:
			bitrateFound = True
		else:
			bitrateFound = False
			bitrate = 3
	if int(bitrate) == 3:
		track['selectedFormat'] = 3
		track['selectedFilesize'] = track['filesize']['mp3_320']
		if track['filesize']['mp3_320'] > 0:
			bitrateFound = True
		else:
			bitrateFound = False
			bitrate = 1
	if int(bitrate) == 1:
		track['selectedFormat'] = 3
		track['selectedFilesize'] = track['filesize']['mp3_320']
		if track['filesize']['mp3_320'] > 0:
			bitrateFound = True
		else:
			bitrateFound = False
	if not bitrateFound:
		track['selectedFormat'] = 8
		track['selectedFilesize'] = track['filesize']['default']
	track['album']['bitrate'] = track['selectedFormat']
	track['album']['picUrl'] = "http://e-cdn-images.deezer.com/images/cover/{}/{}x{}-000000-80-0-0.jpg".format(track['album']['pic'], settings['embeddedArtworkSize'], settings['embeddedArtworkSize'])

	# Create the filename
	filename = "{artist} - {title}".format(title=track['title'], artist=track['mainArtist']['name']) + extensions[
		track['selectedFormat']]
	writepath = os.path.join(settings['downloadLocation'], filename)

	track['downloadUrl'] = dz.get_track_stream_url(track['id'], track['MD5'], track['mediaVersion'],
												   track['selectedFormat'])
	with open(writepath, 'wb') as stream:
		try:
			dz.stream_track(track['id'], track['downloadUrl'], stream)
		except HTTPError:
			if track['selectedFormat'] == 9:
				print("Track not available in flac, trying mp3")
				track['filesize']['flac'] = 0
				return downloadTrackObj(trackAPI, settings, extraTrack=track)
			elif track['fallbackId'] != 0:
				print("Track not available, using fallback id")
				trackNew = dz.get_track_gw(track['fallbackId'])
				if not 'MD5_ORIGIN' in trackNew:
					trackNew['MD5_ORIGIN'] = dz.get_track_md5(trackNew['SNG_ID'])
				track = parseEssentialTrackData(track, trackNew)
				return downloadTrackObj(trackNew, settings, extraTrack=track)
			else:
				print("ERROR: Track not available on deezer's servers!")
				return False
	if track['selectedFormat'] in [3, 1, 8]:
		tagID3(writepath, track, settings['tags'])
	elif track['selectedFormat'] == 9:
		tagFLAC(writepath, track, settings['tags'])
	print("Done!")
	return True

def download_track(id, settings, overwriteBitrate=False):
	trackAPI = dz.get_track_gw(id)
	downloadTrackObj(trackAPI, settings, overwriteBitrate)

def download_album(id, settings, overwriteBitrate=False):
	albumAPI = dz.get_album(id)
	albumAPI2 = dz.get_album_gw(id)
	albumAPI['nb_disk'] = albumAPI2['NUMBER_DISK']
	albumAPI['copyright'] = albumAPI2['COPYRIGHT']
	if albumAPI['nb_tracks'] == 1:
		trackAPI = dz.get_track_gw(albumAPI['tracks']['data'][0]['id'])
		trackAPI['ALBUM_EXTRA'] = albumAPI
		downloadTrackObj(trackAPI, settings, overwriteBitrate)
	else:
		tracksArray = dz.get_album_tracks_gw(id)
		for trackAPI in tracksArray:
			trackAPI['ALBUM_EXTRA'] = albumAPI
			downloadTrackObj(trackAPI, settings, overwriteBitrate)

def download_playlist(id, settings, overwriteBitrate=False):
	playlistAPI = dz.get_playlist(id)
	playlistTracksAPI = dz.get_playlist_tracks_gw(id)
	for trackAPI in playlistTracksAPI:
		trackAPI['PLAYLIST_EXTRA'] = playlistAPI
		downloadTrackObj(trackAPI, settings, overwriteBitrate)
