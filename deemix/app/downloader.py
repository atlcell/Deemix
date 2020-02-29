#!/usr/bin/env python3
from deemix.api.deezer import Deezer, APIError
from deemix.utils.taggers import tagID3, tagFLAC
from deemix.utils.pathtemplates import generateFilename, generateFilepath, settingsRegexAlbum, settingsRegexArtist
import os.path
from os import makedirs
from urllib.request import urlopen
from urllib.error import HTTPError
from tempfile import gettempdir

dz = Deezer()
TEMPDIR = os.path.join(gettempdir(), 'deezloader-imgs')
if not os.path.isdir(TEMPDIR):
	makedirs(TEMPDIR)

extensions = {
	9: '.flac',
	3: '.mp3',
	1: '.mp3',
	8: '.mp3',
	15: '.mp4',
	14: '.mp4',
	13: '.mp4'
}

def getPreferredBitrare(filesize, bitrate):
	bitrateFound = False;
	selectedFormat = 0
	selectedFilesize = 0
	if int(bitrate) == 9:
		selectedFormat = 9
		selectedFilesize = filesize['flac']
		if filesize['flac'] > 0:
			bitrateFound = True
		else:
			bitrateFound = False
			bitrate = 3
	if int(bitrate) == 3:
		selectedFormat = 3
		selectedFilesize = filesize['mp3_320']
		if filesize['mp3_320'] > 0:
			bitrateFound = True
		else:
			bitrateFound = False
			bitrate = 1
	if int(bitrate) == 1:
		selectedFormat = 3
		selectedFilesize = filesize['mp3_320']
		if filesize['mp3_320'] > 0:
			bitrateFound = True
		else:
			bitrateFound = False
	if not bitrateFound:
		selectedFormat = 8
		selectedFilesize = filesize['default']
	return (selectedFormat, selectedFilesize)

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

