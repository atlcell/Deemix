#!/usr/bin/env python3
from deemix.app.downloader import download
from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt
from deemix.api.deezer import APIError
from spotipy.exceptions import SpotifyException
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

queue = []
queueList = {}
queueComplete = []
currentItem = ""

"""
queueItem base structure
	title
	artist
	cover
	size
	downloaded
	failed
    errors
	progress
	type
	id
	bitrate
	uuid: type+id+bitrate
if its a single track
	single
if its an album/playlist
	collection
"""

def resetQueueItems(items, q):
    result = {}
    for item in items.keys():
        result[item] = items[item].copy()
        if item in q:
            result[item]['downloaded'] = 0
            result[item]['failed'] = 0
            result[item]['progress'] = 0
            result[item]['errors'] = []
    return result

def slimQueueItems(items):
    result = {}
    for item in items.keys():
        result[item] = slimQueueItem(items[item])
    return result

def slimQueueItem(item):
    light = item.copy()
    if 'single' in light:
        del light['single']
    if 'collection' in light:
        del light['collection']
    return light

def generateQueueItem(dz, sp, url, settings, bitrate=None, albumAPI=None, interface=None):
    forcedBitrate = getBitrateInt(bitrate)
    bitrate = forcedBitrate if forcedBitrate else settings['maxBitrate']
    type = getTypeFromLink(url)
    id = getIDFromLink(url, type)
    result = {}
    result['link'] = url
    if type == None or id == None:
        logger.warn("URL not recognized")
        result['error'] = "URL not recognized"
        result['errid'] = "invalidURL"
    elif type == "track":
        if id.startswith("isrc"):
            try:
                trackAPI = dz.get_track(id)
                if 'id' in trackAPI and 'title' in trackAPI:
                    id = trackAPI['id']
                else:
                    result['error'] = "Track ISRC is not available on deezer"
                    result['errid'] = "ISRCnotOnDeezer"
                    return result
            except APIError as e:
                e = json.loads(str(e))
                result['error'] = f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}"
                return result
        try:
            trackAPI = dz.get_track_gw(id)
        except APIError as e:
            e = json.loads(str(e))
            result['error'] = "Wrong URL"
            if "DATA_ERROR" in e:
                result['error'] += f": {e['DATA_ERROR']}"
            return result
        if albumAPI:
            trackAPI['_EXTRA_ALBUM'] = albumAPI
        if settings['createSingleFolder']:
            trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
        else:
            trackAPI['FILENAME_TEMPLATE'] = settings['tracknameTemplate']
        trackAPI['SINGLE_TRACK'] = True

        result['title'] = trackAPI['SNG_TITLE']
        if 'VERSION' in trackAPI and trackAPI['VERSION']:
            result['title'] += " " + trackAPI['VERSION']
        result['artist'] = trackAPI['ART_NAME']
        result[
            'cover'] = f"https://e-cdns-images.dzcdn.net/images/cover/{trackAPI['ALB_PICTURE']}/75x75-000000-80-0-0.jpg"
        result['size'] = 1
        result['downloaded'] = 0
        result['failed'] = 0
        result['errors'] = []
        result['progress'] = 0
        result['type'] = 'track'
        result['id'] = id
        result['bitrate'] = bitrate
        result['uuid'] = f"{result['type']}_{id}_{bitrate}"
        result['settings'] = settings or {}
        result['single'] = trackAPI

    elif type == "album":
        try:
            albumAPI = dz.get_album(id)
        except APIError as e:
            e = json.loads(str(e))
            result['error'] = f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}"
            return result
        if id.startswith('upc'):
            id = albumAPI['id']
        albumAPI_gw = dz.get_album_gw(id)
        albumAPI['nb_disk'] = albumAPI_gw['NUMBER_DISK']
        albumAPI['copyright'] = albumAPI_gw['COPYRIGHT']
        if albumAPI['nb_tracks'] == 1:
            return generateQueueItem(dz, sp, f"https://www.deezer.com/track/{albumAPI['tracks']['data'][0]['id']}",
                                     settings, bitrate, albumAPI)
        tracksArray = dz.get_album_tracks_gw(id)
        if albumAPI['nb_tracks'] == 255:
            albumAPI['nb_tracks'] = len(tracksArray)

        result['title'] = albumAPI['title']
        result['artist'] = albumAPI['artist']['name']
        if albumAPI['cover_small'] != None:
            result['cover'] = albumAPI['cover_small'][:-24] + '/75x75-000000-80-0-0.jpg'
        else:
            result['cover'] = f"https://e-cdns-images.dzcdn.net/images/cover/{albumAPI_gw['ALB_PICTURE']}/75x75-000000-80-0-0.jpg"
        result['size'] = albumAPI['nb_tracks']
        result['downloaded'] = 0
        result['failed'] = 0
        result['errors'] = []
        result['progress'] = 0
        result['type'] = 'album'
        result['id'] = id
        result['bitrate'] = bitrate
        result['uuid'] = f"{result['type']}_{id}_{bitrate}"
        result['settings'] = settings or {}
        totalSize = len(tracksArray)
        result['collection'] = []
        for pos, trackAPI in enumerate(tracksArray, start=1):
            trackAPI['_EXTRA_ALBUM'] = albumAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
            result['collection'].append(trackAPI)

    elif type == "playlist":
        try:
            playlistAPI = dz.get_playlist(id)
        except:
            try:
                playlistAPI = dz.get_playlist_gw(id)['results']['DATA']
            except APIError as e:
                e = json.loads(str(e))
                result['error'] = "Wrong URL"
                if "DATA_ERROR" in e:
                    result['error'] += f": {e['DATA_ERROR']}"
                return result
            newPlaylist = {
                'id': playlistAPI['PLAYLIST_ID'],
                'title': playlistAPI['TITLE'],
                'description': playlistAPI['DESCRIPTION'],
                'duration': playlistAPI['DURATION'],
                'public': False,
                'is_loved_track': False,
                'collaborative': False,
                'nb_tracks': playlistAPI['NB_SONG'],
                'fans': playlistAPI['NB_FAN'],
                'link': "https://www.deezer.com/playlist/"+playlistAPI['PLAYLIST_ID'],
                'share': None,
                'picture': "https://api.deezer.com/playlist/"+playlistAPI['PLAYLIST_ID']+"/image",
                'picture_small': "https://cdns-images.dzcdn.net/images/"+playlistAPI['PICTURE_TYPE']+"/"+playlistAPI['PLAYLIST_PICTURE']+"/56x56-000000-80-0-0.jpg",
                'picture_medium': "https://cdns-images.dzcdn.net/images/"+playlistAPI['PICTURE_TYPE']+"/"+playlistAPI['PLAYLIST_PICTURE']+"/250x250-000000-80-0-0.jpg",
                'picture_big': "https://cdns-images.dzcdn.net/images/"+playlistAPI['PICTURE_TYPE']+"/"+playlistAPI['PLAYLIST_PICTURE']+"/500x500-000000-80-0-0.jpg",
                'picture_xl': "https://cdns-images.dzcdn.net/images/"+playlistAPI['PICTURE_TYPE']+"/"+playlistAPI['PLAYLIST_PICTURE']+"/1000x1000-000000-80-0-0.jpg",
                'checksum': playlistAPI['CHECKSUM'],
                'tracklist': "https://api.deezer.com/playlist/"+playlistAPI['PLAYLIST_ID']+"/tracks",
                'creation_date': playlistAPI['DATE_ADD'],
                'creator': {
                    'id': playlistAPI['PARENT_USER_ID'],
                    'name': playlistAPI['PARENT_USERNAME'],
                    'tracklist': "https://api.deezer.com/user/"+playlistAPI['PARENT_USER_ID']+"/flow",
                    'type': "user"
                },
                'type': "playlist"
            }
            playlistAPI = newPlaylist
        if not playlistAPI['public'] and playlistAPI['creator']['id'] != str(dz.user['id']):
            logger.warn("You can't download others private playlists.")
            result['error'] = "You can't download others private playlists."
            result['errid'] = "notYourPrivatePlaylist"
            return result

        playlistTracksAPI = dz.get_playlist_tracks_gw(id)
        playlistAPI['various_artist'] = dz.get_artist(5080)

        result['title'] = playlistAPI['title']
        result['artist'] = playlistAPI['creator']['name']
        result['cover'] = playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg'
        result['size'] = playlistAPI['nb_tracks']
        result['downloaded'] = 0
        result['failed'] = 0
        result['errors'] = []
        result['progress'] = 0
        result['type'] = 'playlist'
        result['id'] = id
        result['bitrate'] = bitrate
        result['uuid'] = f"{result['type']}_{id}_{bitrate}"
        result['settings'] = settings or {}
        totalSize = len(playlistTracksAPI)
        result['collection'] = []
        for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
            if 'EXPLICIT_TRACK_CONTENT' in trackAPI and 'EXPLICIT_LYRICS_STATUS' in trackAPI['EXPLICIT_TRACK_CONTENT'] and trackAPI['EXPLICIT_TRACK_CONTENT']['EXPLICIT_LYRICS_STATUS'] in [1,4]:
                playlistAPI['explicit'] = True
            trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
            result['collection'].append(trackAPI)
        if not 'explicit' in playlistAPI:
            playlistAPI['explicit'] = False

    elif type == "artist":
        try:
            albumAPI = artistAPI = dz.get_artist(id)
        except APIError as e:
            e = json.loads(str(e))
            result['error'] = f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}"
            return result
        if interface:
            interface.send("startAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})
        artistAPITracks = dz.get_artist_albums(id)
        albumList = []
        for album in artistAPITracks['data']:
            albumList.append(generateQueueItem(dz, sp, album['link'], settings, bitrate))
        if interface:
            interface.send("finishAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})
        return albumList
    elif type == "spotifytrack":
        if not sp.spotifyEnabled:
            logger.warn("Spotify Features is not setted up correctly.")
            result['error'] = "Spotify Features is not setted up correctly."
            result['errid'] = "spotifyDisabled"
            return result
        try:
            track_id = sp.get_trackid_spotify(dz, id, settings['fallbackSearch'])
        except SpotifyException as e:
            result['error'] = "Wrong URL: "+e.msg[e.msg.find('\n')+2:]
            return result
        if track_id != 0:
            return generateQueueItem(dz, sp, f'https://www.deezer.com/track/{track_id}', settings, bitrate)
        else:
            logger.warn("Track not found on deezer!")
            result['error'] = "Track not found on deezer!"
            result['errid'] = "trackNotOnDeezer"
    elif type == "spotifyalbum":
        if not sp.spotifyEnabled:
            logger.warn("Spotify Features is not setted up correctly.")
            result['error'] = "Spotify Features is not setted up correctly."
            result['errid'] = "spotifyDisabled"
            return result
        try:
            album_id = sp.get_albumid_spotify(dz, id)
        except SpotifyException as e:
            result['error'] = "Wrong URL: "+e.msg[e.msg.find('\n')+2:]
            return result
        if album_id != 0:
            return generateQueueItem(dz, sp, f'https://www.deezer.com/album/{album_id}', settings, bitrate)
        else:
            logger.warn("Album not found on deezer!")
            result['error'] = "Album not found on deezer!"
            result['errid'] = "albumNotOnDeezer"
    elif type == "spotifyplaylist":
        if not sp.spotifyEnabled:
            logger.warn("Spotify Features is not setted up correctly.")
            result['error'] = "Spotify Features is not setted up correctly."
            result['errid'] = "spotifyDisabled"
            return result
        if interface:
            interface.send("startConvertingSpotifyPlaylist", str(id))
        try:
            playlist = sp.convert_spotify_playlist(dz, id, settings)
        except SpotifyException as e:
            result['error'] = "Wrong URL: "+e.msg[e.msg.find('\n')+2:]
            return result
        playlist['bitrate'] = bitrate
        playlist['uuid'] = f"{playlist['type']}_{id}_{bitrate}"
        result = playlist
        if interface:
            interface.send("finishConvertingSpotifyPlaylist", str(id))
    else:
        logger.warn("URL not supported yet")
        result['error'] = "URL not supported yet"
        result['errid'] = "unsupportedURL"
    return result


def addToQueue(dz, sp, url, settings, bitrate=None, interface=None):
    global currentItem, queueList, queue
    if not dz.logged_in:
        return "Not logged in"
    if type(url) is list:
        queueItem = []
        for link in url:
            link = link.strip()
            if link == "":
                continue
            logger.info("Generating queue item for: "+link)
            item = generateQueueItem(dz, sp, link, settings, bitrate, interface=interface)
            if type(item) is list:
                queueItem += item
            else:
                queueItem.append(item)
    else:
        url = url.strip()
        if url == "":
            return False
        logger.info("Generating queue item for: "+url)
        queueItem = generateQueueItem(dz, sp, url, settings, bitrate, interface=interface)
    if type(queueItem) is list:
        for x in queueItem:
            if 'error' in x:
                logger.error(f"[{x['link']}] {x['error']}")
                continue
            if x['uuid'] in list(queueList.keys()):
                logger.warn(f"[{x['uuid']}] Already in queue, will not be added again.")
                continue
            if interface:
                interface.send("addedToQueue", slimQueueItem(x))
            queue.append(x['uuid'])
            queueList[x['uuid']] = x
            logger.info(f"[{x['uuid']}] Added to queue.")
    else:
        if 'error' in queueItem:
            logger.error(f"[{queueItem['link']}] {queueItem['error']}")
            if interface:
                interface.send("queueError", queueItem)
            return False
        if queueItem['uuid'] in list(queueList.keys()):
            logger.warn(f"[{queueItem['uuid']}] Already in queue, will not be added again.")
            if interface:
                interface.send("alreadyInQueue", {'uuid': queueItem['uuid'], 'title': queueItem['title']})
            return False
        if interface:
            interface.send("addedToQueue", slimQueueItem(queueItem))
        logger.info(f"[{queueItem['uuid']}] Added to queue.")
        queue.append(queueItem['uuid'])
        queueList[queueItem['uuid']] = queueItem
    nextItem(dz, interface)
    return True


def nextItem(dz, interface=None):
    global currentItem, queueList, queue
    if currentItem != "":
        return None
    else:
        if len(queue) > 0:
            currentItem = queue.pop(0)
        else:
            return None
        if interface:
            interface.send("startDownload", currentItem)
        logger.info(f"[{currentItem}] Started downloading.")
        result = download(dz, queueList[currentItem], interface)
        callbackQueueDone(result)


def callbackQueueDone(result):
    global currentItem, queueList, queueComplete
    if 'cancel' in queueList[currentItem]:
        del queueList[currentItem]
    else:
        queueComplete.append(currentItem)
    logger.info(f"[{currentItem}] Finished downloading.")
    currentItem = ""
    nextItem(result['dz'], result['interface'])


def getQueue():
    global currentItem, queueList, queue, queueComplete
    return (queue, queueComplete, queueList, currentItem)


def restoreQueue(pqueue, pqueueComplete, pqueueList, dz, interface):
    global currentItem, queueList, queue, queueComplete
    queueComplete = pqueueComplete
    queueList = pqueueList
    queue = pqueue
    nextItem(dz, interface)


def removeFromQueue(uuid, interface=None):
    global currentItem, queueList, queue, queueComplete
    if uuid == currentItem:
        if interface:
            interface.send("cancellingCurrentItem", currentItem)
        queueList[uuid]['cancel'] = True
    elif uuid in queue:
        queue.remove(uuid)
        del queueList[uuid]
        if interface:
            interface.send("removedFromQueue", uuid)
    elif uuid in queueComplete:
        queueComplete.remove(uuid)
        del queueList[uuid]
        if interface:
            interface.send("removedFromQueue", uuid)


def cancelAllDownloads(interface=None):
    global currentItem, queueList, queue, queueComplete
    queue = []
    queueComplete = []
    if currentItem != "":
        if interface:
            interface.send("cancellingCurrentItem", currentItem)
        queueList[currentItem]['cancel'] = True
    for uuid in list(queueList.keys()):
        if uuid != currentItem:
            del queueList[uuid]
    if interface:
        interface.send("removedAllDownloads", currentItem)


def removeFinishedDownloads(interface=None):
    global queueList, queueComplete
    for uuid in queueComplete:
        del queueList[uuid]
    queueComplete = []
    if interface:
        interface.send("removedFinishedDownloads")
