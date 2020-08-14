#!/usr/bin/env python3
from deemix.app.downloader import download
from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt
from deemix.api.deezer import APIError
from spotipy.exceptions import SpotifyException
from deemix.app.queueitem import QISingle, QICollection
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

class QueueManager:
    def __init__(self):
        self.queue = []
        self.queueList = {}
        self.queueComplete = []
        self.currentItem = ""

    def generateQueueItem(self, dz, sp, url, settings, bitrate=None, albumAPI=None, interface=None):
        forcedBitrate = getBitrateInt(bitrate)
        bitrate = forcedBitrate if forcedBitrate else settings['maxBitrate']
        type = getTypeFromLink(url)
        id = getIDFromLink(url, type)


        if type == None or id == None:
            logger.warn("URL not recognized")
            return queueError(url, "URL not recognized", "invalidURL")

        elif type == "track":
            if id.startswith("isrc"):
                try:
                    trackAPI = dz.get_track(id)
                    if 'id' in trackAPI and 'title' in trackAPI:
                        id = trackAPI['id']
                    else:

                except APIError as e:
                    e = json.loads(str(e))
                    return queueError(url, f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")
            try:
                trackAPI = dz.get_track_gw(id)
            except APIError as e:
                e = json.loads(str(e))
                message = "Wrong URL"
                if "DATA_ERROR" in e:
                    message += f": {e['DATA_ERROR']}"
                return queueError(url, message)
            if albumAPI:
                trackAPI['_EXTRA_ALBUM'] = albumAPI
            if settings['createSingleFolder']:
                trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
            else:
                trackAPI['FILENAME_TEMPLATE'] = settings['tracknameTemplate']
            trackAPI['SINGLE_TRACK'] = True

            title = trackAPI['SNG_TITLE']
            if 'VERSION' in trackAPI and trackAPI['VERSION']:
                title += " " + trackAPI['VERSION']
            return QISingle(
                id,
                bitrate,
                title,
                trackAPI['ART_NAME'],
                f"https://e-cdns-images.dzcdn.net/images/cover/{trackAPI['ALB_PICTURE']}/75x75-000000-80-0-0.jpg",
                'track',
                settings,
                trackAPI,
            )

        elif type == "album":
            try:
                albumAPI = dz.get_album(id)
            except APIError as e:
                e = json.loads(str(e))
                return queueError(url, f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")
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


            if albumAPI['cover_small'] != None:
                cover = albumAPI['cover_small'][:-24] + '/75x75-000000-80-0-0.jpg'
            else:
                cover = f"https://e-cdns-images.dzcdn.net/images/cover/{albumAPI_gw['ALB_PICTURE']}/75x75-000000-80-0-0.jpg"
            totalSize = len(tracksArray)
            collection = []
            for pos, trackAPI in enumerate(tracksArray, start=1):
                trackAPI['_EXTRA_ALBUM'] = albumAPI
                trackAPI['POSITION'] = pos
                trackAPI['SIZE'] = totalSize
                trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
                collection.append(trackAPI)

            return return QICollection(
                id,
                bitrate,
                albumAPI['title'],
                albumAPI['artist']['name'],
                cover,
                totalSize,
                'album',
                settings,
                collection,
            )


        elif type == "playlist":
            try:
                playlistAPI = dz.get_playlist(id)
            except:
                try:
                    playlistAPI = dz.get_playlist_gw(id)['results']['DATA']
                except APIError as e:
                    e = json.loads(str(e))
                    message = "Wrong URL"
                    if "DATA_ERROR" in e:
                        message += f": {e['DATA_ERROR']}"
                    return queueError(url, message)
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
                return return queueError(url, "You can't download others private playlists.", "notYourPrivatePlaylist")

            playlistTracksAPI = dz.get_playlist_tracks_gw(id)
            playlistAPI['various_artist'] = dz.get_artist(5080)

            totalSize = len(playlistTracksAPI)
            collection = []
            for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
                if 'EXPLICIT_TRACK_CONTENT' in trackAPI and 'EXPLICIT_LYRICS_STATUS' in trackAPI['EXPLICIT_TRACK_CONTENT'] and trackAPI['EXPLICIT_TRACK_CONTENT']['EXPLICIT_LYRICS_STATUS'] in [1,4]:
                    playlistAPI['explicit'] = True
                trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
                trackAPI['POSITION'] = pos
                trackAPI['SIZE'] = totalSize
                trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
                collection.append(trackAPI)
            if not 'explicit' in playlistAPI:
                playlistAPI['explicit'] = False

            return return QICollection(
                id,
                bitrate,
                playlistAPI['title'],
                playlistAPI['creator']['name'],
                playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
                totalSize,
                'playlist',
                settings,
                collection,
            )

        elif type == "artist":
            try:
                artistAPI = dz.get_artist(id)
            except APIError as e:
                e = json.loads(str(e))
                return return queueError(url, f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

            if interface:
                interface.send("startAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})

            artistAPITracks = dz.get_artist_albums(id)
            albumList = []
            for album in artistAPITracks['data']:
                albumList.append(generateQueueItem(dz, sp, album['link'], settings, bitrate))

            if interface:
                interface.send("finishAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})

            return albumList

        elif type == "artistdiscography":
            try:
                artistAPI = dz.get_artist(id)
            except APIError as e:
                e = json.loads(str(e))
                return return queueError(url, f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

            if interface:
                interface.send("startAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})

            artistDiscographyAPI = dz.get_artist_discography_gw(id, 100)
            albumList = []
            for type in artistDiscographyAPI:
                if type != 'all':
                    for album in artistDiscographyAPI[type]:
                        albumList.append(generateQueueItem(dz, sp, album['link'], settings, bitrate))

            if interface:
                interface.send("finishAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})

            return albumList

        elif type == "artisttop":
            try:
                artistAPI = dz.get_artist(id)
            except APIError as e:
                e = json.loads(str(e))
                return return queueError(url, f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

            playlistAPI = {
                'id': str(artistAPI['id'])+"_top_track",
                'title': artistAPI['name']+" - Top Tracks",
                'description': "Top Tracks for "+artistAPI['name'],
                'duration': 0,
                'public': True,
                'is_loved_track': False,
                'collaborative': False,
                'nb_tracks': 0,
                'fans': artistAPI['nb_fan'],
                'link': "https://www.deezer.com/artist/"+str(artistAPI['id'])+"/top_track",
                'share': None,
                'picture': artistAPI['picture'],
                'picture_small': artistAPI['picture_small'],
                'picture_medium': artistAPI['picture_medium'],
                'picture_big': artistAPI['picture_big'],
                'picture_xl': artistAPI['picture_xl'],
                'checksum': None,
                'tracklist': "https://api.deezer.com/artist/"+str(artistAPI['id'])+"/top",
                'creation_date': "XXXX-00-00",
                'creator': {
                    'id': "art_"+str(artistAPI['id']),
                    'name': artistAPI['name'],
                    'type': "user"
                },
                'type': "playlist"
            }

            artistTopTracksAPI_gw = dz.get_artist_toptracks_gw(id)
            playlistAPI['various_artist'] = dz.get_artist(5080)
            playlistAPI['nb_tracks'] = len(artistTopTracksAPI_gw)

            totalSize = len(artistTopTracksAPI_gw)
            collection = []
            for pos, trackAPI in enumerate(artistTopTracksAPI_gw, start=1):
                if 'EXPLICIT_TRACK_CONTENT' in trackAPI and 'EXPLICIT_LYRICS_STATUS' in trackAPI['EXPLICIT_TRACK_CONTENT'] and trackAPI['EXPLICIT_TRACK_CONTENT']['EXPLICIT_LYRICS_STATUS'] in [1,4]:
                    playlistAPI['explicit'] = True
                trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
                trackAPI['POSITION'] = pos
                trackAPI['SIZE'] = totalSize
                trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
                collection.append(trackAPI)
            if not 'explicit' in playlistAPI:
                playlistAPI['explicit'] = False

            return return QICollection(
                id,
                bitrate,
                playlistAPI['title'],
                playlistAPI['creator']['name'],
                playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
                totalSize,
                'playlist',
                settings,
                collection,
            )

        elif type == "spotifytrack":
            if not sp.spotifyEnabled:
                logger.warn("Spotify Features is not setted up correctly.")
                return queueError(url, "Spotify Features is not setted up correctly.", "spotifyDisabled")

            try:
                track_id = sp.get_trackid_spotify(dz, id, settings['fallbackSearch'])
            except SpotifyException as e:
                return queueError(url, "Wrong URL: "+e.msg[e.msg.find('\n')+2:])

            if track_id != 0:
                return generateQueueItem(dz, sp, f'https://www.deezer.com/track/{track_id}', settings, bitrate)
            else:
                logger.warn("Track not found on deezer!")
                return queueError(url, "Track not found on deezer!", "trackNotOnDeezer")

        elif type == "spotifyalbum":
            if not sp.spotifyEnabled:
                logger.warn("Spotify Features is not setted up correctly.")
                return queueError(url, "Spotify Features is not setted up correctly.", "spotifyDisabled")

            try:
                album_id = sp.get_albumid_spotify(dz, id)
            except SpotifyException as e:
                return queueError(url, "Wrong URL: "+e.msg[e.msg.find('\n')+2:])

            if album_id != 0:
                return generateQueueItem(dz, sp, f'https://www.deezer.com/album/{album_id}', settings, bitrate)
            else:
                logger.warn("Album not found on deezer!")
                return queueError(url, "Album not found on deezer!", "albumNotOnDeezer")

        elif type == "spotifyplaylist":
            if not sp.spotifyEnabled:
                logger.warn("Spotify Features is not setted up correctly.")
                return queueError(url, "Spotify Features is not setted up correctly.", "spotifyDisabled")

            try:
                playlist = sp.adapt_spotify_playlist(dz, id, settings)
                playlist['bitrate'] = bitrate
                playlist['uuid'] = f"{playlist['type']}_{id}_{bitrate}"
                return playlist
            except SpotifyException as e:
                return queueError(url, "Wrong URL: "+e.msg[e.msg.find('\n')+2:])

        else:
            logger.warn("URL not supported yet")
            return queueError(url, "URL not supported yet", "unsupportedURL")


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
    nextItem(dz, sp, interface)
    return True


def nextItem(dz, sp, interface=None):
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
        result = download(dz, sp, queueList[currentItem], interface)
        callbackQueueDone(result)


def callbackQueueDone(result):
    global currentItem, queueList, queueComplete
    if 'cancel' in queueList[currentItem]:
        del queueList[currentItem]
    else:
        queueComplete.append(currentItem)
    logger.info(f"[{currentItem}] Finished downloading.")
    currentItem = ""
    nextItem(result['dz'], result['sp'], result['interface'])


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

class queueError:
    def __init__(self, link, message, errid=None):
        self.link = link
        self.message = message
        self.errid = errid

    def toList(self):
        error = {
            'link'
        }
