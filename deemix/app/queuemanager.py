#!/usr/bin/env python3
from deemix.app.downloader import download
from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt
import logging

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
    if type == None or id == None:
        logger.warn("URL not recognized")
        result['error'] = "URL not recognized"
    elif type == "track":
        trackAPI = dz.get_track_gw(id)
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
        albumAPI = dz.get_album(id)
        albumAPI_gw = dz.get_album_gw(id)
        albumAPI['nb_disk'] = albumAPI_gw['NUMBER_DISK']
        albumAPI['copyright'] = albumAPI_gw['COPYRIGHT']
        if albumAPI['nb_tracks'] == 1:
            return generateQueueItem(dz, sp, f"https://www.deezer.com/track/{albumAPI['tracks']['data'][0]['id']}",
                                     settings, bitrate, albumAPI)
        tracksArray = dz.get_album_tracks_gw(id)

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
            playlistAPI = dz.get_playlist_gw(id)['results']['DATA']
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
            trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
            result['collection'].append(trackAPI)

    elif type == "artist":
        artistAPI = dz.get_artist(id)
        if interface:
            interface.send("toast",
                           {'msg': f"Adding {artistAPI['name']} albums to queue", 'icon': 'loading', 'dismiss': False,
                            'id': 'artist_' + str(artistAPI['id'])})
        artistAPITracks = dz.get_artist_albums(id)
        albumList = []
        for album in artistAPITracks['data']:
            albumList.append(generateQueueItem(dz, sp, album['link'], settings, bitrate))
        if interface:
            interface.send("toast",
                           {'msg': f"Added {artistAPI['name']} albums to queue", 'icon': 'done', 'dismiss': True,
                            'id': 'artist_' + str(artistAPI['id'])})
        return albumList
    elif type == "spotifytrack":
        result = {}
        if not sp.spotifyEnabled:
            logger.warn("Spotify Features is not setted up correctly.")
            result['error'] = "Spotify Features is not setted up correctly."
            return result
        track_id = sp.get_trackid_spotify(dz, id, settings['fallbackSearch'])
        if track_id != 0:
            return generateQueueItem(dz, sp, f'https://www.deezer.com/track/{track_id}', settings, bitrate)
        else:
            logger.warn("Track not found on deezer!")
            result['error'] = "Track not found on deezer!"
    elif type == "spotifyalbum":
        result = {}
        if not sp.spotifyEnabled:
            logger.warn("Spotify Features is not setted up correctly.")
            result['error'] = "Spotify Features is not setted up correctly."
            return result
        album_id = sp.get_albumid_spotify(dz, id)
        if album_id != 0:
            return generateQueueItem(dz, sp, f'https://www.deezer.com/album/{album_id}', settings, bitrate)
        else:
            logger.warn("Album not found on deezer!")
            result['error'] = "Album not found on deezer!"
    elif type == "spotifyplaylist":
        result = {}
        if not sp.spotifyEnabled:
            logger.warn("Spotify Features is not setted up correctly.")
            result['error'] = "Spotify Features is not setted up correctly."
            return result
        if interface:
            interface.send("toast",
                           {'msg': f"Converting spotify tracks to deezer tracks", 'icon': 'loading', 'dismiss': False,
                            'id': 'spotifyplaylist_' + str(id)})
        playlist = sp.convert_spotify_playlist(dz, id, settings)
        playlist['bitrate'] = bitrate
        playlist['uuid'] = f"{playlist['type']}_{id}_{bitrate}"
        result = playlist
        if interface:
            interface.send("toast", {'msg': f"Spotify playlist converted", 'icon': 'done', 'dismiss': True,
                                     'id': 'spotifyplaylist_' + str(id)})
    else:
        logger.warn("URL not supported yet")
        result['error'] = "URL not supported yet"
    return result


def addToQueue(dz, sp, url, settings, bitrate=None, interface=None):
    global currentItem, queueList, queue
    if not dz.logged_in:
        return "Not logged in"
    logger.info("Generating queue item for: "+url)
    queueItem = generateQueueItem(dz, sp, url, settings, bitrate, interface=interface)
    if type(queueItem) is list:
        for x in queueItem:
            if 'error' in x:
                logger.error(f"[{url}] {x['error']}")
                continue
            if x['uuid'] in list(queueList.keys()):
                logger.warn(f"[{x['uuid']}] Already in queue, will not be added again.")
                continue
            if interface:
                interface.send("addedToQueue", slimQueueItem(x))
            logger.info(f"[{x['uuid']}] Added to queue.")
            queue.append(x['uuid'])
            queueList[x['uuid']] = x
    else:
        if 'error' in queueItem:
            logger.error(f"[{url}] {queueItem['error']}")
            if interface:
                interface.send("toast", {'msg': queueItem['error'], 'icon': 'error'})
            return False
        if queueItem['uuid'] in list(queueList.keys()):
            logger.warn(f"[{queueItem['uuid']}] Already in queue, will not be added again.")
            if interface:
                interface.send("toast",
                               {'msg': f"{queueItem['title']} is already in queue!", 'icon': 'playlist_add_check'})
            return False
        if interface:
            interface.send("addedToQueue", slimQueueItem(queueItem))
            interface.send("toast", {'msg': f"{queueItem['title']} added to queue", 'icon': 'playlist_add'})
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
            interface.send('toast', {'msg': "Cancelling current item.", 'icon': 'loading', 'dismiss': False,
                                     'id': 'cancelling_' + uuid})
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
            interface.send('toast', {'msg': "Cancelling current item.", 'icon': 'loading', 'dismiss': False,
                                     'id': 'cancelling_' + currentItem})
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
