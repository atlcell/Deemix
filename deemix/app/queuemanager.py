from deemix.app.downloadjob import DownloadJob
from deemix.utils import getIDFromLink, getTypeFromLink, getBitrateInt
from deezer.gw import APIError as gwAPIError, LyricsStatus
from deezer.api import APIError
from spotipy.exceptions import SpotifyException
from deemix.app.queueitem import QueueItem, QISingle, QICollection, QIConvertable
import logging
from pathlib import Path
import json
from os import remove
import eventlet
import uuid
urlopen = eventlet.import_patched('urllib.request').urlopen

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

class QueueManager:
    def __init__(self, spotifyHelper=None):
        self.queue = []
        self.queueList = {}
        self.queueComplete = []
        self.currentItem = ""
        self.sp = spotifyHelper

    def generateTrackQueueItem(self, dz, id, settings, bitrate, trackAPI=None, albumAPI=None):
        # Check if is an isrc: url
        if str(id).startswith("isrc"):
            try:
                trackAPI = dz.api.get_track(id)
            except APIError as e:
                e = json.loads(str(e))
                return QueueError("https://deezer.com/track/"+str(id), f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")
            if 'id' in trackAPI and 'title' in trackAPI:
                id = trackAPI['id']
            else:
                return QueueError("https://deezer.com/track/"+str(id), "Track ISRC is not available on deezer", "ISRCnotOnDeezer")

        # Get essential track info
        try:
            trackAPI_gw = dz.gw.get_track_with_fallback(id)
        except gwAPIError as e:
            e = json.loads(str(e))
            message = "Wrong URL"
            if "DATA_ERROR" in e: message += f": {e['DATA_ERROR']}"
            return QueueError("https://deezer.com/track/"+str(id), message)

        if albumAPI: trackAPI_gw['_EXTRA_ALBUM'] = albumAPI
        if trackAPI: trackAPI_gw['_EXTRA_TRACK'] = trackAPI

        if settings['createSingleFolder']:
            trackAPI_gw['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
        else:
            trackAPI_gw['FILENAME_TEMPLATE'] = settings['tracknameTemplate']

        trackAPI_gw['SINGLE_TRACK'] = True

        title = trackAPI_gw['SNG_TITLE'].strip()
        if trackAPI_gw.get('VERSION') and trackAPI_gw['VERSION'] not in trackAPI_gw['SNG_TITLE']:
            title += f" {trackAPI_gw['VERSION']}".strip()
        explicit = bool(int(trackAPI_gw.get('EXPLICIT_LYRICS', 0)))

        return QISingle(
            id=id,
            bitrate=bitrate,
            title=title,
            artist=trackAPI_gw['ART_NAME'],
            cover=f"https://e-cdns-images.dzcdn.net/images/cover/{trackAPI_gw['ALB_PICTURE']}/75x75-000000-80-0-0.jpg",
            explicit=explicit,
            type='track',
            settings=settings,
            single=trackAPI_gw,
        )

    def generateAlbumQueueItem(self, dz, id, settings, bitrate, rootArtist=None):
        # Get essential album info
        try:
            albumAPI = dz.api.get_album(id)
        except APIError as e:
            e = json.loads(str(e))
            return QueueError("https://deezer.com/album/"+str(id), f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

        if str(id).startswith('upc'): id = albumAPI['id']

        # Get extra info about album
        # This saves extra api calls when downloading
        albumAPI_gw = dz.gw.get_album(id)
        albumAPI['nb_disk'] = albumAPI_gw['NUMBER_DISK']
        albumAPI['copyright'] = albumAPI_gw['COPYRIGHT']
        albumAPI['root_artist'] = rootArtist

        # If the album is a single download as a track
        if albumAPI['nb_tracks'] == 1:
            return self.generateTrackQueueItem(dz, albumAPI['tracks']['data'][0]['id'], settings, bitrate, albumAPI=albumAPI)

        tracksArray = dz.gw.get_album_tracks(id)

        if albumAPI['cover_small'] != None:
            cover = albumAPI['cover_small'][:-24] + '/75x75-000000-80-0-0.jpg'
        else:
            cover = f"https://e-cdns-images.dzcdn.net/images/cover/{albumAPI_gw['ALB_PICTURE']}/75x75-000000-80-0-0.jpg"

        totalSize = len(tracksArray)
        albumAPI['nb_tracks'] = totalSize
        collection = []
        for pos, trackAPI in enumerate(tracksArray, start=1):
            trackAPI['_EXTRA_ALBUM'] = albumAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
            collection.append(trackAPI)

        explicit = albumAPI_gw.get('EXPLICIT_ALBUM_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]

        return QICollection(
            id=id,
            bitrate=bitrate,
            title=albumAPI['title'],
            artist=albumAPI['artist']['name'],
            cover=cover,
            explicit=explicit,
            size=totalSize,
            type='album',
            settings=settings,
            collection=collection,
        )

    def generatePlaylistQueueItem(self, dz, id, settings, bitrate):
        # Get essential playlist info
        try:
            playlistAPI = dz.api.get_playlist(id)
        except:
            playlistAPI = None
        # Fallback to gw api if the playlist is private
        if not playlistAPI:
            try:
                playlistAPI = dz.gw.get_playlist_page(id)
            except gwAPIError as e:
                e = json.loads(str(e))
                message = "Wrong URL"
                if "DATA_ERROR" in e:
                    message += f": {e['DATA_ERROR']}"
                return QueueError("https://deezer.com/playlist/"+str(id), message)

        # Check if private playlist and owner
        if not playlistAPI['public'] and playlistAPI['creator']['id'] != str(dz.current_user['id']):
            logger.warn("You can't download others private playlists.")
            return QueueError("https://deezer.com/playlist/"+str(id), "You can't download others private playlists.", "notYourPrivatePlaylist")

        playlistTracksAPI = dz.gw.get_playlist_tracks(id)
        playlistAPI['various_artist'] = dz.api.get_artist(5080) # Useful for save as compilation

        totalSize = len(playlistTracksAPI)
        playlistAPI['nb_tracks'] = totalSize
        collection = []
        for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
            if trackAPI.get('EXPLICIT_TRACK_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]:
                playlistAPI['explicit'] = True
            trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
            collection.append(trackAPI)
        if not 'explicit' in playlistAPI:
            playlistAPI['explicit'] = False

        return QICollection(
            id=id,
            bitrate=bitrate,
            title=playlistAPI['title'],
            artist=playlistAPI['creator']['name'],
            cover=playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
            explicit=playlistAPI['explicit'],
            size=totalSize,
            type='playlist',
            settings=settings,
            collection=collection,
        )

    def generateArtistQueueItem(self, dz, id, settings, bitrate, interface=None):
        # Get essential artist info
        try:
            artistAPI = dz.api.get_artist(id)
        except APIError as e:
            e = json.loads(str(e))
            return QueueError("https://deezer.com/artist/"+str(id), f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

        if interface: interface.send("startAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})
        rootArtist = {
            'id': artistAPI['id'],
            'name': artistAPI['name']
        }

        artistDiscographyAPI = dz.gw.get_artist_discography_tabs(id, 100)
        allReleases = artistDiscographyAPI.pop('all', [])
        albumList = []
        for album in allReleases:
            albumList.append(self.generateAlbumQueueItem(dz, album['id'], settings, bitrate, rootArtist=rootArtist))

        if interface: interface.send("finishAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})
        return albumList

    def generateArtistDiscographyQueueItem(self, dz, id, settings, bitrate, interface=None):
        # Get essential artist info
        try:
            artistAPI = dz.api.get_artist(id)
        except APIError as e:
            e = json.loads(str(e))
            return QueueError("https://deezer.com/artist/"+str(id)+"/discography", f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

        if interface: interface.send("startAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})
        rootArtist = {
            'id': artistAPI['id'],
            'name': artistAPI['name']
        }

        artistDiscographyAPI = dz.gw.get_artist_discography_tabs(id, 100)
        artistDiscographyAPI.pop('all', None) # all contains albums and singles, so its all duplicates. This removes them
        albumList = []
        for type in artistDiscographyAPI:
            for album in artistDiscographyAPI[type]:
                albumList.append(self.generateAlbumQueueItem(dz, album['id'], settings, bitrate, rootArtist=rootArtist))

        if interface: interface.send("finishAddingArtist", {'name': artistAPI['name'], 'id': artistAPI['id']})
        return albumList

    def generateArtistTopQueueItem(self, dz, id, settings, bitrate, interface=None):
        # Get essential artist info
        try:
            artistAPI = dz.api.get_artist(id)
        except APIError as e:
            e = json.loads(str(e))
            return QueueError("https://deezer.com/artist/"+str(id)+"/top_track", f"Wrong URL: {e['type']+': ' if 'type' in e else ''}{e['message'] if 'message' in e else ''}")

        # Emulate the creation of a playlist
        # Can't use generatePlaylistQueueItem as this is not a real playlist
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

        artistTopTracksAPI_gw = dz.gw.get_artist_toptracks(id)
        playlistAPI['various_artist'] = dz.api.get_artist(5080) # Useful for save as compilation

        totalSize = len(artistTopTracksAPI_gw)
        playlistAPI['nb_tracks'] = totalSize
        collection = []
        for pos, trackAPI in enumerate(artistTopTracksAPI_gw, start=1):
            if trackAPI.get('EXPLICIT_TRACK_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]:
                playlistAPI['explicit'] = True
            trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
            collection.append(trackAPI)
        if not 'explicit' in playlistAPI:
            playlistAPI['explicit'] = False

        return QICollection(
            id=id,
            bitrate=bitrate,
            title=playlistAPI['title'],
            artist=playlistAPI['creator']['name'],
            cover=playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
            explicit=playlistAPI['explicit'],
            size=totalSize,
            type='playlist',
            settings=settings,
            collection=collection,
        )

    def generateQueueItem(self, dz, url, settings, bitrate=None, interface=None):
        bitrate = getBitrateInt(bitrate) or settings['maxBitrate']
        if 'deezer.page.link' in url: url = urlopen(url).url
        if 'link.tospotify.com' in url: url = urlopen(url).url

        type = getTypeFromLink(url)
        id = getIDFromLink(url, type)
        if type == None or id == None:
            logger.warn("URL not recognized")
            return QueueError(url, "URL not recognized", "invalidURL")

        if type == "track":
            return self.generateTrackQueueItem(dz, id, settings, bitrate)
        elif type == "album":
            return self.generateAlbumQueueItem(dz, id, settings, bitrate)
        elif type == "playlist":
            return self.generatePlaylistQueueItem(dz, id, settings, bitrate)
        elif type == "artist":
            return self.generateArtistQueueItem(dz, id, settings, bitrate, interface=interface)
        elif type == "artistdiscography":
            return self.generateArtistDiscographyQueueItem(dz, id, settings, bitrate, interface=interface)
        elif type == "artisttop":
            return self.generateArtistTopQueueItem(dz, id, settings, bitrate, interface=interface)
        elif type.startswith("spotify") and self.sp:
            if not self.sp.spotifyEnabled:
                logger.warn("Spotify Features is not setted up correctly.")
                return QueueError(url, "Spotify Features is not setted up correctly.", "spotifyDisabled")

            if type == "spotifytrack":
                try:
                    (track_id, trackAPI, _) = self.sp.get_trackid_spotify(dz, id, settings['fallbackSearch'])
                except SpotifyException as e:
                    return QueueError(url, "Wrong URL: "+e.msg[e.msg.find('\n')+2:])
                except Exception as e:
                    return QueueError(url, "Something went wrong: "+str(e))

                if track_id != "0":
                    return self.generateTrackQueueItem(dz, track_id, settings, bitrate, trackAPI=trackAPI)
                else:
                    logger.warn("Track not found on deezer!")
                    return QueueError(url, "Track not found on deezer!", "trackNotOnDeezer")

            elif type == "spotifyalbum":
                try:
                    album_id = self.sp.get_albumid_spotify(dz, id)
                except SpotifyException as e:
                    return QueueError(url, "Wrong URL: "+e.msg[e.msg.find('\n')+2:])
                except Exception as e:
                    return QueueError(url, "Something went wrong: "+str(e))

                if album_id != "0":
                    return self.generateAlbumQueueItem(dz, album_id, settings, bitrate)
                else:
                    logger.warn("Album not found on deezer!")
                    return QueueError(url, "Album not found on deezer!", "albumNotOnDeezer")

            elif type == "spotifyplaylist":
                try:
                    return self.sp.generate_playlist_queueitem(dz, id, bitrate, settings)
                except SpotifyException as e:
                    return QueueError(url, "Wrong URL: "+e.msg[e.msg.find('\n')+2:])
                except Exception as e:
                    return QueueError(url, "Something went wrong: "+str(e))
        logger.warn("URL not supported yet")
        return QueueError(url, "URL not supported yet", "unsupportedURL")

    def addToQueue(self, dz, url, settings, bitrate=None, interface=None, ack=None):
        if not dz.logged_in:
            if interface: interface.send("loginNeededToDownload")
            return False

        def parseLink(link):
            link = link.strip()
            if link == "": return False
            logger.info("Generating queue item for: "+link)
            item = self.generateQueueItem(dz, link, settings, bitrate, interface=interface)

            # Add ack to all items
            if type(item) is list:
                for i in item:
                    if isinstance(i, QueueItem):
                        i.ack = ack
            elif isinstance(item, QueueItem):
                item.ack = ack
            return item

        if type(url) is list:
            queueItem = []
            request_uuid = str(uuid.uuid4())
            if interface: interface.send("startGeneratingItems", {'uuid': request_uuid, 'total': len(url)})
            for link in url:
                item = parseLink(link)
                if not item: continue
                if type(item) is list:
                    queueItem += item
                else:
                    queueItem.append(item)
            if interface: interface.send("finishGeneratingItems", {'uuid': request_uuid, 'total': len(queueItem)})
            if not len(queueItem):
                return False
        else:
            queueItem = parseLink(url)
            if not queueItem:
                return False

        def processQueueItem(item, silent=False):
            if isinstance(item, QueueError):
                logger.error(f"[{item.link}] {item.message}")
                if interface: interface.send("queueError", item.toDict())
                return False
            if item.uuid in list(self.queueList.keys()):
                logger.warn(f"[{item.uuid}] Already in queue, will not be added again.")
                if interface and not silent: interface.send("alreadyInQueue", {'uuid': item.uuid, 'title': item.title})
                return False
            self.queue.append(item.uuid)
            self.queueList[item.uuid] = item
            logger.info(f"[{item.uuid}] Added to queue.")
            return True

        if type(queueItem) is list:
            slimmedItems = []
            for item in queueItem:
                if processQueueItem(item, silent=True):
                    slimmedItems.append(item.getSlimmedItem())
                else:
                    continue
            if not len(slimmedItems):
                return False
            if interface: interface.send("addedToQueue", slimmedItems)
        else:
            if processQueueItem(queueItem):
                if interface: interface.send("addedToQueue", queueItem.getSlimmedItem())
            else:
                return False
        self.nextItem(dz, interface)
        return True

    def nextItem(self, dz, interface=None):
        # Check that nothing is already downloading and
        # that the queue is not empty
        if self.currentItem != "": return None
        if not len(self.queue): return None

        self.currentItem = self.queue.pop(0)

        if isinstance(self.queueList[self.currentItem], QIConvertable) and self.queueList[self.currentItem].extra:
            logger.info(f"[{self.currentItem}] Converting tracks to deezer.")
            self.sp.convert_spotify_playlist(dz, self.queueList[self.currentItem], interface=interface)
            logger.info(f"[{self.currentItem}] Tracks converted.")

        if interface: interface.send("startDownload", self.currentItem)
        logger.info(f"[{self.currentItem}] Started downloading.")

        DownloadJob(dz, self.queueList[self.currentItem], interface).start()

        if self.queueList[self.currentItem].cancel:
            del self.queueList[self.currentItem]
        else:
            self.queueComplete.append(self.currentItem)
        logger.info(f"[{self.currentItem}] Finished downloading.")
        self.currentItem = ""
        self.nextItem(dz, interface)

    def getQueue(self):
        return (self.queue, self.queueComplete, self.slimQueueList(), self.currentItem)

    def saveQueue(self, configFolder):
        if len(self.queueList) > 0:
            if self.currentItem != "":
                self.queue.insert(0, self.currentItem)
            with open(Path(configFolder) / 'queue.json', 'w') as f:
                json.dump({
                    'queue': self.queue,
                    'queueComplete': self.queueComplete,
                    'queueList': self.exportQueueList()
                }, f)

    def exportQueueList(self):
        queueList = {}
        for uuid in self.queueList:
            if uuid in self.queue:
                queueList[uuid] = self.queueList[uuid].getResettedItem()
            else:
                queueList[uuid] = self.queueList[uuid].toDict()
        return queueList

    def slimQueueList(self):
        queueList = {}
        for uuid in self.queueList:
            queueList[uuid] = self.queueList[uuid].getSlimmedItem()
        return queueList

    def loadQueue(self, configFolder, settings, interface=None):
        configFolder = Path(configFolder)
        if (configFolder / 'queue.json').is_file() and not len(self.queue):
            if interface: interface.send('restoringQueue')
            with open(configFolder / 'queue.json', 'r') as f:
                try:
                    qd = json.load(f)
                except json.decoder.JSONDecodeError:
                    logger.warn("Saved queue is corrupted, resetting it")
                    qd = {
                        'queue': [],
                        'queueComplete': [],
                        'queueList': {}
                    }
            remove(configFolder / 'queue.json')
            self.restoreQueue(qd['queue'], qd['queueComplete'], qd['queueList'], settings)
            if interface:
                interface.send('init_downloadQueue', {
                    'queue': self.queue,
                    'queueComplete': self.queueComplete,
                    'queueList': self.slimQueueList(),
                    'restored': True
                })

    def restoreQueue(self, queue, queueComplete, queueList, settings):
        self.queue = queue
        self.queueComplete = queueComplete
        self.queueList = {}
        for uuid in queueList:
            if 'single' in queueList[uuid]:
                self.queueList[uuid] = QISingle(queueItemDict = queueList[uuid])
            if 'collection' in queueList[uuid]:
                self.queueList[uuid] = QICollection(queueItemDict = queueList[uuid])
            if '_EXTRA' in queueList[uuid]:
                self.queueList[uuid] = QIConvertable(queueItemDict = queueList[uuid])
            self.queueList[uuid].settings = settings

    def removeFromQueue(self, uuid, interface=None):
        if uuid == self.currentItem:
            if interface: interface.send("cancellingCurrentItem", uuid)
            self.queueList[uuid].cancel = True
            return
        if uuid in self.queue:
            self.queue.remove(uuid)
        elif uuid in self.queueComplete:
            self.queueComplete.remove(uuid)
        else:
            return
        del self.queueList[uuid]
        if interface: interface.send("removedFromQueue", uuid)


    def cancelAllDownloads(self, interface=None):
        self.queue = []
        self.queueComplete = []
        if self.currentItem != "":
            if interface: interface.send("cancellingCurrentItem", self.currentItem)
            self.queueList[self.currentItem].cancel = True
        for uuid in list(self.queueList.keys()):
            if uuid != self.currentItem: del self.queueList[uuid]
        if interface: interface.send("removedAllDownloads", self.currentItem)


    def removeFinishedDownloads(self, interface=None):
        for uuid in self.queueComplete:
            del self.queueList[uuid]
        self.queueComplete = []
        if interface: interface.send("removedFinishedDownloads")

class QueueError:
    def __init__(self, link, message, errid=None):
        self.link = link
        self.message = message
        self.errid = errid

    def toDict(self):
        return {
            'link': self.link,
            'error': self.message,
            'errid': self.errid
        }