def getTrackData(trackAPI_gw, trackAPI = None, albumAPI_gw = None, albumAPI = None):
	if not 'MD5_ORIGIN' in trackAPI_gw:
		trackAPI_gw['MD5_ORIGIN'] = dz.get_track_md5(trackAPI_gw['SNG_ID'])

	track = {}
	track['title'] = trackAPI_gw['SNG_TITLE']
	if trackAPI_gw['VERSION']:
		track['title'] += " " + trackAPI_gw['VERSION']

	track = parseEssentialTrackData(track, trackAPI_gw)

	if int(track['id']) < 0:
		track['filesize'] = trackAPI_gw['FILESIZE']
		track['album'] = {}
		track['album']['id'] = 0
		track['album']['title'] = trackAPI_gw['ALB_TITLE']
		if 'ALB_PICTURE' in trackAPI_gw:
			track['album']['pic'] = trackAPI_gw['ALB_PICTURE']
		track['mainArtist'] = {}
		track['mainArtist']['id'] = 0
		track['mainArtist']['name'] = trackAPI_gw['ART_NAME']
		track['artists'] = [trackAPI_gw['ART_NAME']]
		track['aritst'] = {
			'Main': [trackAPI_gw['ART_NAME']]
		}
		track['date'] = {
			'day': 0,
			'month': 0,
			'year': 0
		}
		track['localTrack'] = True
		return track

	if 'DISK_NUMBER' in trackAPI_gw:
		track['discNumber'] = trackAPI_gw['DISK_NUMBER']
	if 'EXPLICIT_LYRICS' in trackAPI_gw:
		track['explicit'] = trackAPI_gw['EXPLICIT_LYRICS'] != "0"
	if 'COPYRIGHT' in trackAPI_gw:
		track['copyright'] = trackAPI_gw['COPYRIGHT']
	track['replayGain'] = "{0:.2f} dB".format((float(trackAPI_gw['GAIN']) + 18.4) * -1) if 'GAIN' in trackAPI_gw else None
	track['ISRC'] = trackAPI_gw['ISRC']
	track['trackNumber'] = trackAPI_gw['TRACK_NUMBER']
	track['contributors'] = trackAPI_gw['SNG_CONTRIBUTORS']
	if 'POSITION' in trackAPI_gw:
		track['position'] = trackAPI_gw['POSITION']

	track['lyrics'] = {}
	if 'LYRICS_ID' in trackAPI_gw:
		track['lyrics']['id'] = trackAPI_gw['LYRICS_ID']
	if not "LYRICS" in trackAPI_gw and int(track['lyrics']['id']) != 0:
		trackAPI_gw["LYRICS"] = dz.get_lyrics_gw(track['id'])
	if int(track['lyrics']['id']) != 0:
		if "LYRICS_TEXT" in trackAPI_gw["LYRICS"]:
			track['lyrics']['unsync'] = trackAPI_gw["LYRICS"]["LYRICS_TEXT"]
		if "LYRICS_SYNC_JSON" in trackAPI_gw["LYRICS"]:
			track['lyrics']['sync'] = ""
			for i in range(len(trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"])):
				if "lrc_timestamp" in trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"][i]:
					track['lyrics']['sync'] += trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"][i]["lrc_timestamp"] + \
											   trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"] + "\r\n"
				elif i + 1 < len(trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"]):
					track['lyrics']['sync'] += trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"][i + 1]["lrc_timestamp"] + \
											   trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"] + "\r\n"

	track['mainArtist'] = {}
	track['mainArtist']['id'] = trackAPI_gw['ART_ID']
	track['mainArtist']['name'] = trackAPI_gw['ART_NAME']
	if 'ART_PICTURE' in trackAPI_gw:
		track['mainArtist']['pic'] = trackAPI_gw['ART_PICTURE']

	if 'PHYSICAL_RELEASE_DATE' in trackAPI_gw:
		track['date'] = {
			'day': trackAPI_gw["PHYSICAL_RELEASE_DATE"][8:10],
			'month': trackAPI_gw["PHYSICAL_RELEASE_DATE"][5:7],
			'year': trackAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
		}

	track['album'] = {}
	track['album']['id'] = trackAPI_gw['ALB_ID']
	track['album']['title'] = trackAPI_gw['ALB_TITLE']
	if 'ALB_PICTURE' in trackAPI_gw:
		track['album']['pic'] = trackAPI_gw['ALB_PICTURE']

	try:
		if not albumAPI:
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
		if 'release_date' in albumAPI:
			track['album']['date'] = {
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
		if not albumAPI_gw:
			albumAPI_gw = dz.get_album_gw(track['album']['id'])
		track['album']['artist'] = {
			'id': albumAPI_gw['ART_ID'],
			'name': albumAPI_gw['ART_NAME']
		}
		artistAPI = dz.get_artist(track['album']['artist']['id'])
		track['album']['artist']['pic'] = artistAPI['picture_small'][44:-24]
		track['album']['trackTotal'] = albumAPI_gw['NUMBER_TRACK']
		track['album']['discTotal'] = albumAPI_gw['NUMBER_DISK']
		track['album']['recordType'] = "Album"
		track['album']['barcode'] = "Unknown"
		track['album']['label'] = albumAPI_gw['LABEL_NAME'] if 'LABEL_NAME' in albumAPI_gw else "Unknown"
		if not 'pic' in track['album']:
			track['album']['pic'] = albumAPI_gw['ALB_PICTURE']
		if 'PHYSICAL_RELEASE_DATE' in albumAPI_gw:
			track['album']['date'] = {
				'day': albumAPI_gw["PHYSICAL_RELEASE_DATE"][8:10],
				'month': albumAPI_gw["PHYSICAL_RELEASE_DATE"][5:7],
				'year': albumAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
			}
		track['album']['genre'] = []

	if 'date' in track['album']:
		track['date'] = track['album']['date']

	if not trackAPI:
		trackAPI = dz.get_track(track['id'])
	track['bpm'] = trackAPI['bpm']
	if not 'replayGain' in track:
		track['replayGain'] = "{0:.2f} dB".format((float(trackAPI['gain']) + 18.4) * -1) if 'gain' in trackAPI else ""
	if not 'explicit' in track:
		track['explicit'] = trackAPI['explicit_lyrics']
	if not 'discNumber' in track:
		track['discNumber'] = trackAPI['disk_number']
	track['artist'] = {}
	track['artists'] = []
	for artist in trackAPI['contributors']:
		if artist['id'] != 5080:
			track['artists'].append(artist['name'])
			if not artist['role'] in track['artist']:
				track['artist'][artist['role']] = []
			track['artist'][artist['role']].append(artist['name'])

	if not 'discTotal' in track['album'] or not track['album']['discTotal']:
		if not albumAPI_gw:
			albumAPI_gw = dz.get_album_gw(track['album']['id'])
		track['album']['discTotal'] = albumAPI_gw['NUMBER_DISK']
	if not 'copyright' in track or not track['copyright']:
		if not albumAPI_gw:
			albumAPI_gw = dz.get_album_gw(track['album']['id'])
		track['copyright'] = albumAPI_gw['COPYRIGHT']
	return track

def downloadTrackObj(trackAPI, settings, overwriteBitrate=False, extraTrack=None):
	# Get the metadata
	if extraTrack:
		track = extraTrack
	else:
		track = getTrackData(
			trackAPI_gw = trackAPI,
			trackAPI =  trackAPI['_EXTRA_TRACK'] if '_EXTRA_TRACK' in trackAPI else None,
			albumAPI = trackAPI['_EXTRA_ALBUM'] if '_EXTRA_ALBUM' in trackAPI else None
		)
	print('Downloading: {} - {}'.format(track['mainArtist']['name'], track['title']))

	# Get the selected bitrate
	bitrate = overwriteBitrate if overwriteBitrate else settings['maxBitrate']
	(format, filesize) = getPreferredBitrare(track['filesize'], bitrate)
	track['selectedFormat'] = format
	track['selectedFilesize'] = filesize
	track['album']['bitrate'] = format
	track['album']['picUrl'] = "https://e-cdn-images.deezer.com/images/cover/{}/{}x{}-000000-80-0-0.{}".format(track['album']['pic'], settings['embeddedArtworkSize'], settings['embeddedArtworkSize'], 'png' if settings['PNGcovers'] else 'jpg')

	# Generate filename and filepath from metadata
	filename = generateFilename(track, trackAPI, settings)
	(filepath, artistPath, coverPath, extrasPath) = generateFilepath(track, trackAPI, settings)

	# Download and cache coverart
	track['album']['picPath'] = os.path.join(TEMPDIR, f"alb{track['album']['id']}_{settings['embeddedArtworkSize']}.{'png' if settings['PNGcovers'] else 'jpg'}")
	if not os.path.isfile(track['album']['picPath']):
		with open(track['album']['picPath'], 'wb') as f:
			try:
				f.write(urlopen(track['album']['picUrl']).read())
			except HTTPError:
				track['album']['picPath'] = None

	makedirs(filepath, exist_ok=True)
	writepath = os.path.join(filepath, filename + extensions[track['selectedFormat']])

	# Save lyrics in lrc file
	if settings['syncedLyrics'] and 'sync' in track['lyrics']:
		with open(os.path.join(filepath, filename + '.lrc'), 'w') as f:
			f.write(track['lyrics']['sync'])

	# Save local album art
	if coverPath:
		track['album']['picPathLocal'] = os.path.join(coverPath, f"{settingsRegexAlbum(settings['coverImageTemplate'], track['album'], settings)}.{'png' if settings['PNGcovers'] else 'jpg'}")
		if not os.path.isfile(track['album']['picPathLocal']):
			with open(track['album']['picPathLocal'], 'wb') as f:
				try:
					f.write(urlopen(track['album']['picUrl'].replace(f"{settings['embeddedArtworkSize']}x{settings['embeddedArtworkSize']}", f"{settings['localArtworkSize']}x{settings['localArtworkSize']}")).read())
				except HTTPError:
					track['album']['picPathLocal'] = None
	# Save artist art
	if artistPath:
		track['album']['artist']['picUrl'] = "https://cdns-images.dzcdn.net/images/artist/{}/{}x{}-000000-80-0-0.{}".format(track['album']['artist']['pic'], settings['localArtworkSize'], settings['localArtworkSize'], 'png' if settings['PNGcovers'] else 'jpg')
		track['album']['artist']['picPathLocal'] = os.path.join(artistPath, f"{settingsRegexArtist(settings['artistImageTemplate'], track['album']['artist'], settings)}.{'png' if settings['PNGcovers'] else 'jpg'}")
		if not os.path.isfile(track['album']['artist']['picPathLocal']):
			with open(track['album']['artist']['picPathLocal'], 'wb') as f:
				try:
					f.write(urlopen(track['album']['artist']['picUrl']).read())
				except HTTPError:
					track['album']['artist']['picPathLocal'] = None

	track['downloadUrl'] = dz.get_track_stream_url(track['id'], track['MD5'], track['mediaVersion'], track['selectedFormat'])
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
	trackAPI['FILENAME_TEMPLATE'] = settings['tracknameTemplate']
	trackAPI['SINGLE_TRACK'] = True
	downloadTrackObj(trackAPI, settings, overwriteBitrate)

def download_album(id, settings, overwriteBitrate=False):
	albumAPI = dz.get_album(id)
	albumAPI_gw = dz.get_album_gw(id)
	albumAPI['nb_disk'] = albumAPI_gw['NUMBER_DISK']
	albumAPI['copyright'] = albumAPI_gw['COPYRIGHT']
	if albumAPI['nb_tracks'] == 1:
		trackAPI = dz.get_track_gw(albumAPI['tracks']['data'][0]['id'])
		trackAPI['_EXTRA_ALBUM'] = albumAPI
		trackAPI['FILENAME_TEMPLATE'] = settings['tracknameTemplate']
		trackAPI['SINGLE_TRACK'] = True
		downloadTrackObj(trackAPI, settings, overwriteBitrate)
	else:
		tracksArray = dz.get_album_tracks_gw(id)
		for trackAPI in tracksArray:
			trackAPI['_EXTRA_ALBUM'] = albumAPI
			trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
			downloadTrackObj(trackAPI, settings, overwriteBitrate)

def download_playlist(id, settings, overwriteBitrate=False):
	playlistAPI = dz.get_playlist(id)
	playlistTracksAPI = dz.get_playlist_tracks_gw(id)
	for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
		trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
		trackAPI['POSITION'] = pos
		trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
		downloadTrackObj(trackAPI, settings, overwriteBitrate)
