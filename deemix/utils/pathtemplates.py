#!/usr/bin/env python3
import re
from os.path import sep as pathSep

bitrateLabels = {
	15: "360 HQ",
	14: "360 MQ",
	13: "360 LQ",
	9: "FLAC",
	3: "320",
	1: "128",
	8: "128"
}

def fixName(txt, char='_'):
	txt = str(txt)
	txt = re.sub(r'[\0\/\\:*?"<>|]', char, txt)
	return txt

def fixLongName(name):
	if pathSep in name:
		name2 = name.split(pathSep)
		name = ""
		for txt in name:
			txt = txt[:200]
			name += txt+pathSep
		name = name[:-1]
	else:
		name = name[:200]
	return name

def antiDot(str):
	while str[-1:] == "." or str[-1:] == " " or str[-1:] == "\n":
		str = str[:-1]
	if len(str) < 1:
		str = "dot"
	return str

def pad(num, max, dopad=True):
	paddingsize = len(str(max))
	if dopad:
		return str(num).zfill(paddingsize)
	else:
		return str(num)

def generateFilename(track, trackAPI, settings):
	if trackAPI['FILENAME_TEMPLATE'] == "":
		filename = "%artist% - %title%"
	else:
		filename = trackAPI['FILENAME_TEMPLATE']
	return settingsRegex(filename, track, settings, trackAPI['_EXTRA_PLAYLIST'] if '_EXTRA_PLAYLIST' in trackAPI else None)

def generateFilepath(track, trackAPI, settings):
	filepath = settings['downloadLocation']
	if filepath[-1:] != pathSep:
		filepath += pathSep
	artistPath = None
	coverPath = None
	extrasPath = None

	if settings['createPlaylistFolder'] and '_EXTRA_PLAYLIST' in trackAPI and not settings['savePlaylistAsCompilation']:
		filepath += antiDot(settingsRegexPlaylist(settings['playlistNameTemplate'], trackAPI['_EXTRA_PLAYLIST'], settings)) + pathSep

	if '_EXTRA_PLAYLIST' in trackAPI and not settings['savePlaylistAsCompilation']:
		extrasPath = filepath

	if (
		settings['createArtistFolder'] and not '_EXTRA_PLAYLIST' in trackAPI or
		(settings['createArtistFolder'] and '_EXTRA_PLAYLIST' in trackAPI and settings['savePlaylistAsCompilation']) or
		(settings['createArtistFolder'] and '_EXTRA_PLAYLIST' in trackAPI and settings['createStructurePlaylist'])
	):
		if (track['id']<0 and not 'artist' in track['album']):
			track['album']['artist'] = track['mainArtist']
		filepath += antiDot(settingsRegexArtist(settings['artistNameTemplate'], track['album']['artist'], settings)) + pathSep
		artistPath = filepath

	if (settings['createAlbumFolder'] and
		(not 'SINGLE_TRACK' in trackAPI or ('SINGLE_TRACK' in trackAPI and settings['createSingleFolder'])) and
		(not '_EXTRA_PLAYLIST' in trackAPI or ('_EXTRA_PLAYLIST' in trackAPI and settings['savePlaylistAsCompilation']) or ('_EXTRA_PLAYLIST' in trackAPI and settings['createStructurePlaylist']))
	):
		filepath += antiDot(settingsRegexAlbum(settings['albumNameTemplate'], track['album'], settings)) + pathSep
		coverPath = filepath

	if not ('_EXTRA_PLAYLIST' in trackAPI and not settings['savePlaylistAsCompilation']):
		extrasPath = filepath

	if (
		int(track['album']['discTotal']) > 1 and (
		(settings['createAlbumFolder'] and settings['createCDFolder']) and
		(not 'SINGLE_TRACK' in trackAPI or ('SINGLE_TRACK' in trackAPI and settings['createSingleFolder'])) and
		(not '_EXTRA_PLAYLIST' in trackAPI or ('_EXTRA_PLAYLIST' in trackAPI and settings['savePlaylistAsCompilation']) or ('_EXTRA_PLAYLIST' in trackAPI and settings['createStructurePlaylist']))
	)):
		filepath += 'CD'+str(track['discNumber']) + pathSep

	return (filepath, artistPath, coverPath, extrasPath)

def settingsRegex(filename, track, settings, playlist=None):
	filename = filename.replace("%title%", fixName(track['title'], settings['illegalCharacterReplacer']))
	filename = filename.replace("%artist%", fixName(track['mainArtist']['name'], settings['illegalCharacterReplacer']))
	filename = filename.replace("%album%", fixName(track['album']['title'], settings['illegalCharacterReplacer']))
	filename = filename.replace("%albumartist%", fixName(track['album']['artist']['name'], settings['illegalCharacterReplacer']))
	filename = filename.replace("%tracknumber%", pad(track['trackNumber'], track['album']['trackTotal'], settings['padTracks']))
	filename = filename.replace("%tracktotal%", str(track['album']['trackTotal']))
	filename = filename.replace("%discnumber%", str(track['discNumber']))
	filename = filename.replace("%disctotal%", str(track['album']['discTotal']))
	if len(track['album']['genre'])>0:
		filename = filename.replace("%genre%", fixName(track['album']['genre'][0], settings['illegalCharacterReplacer']))
	else:
		filename = filename.replace("%genre%", "Unknown")
	filename = filename.replace("%year%", str(track['date']['year']))
	filename = filename.replace("%date%", "{}-{}-{}".format(str(track['date']['year']), str(track['date']['month']), str(track['date']['day'])))
	filename = filename.replace("%bpm%", str(track['bpm']))
	filename = filename.replace("%label%", fixName(track['album']['label'], settings['illegalCharacterReplacer']))
	filename = filename.replace("%isrc%", track['ISRC'])
	filename = filename.replace("%upc%", track['album']['barcode'])
	filename = filename.replace("%explicit%", "(Explicit)" if track['explicit'] else "")

	filename = filename.replace("%track_id%", str(track['id']))
	filename = filename.replace("%album_id%", str(track['album']['id']))
	filename = filename.replace("%artist_id%", str(track['mainArtist']['id']))
	if playlist:
		filename = filename.replace("%playlist_id%", str(playlist['id']))
		filename = filename.replace("%position%", pad(track['position'], playlist['nb_tracks'], settings['padTracks']))
	else:
		filename = filename.replace("%position%", pad(track['trackNumber'], track['album']['trackTotal'], settings['padTracks']))
	filename = re.sub(r'[/\\]', pathSep, filename)
	return antiDot(fixLongName(filename))

def settingsRegexAlbum(foldername, album, settings):
	foldername = foldername.replace("%album_id%", str(album['id']))
	foldername = foldername.replace("%album%", fixName(album['title'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%artist%", fixName(album['artist']['name'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%artist_id%", str(album['artist']['id']))
	foldername = foldername.replace("%tracktotal%", str(album['trackTotal']))
	foldername = foldername.replace("%disctotal%", str(album['discTotal']))
	foldername = foldername.replace("%type%", fixName(album['recordType'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%upc%", album['barcode'])
	foldername = foldername.replace("%label%", fixName(album['label'], settings['illegalCharacterReplacer']))
	if len(album['genre'])>0:
		foldername = foldername.replace("%genre%", fixName(album['genre'][0], settings['illegalCharacterReplacer']))
	else:
		foldername = foldername.replace("%genre%", "Unknown")
	foldername = foldername.replace("%year%", str(album['date']['year']))
	foldername = foldername.replace("%date%", "{}-{}-{}".format(str(album['date']['year']), str(album['date']['month']), str(album['date']['day'])))
	foldername = foldername.replace("%bitrate%", bitrateLabels[int(album['bitrate'])])

	foldername = re.sub(r'[/\\]', pathSep, foldername)
	return antiDot(fixLongName(foldername))

def settingsRegexArtist(foldername, artist, settings):
	foldername = foldername.replace("%artist%", fixName(artist['name'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%artist_id%", str(artist['id']))
	foldername = re.sub(r'[/\\]', pathSep, foldername)
	return antiDot(fixLongName(foldername))

def settingsRegexPlaylist(foldername, playlist, settings):
	foldername = foldername.replace("%playlist%", fixName(playlist['title'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%playlist_id%", fixName(playlist['id'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%owner%", fixName(playlist['creator']['name'], settings['illegalCharacterReplacer']))
	foldername = foldername.replace("%owner_id%", str(playlist['creator']['id']))
	foldername = foldername.replace("%year%", str(playlist['creation_date'][:4]))
	foldername = foldername.replace("%date%", str(playlist['creation_date'][:10]))
	foldername = re.sub(r'[/\\]', pathSep, foldername)
	return antiDot(fixLongName(foldername))
