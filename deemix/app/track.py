import eventlet
requests = eventlet.import_patched('requests')

import logging

from deezer.gw import APIError as gwAPIError, LyricsStatus
from deezer.api import APIError
from deemix.utils import removeFeatures, andCommaConcat, uniqueArray, generateReplayGainString

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

VARIOUS_ARTISTS = 5080

class Track:
    def __init__(self, dz, settings, trackAPI_gw, trackAPI=None, albumAPI_gw=None, albumAPI=None):
        self.parseEssentialData(dz, trackAPI_gw)

        self.title = trackAPI_gw['SNG_TITLE'].strip()
        if trackAPI_gw.get('VERSION') and not trackAPI_gw['VERSION'] in trackAPI_gw['SNG_TITLE']:
            self.title += " " + trackAPI_gw['VERSION'].strip()

        self.position = trackAPI_gw.get('POSITION')

        self.localTrack = int(self.id) < 0
        if self.localTrack:
            self.parseLocalTrackData(trackAPI_gw)
        else:
            self.parseData(dz, settings, trackAPI_gw, trackAPI, albumAPI_gw, albumAPI)

        # Make sure there is at least one artist
        if not 'Main' in self.artist:
            self.artist['Main'] = [self.mainArtist['name']]

        # Fix incorrect day month when detectable
        if int(self.date['month']) > 12:
            monthTemp = self.date['month']
            self.date['month'] = self.date['day']
            self.date['day'] = monthTemp
        if int(self.album['date']['month']) > 12:
            monthTemp = self.album['date']['month']
            self.album['date']['month'] = self.album['date']['day']
            self.album['date']['day'] = monthTemp

        # Add playlist data if track is in a playlist
        self.playlist = None
        if "_EXTRA_PLAYLIST" in trackAPI_gw:
            self.parsePlaylistData(trackAPI_gw["_EXTRA_PLAYLIST"], settings)

        self.singleDownload = trackAPI_gw.get('SINGLE_TRACK', False)

        self.generateMainFeatStrings()

        # Bits useful for later
        self.searched = False
        self.selectedFormat = 0
        self.dateString = None
        self.album['embeddedCoverURL'] = None
        self.album['embeddedCoverPath'] = None
        self.album['bitrate'] = 0
        self.album['dateString'] = None
        self.artistsString = ""

    def parseEssentialData(self, dz, trackAPI_gw):
        self.id = trackAPI_gw['SNG_ID']
        self.duration = trackAPI_gw['DURATION']
        self.MD5 = trackAPI_gw['MD5_ORIGIN']
        self.mediaVersion = trackAPI_gw['MEDIA_VERSION']
        self.fallbackId = "0"
        if 'FALLBACK' in trackAPI_gw:
            self.fallbackId = trackAPI_gw['FALLBACK']['SNG_ID']
        if int(self.id) > 0:
            self.filesizes = self.getFilesizes(dz)

    def parseLocalTrackData(self, trackAPI_gw):
        # Local tracks has only the trackAPI_gw page and
        # contains only the tags provided by the file
        self.album = {
            'id': "0",
            'title': trackAPI_gw['ALB_TITLE'],
            'pic': {
                'md5': trackAPI_gw.get('ALB_PICTURE', ""),
                'type': "cover",
                'url': None
            }
        }
        self.mainArtist = {
            'id': "0",
            'name': trackAPI_gw['ART_NAME'],
            'pic': {
                'md5': "",
                'type': "artist",
                'url': None
            }
        }
        self.artists = [trackAPI_gw['ART_NAME']]
        self.artist = {
            'Main': [trackAPI_gw['ART_NAME']]
        }
        self.date = {
            'day': "00",
            'month': "00",
            'year': "XXXX"
        }
        # Defaulting all the missing data
        self.ISRC = ""
        self.album['artist'] = self.artist
        self.album['artists'] = self.artists
        self.album['barcode'] = "Unknown"
        self.album['date'] = self.date
        self.album['discTotal'] = "0"
        self.album['explicit'] = False
        self.album['genre'] = []
        self.album['label'] = "Unknown"
        self.album['mainArtist'] = self.mainArtist
        self.album['recordType'] = "album"
        self.album['trackTotal'] = "0"
        self.bpm = 0
        self.contributors = {}
        self.copyright = ""
        self.discNumber = "0"
        self.explicit = False
        self.lyrics = {}
        self.replayGain = ""
        self.trackNumber = "0"

    def parseData(self, dz, settings, trackAPI_gw, trackAPI, albumAPI_gw, albumAPI):
        self.discNumber = trackAPI_gw.get('DISK_NUMBER')
        self.explicit = bool(int(trackAPI_gw.get('EXPLICIT_LYRICS', "0")))
        self.copyright = trackAPI_gw.get('COPYRIGHT')
        self.replayGain = ""
        if 'GAIN' in trackAPI_gw:
            self.replayGain = generateReplayGainString(trackAPI_gw['GAIN'])
        self.ISRC = trackAPI_gw.get('ISRC')
        self.trackNumber = trackAPI_gw['TRACK_NUMBER']
        self.contributors = trackAPI_gw['SNG_CONTRIBUTORS']

        self.lyrics = {
            'id': int(trackAPI_gw.get('LYRICS_ID', "0")),
            'unsync': None,
            'sync': None,
            'syncID3': None
        }
        if not "LYRICS" in trackAPI_gw and self.lyrics['id'] != 0:
            logger.info(f"[{trackAPI_gw['ART_NAME']} - {self.title}] Getting lyrics")
            try:
                trackAPI_gw["LYRICS"] = dz.gw.get_track_lyrics(self.id)
            except gwAPIError:
                self.lyrics['id'] = 0
        if self.lyrics['id'] != 0:
            self.lyrics['unsync'] = trackAPI_gw["LYRICS"].get("LYRICS_TEXT")
            if "LYRICS_SYNC_JSON" in trackAPI_gw["LYRICS"]:
                syncLyricsJson = trackAPI_gw["LYRICS"]["LYRICS_SYNC_JSON"]
                self.lyrics['sync'] = ""
                self.lyrics['syncID3'] = []
                timestamp = ""
                milliseconds = 0
                for line in range(len(syncLyricsJson)):
                    if syncLyricsJson[line]["line"] != "":
                        timestamp = syncLyricsJson[line]["lrc_timestamp"]
                        milliseconds = int(syncLyricsJson[line]["milliseconds"])
                        self.lyrics['syncID3'].append((syncLyricsJson[line]["line"], milliseconds))
                    else:
                        notEmptyLine = line + 1
                        while syncLyricsJson[notEmptyLine]["line"] == "":
                            notEmptyLine = notEmptyLine + 1
                        timestamp = syncLyricsJson[notEmptyLine]["lrc_timestamp"]
                    self.lyrics['sync'] += timestamp + syncLyricsJson[line]["line"] + "\r\n"

        self.mainArtist = {
            'id': trackAPI_gw['ART_ID'],
            'name': trackAPI_gw['ART_NAME'],
            'pic': {
                'md5': trackAPI_gw.get('ART_PICTURE'),
                'type': "artist",
                'url': None
            }
        }

        self.date = None
        if 'PHYSICAL_RELEASE_DATE' in trackAPI_gw:
            self.date = {
                'day': trackAPI_gw["PHYSICAL_RELEASE_DATE"][8:10],
                'month': trackAPI_gw["PHYSICAL_RELEASE_DATE"][5:7],
                'year': trackAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
            }

        self.album = {
            'id': trackAPI_gw['ALB_ID'],
            'title': trackAPI_gw['ALB_TITLE'],
            'pic': {
                'md5': trackAPI_gw.get('ALB_PICTURE'),
                'type': "cover",
                'url': None
            },
            'barcode': "Unknown",
            'label': "Unknown",
            'explicit': False,
            'date': None,
            'genre': []
        }

        # Try the public API first (as it has more data)
        if not albumAPI:
            logger.info(f"[{self.mainArtist['name']} - {self.title}] Getting album infos")
            try:
                albumAPI = dz.api.get_album(self.album['id'])
            except APIError:
                albumAPI = None

        if albumAPI:
            self.album['title'] = albumAPI['title']

            # Getting artist image ID
            # ex: https://e-cdns-images.dzcdn.net/images/artist/f2bc007e9133c946ac3c3907ddc5d2ea/56x56-000000-80-0-0.jpg
            artistPicture = albumAPI['artist']['picture_small']
            artistPicture = artistPicture[artistPicture.find('artist/') + 7:-24]
            self.album['mainArtist'] = {
                'id': albumAPI['artist']['id'],
                'name': albumAPI['artist']['name'],
                'pic': {
                    'md5': artistPicture,
                    'type': "artist",
                    'url': None
                }
            }
            self.album['rootArtist'] = albumAPI.get('root_artist', None)

            self.album['artist'] = {}
            self.album['artists'] = []
            for artist in albumAPI['contributors']:
                isVariousArtists = artist['id'] == VARIOUS_ARTISTS
                isMainArtist = artist['role'] == "Main"

                if not isVariousArtists or settings['albumVariousArtists'] and isVariousArtists:
                    if artist['name'] not in self.album['artists']:
                        self.album['artists'].append(artist['name'])

                    if isMainArtist or artist['name'] not in self.album['artist']['Main'] and not isMainArtist:
                        if not artist['role'] in self.album['artist']:
                            self.album['artist'][artist['role']] = []
                        self.album['artist'][artist['role']].append(artist['name'])

            if settings['removeDuplicateArtists']:
                self.album['artists'] = uniqueArray(self.album['artists'])
                for role in self.album['artist'].keys():
                    self.album['artist'][role] = uniqueArray(self.album['artist'][role])

            self.album['trackTotal'] = albumAPI['nb_tracks']
            self.album['recordType'] = albumAPI['record_type']

            self.album['barcode'] = albumAPI.get('upc', self.album['barcode'])
            self.album['label'] = albumAPI.get('label', self.album['label'])
            self.album['explicit'] = bool(albumAPI.get('explicit_lyrics', False))
            if 'release_date' in albumAPI:
                self.album['date'] = {
                    'day': albumAPI["release_date"][8:10],
                    'month': albumAPI["release_date"][5:7],
                    'year': albumAPI["release_date"][0:4]
                }
            self.album['discTotal'] = albumAPI.get('nb_disk', "1")
            self.copyright = albumAPI.get('copyright')

            if not self.album['pic']['md5']:
                # Getting album cover MD5
                # ex: https://e-cdns-images.dzcdn.net/images/cover/2e018122cb56986277102d2041a592c8/56x56-000000-80-0-0.jpg
                self.album['pic']['md5'] = albumAPI['cover_small'][albumAPI['cover_small'].find('cover/') + 6:-24]

            if albumAPI.get('genres') and len(albumAPI['genres'].get('data', [])) > 0:
                for genre in albumAPI['genres']['data']:
                    self.album['genre'].append(genre['name'])
        else:
            if not albumAPI_gw:
                logger.info(f"[{self.mainArtist['name']} - {self.title}] Getting more album infos")
                try:
                    albumAPI_gw = dz.gw.get_album(self.album['id'])
                except gwAPIError:
                    albumAPI_gw = None
                    raise AlbumDoesntExists

            self.album['title'] = albumAPI_gw['ALB_TITLE']
            self.album['mainArtist'] = {
                'id': albumAPI_gw['ART_ID'],
                'name': albumAPI_gw['ART_NAME'],
                'pic': {
                    'md5': "",
                    'type': "artist",
                    'url': None
                }
            }
            self.album['rootArtist'] = None

            # albumAPI_gw doesn't contain the artist cover
            # Getting artist image ID
            # ex: https://e-cdns-images.dzcdn.net/images/artist/f2bc007e9133c946ac3c3907ddc5d2ea/56x56-000000-80-0-0.jpg
            logger.info(f"[{self.mainArtist['name']} - {self.title}] Getting artist picture fallback")
            artistAPI = dz.api.get_artist(self.album['mainArtist']['id'])
            self.album['mainArtist']['pic']['md5'] = artistAPI['picture_small'][artistAPI['picture_small'].find('artist/') + 7:-24]

            self.album['artists'] = [albumAPI_gw['ART_NAME']]
            self.album['trackTotal'] = albumAPI_gw['NUMBER_TRACK']
            self.album['discTotal'] = albumAPI_gw['NUMBER_DISK']
            self.album['recordType'] = "album"
            self.album['label'] = albumAPI_gw.get('LABEL_NAME', self.album['label'])

            explicitLyricsStatus = albumAPI_gw.get('EXPLICIT_ALBUM_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN)
            self.album['explicit'] = explicitLyricsStatus in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]

            if not self.album['pic']['md5']:
                self.album['pic']['md5'] = albumAPI_gw['ALB_PICTURE']
            if 'PHYSICAL_RELEASE_DATE' in albumAPI_gw:
                self.album['date'] = {
                    'day': albumAPI_gw["PHYSICAL_RELEASE_DATE"][8:10],
                    'month': albumAPI_gw["PHYSICAL_RELEASE_DATE"][5:7],
                    'year': albumAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
                }

        isAlbumArtistVariousArtists = self.album['mainArtist']['id'] == VARIOUS_ARTISTS
        self.album['mainArtist']['save'] = not isAlbumArtistVariousArtists or settings['albumVariousArtists'] and isAlbumArtistVariousArtists

        if self.album['date'] and not self.date:
            self.date = self.album['date']

        if not trackAPI:
            logger.info(f"[{self.mainArtist['name']} - {self.title}] Getting extra track infos")
            trackAPI = dz.api.get_track(self.id)
        self.bpm = trackAPI['bpm']

        if not self.replayGain and 'gain' in trackAPI:
            self.replayGain = generateReplayGainString(trackAPI['gain'])
        if not self.explicit:
            self.explicit = trackAPI['explicit_lyrics']
        if not self.discNumber:
            self.discNumber = trackAPI['disk_number']

        self.artist = {}
        self.artists = []
        for artist in trackAPI['contributors']:
            isVariousArtists = artist['id'] == VARIOUS_ARTISTS
            isMainArtist = artist['role'] == "Main"

            if not isVariousArtists or len(trackAPI['contributors']) == 1 and isVariousArtists:
                if artist['name'] not in self.artists:
                    self.artists.append(artist['name'])

                if isMainArtist or artist['name'] not in self.artist['Main'] and not isMainArtist:
                    if not artist['role'] in self.artist:
                        self.artist[artist['role']] = []
                    self.artist[artist['role']].append(artist['name'])

        if settings['removeDuplicateArtists']:
            self.artists = uniqueArray(self.artists)
            for role in self.artist.keys():
                self.artist[role] = uniqueArray(self.artist[role])

        if not self.album['discTotal']:
            if not albumAPI_gw:
                logger.info(f"[{self.mainArtist['name']} - {self.title}] Getting more album infos")
                albumAPI_gw = dz.gw.get_album(self.album['id'])
            self.album['discTotal'] = albumAPI_gw['NUMBER_DISK']

        if not self.copyright:
            if not albumAPI_gw:
                logger.info(f"[{self.mainArtist['name']} - {self.title}] Getting more album infos")
                albumAPI_gw = dz.gw.get_album(self.album['id'])
            self.copyright = albumAPI_gw['COPYRIGHT']

    def parsePlaylistData(self, playlist, settings):
        self.playlist = {}
        if 'dzcdn.net' in playlist['picture_small']:
            url = playlist['picture_small']
            picType = url[url.find('images/')+7:]
            picType = picType[:picType.find('/')]
            self.playlist['pic'] = {
                'md5': url[url.find(picType+'/') + len(picType)+1:-24],
                'type': picType,
                'url': None
            }
        else:
            self.playlist['pic'] = {
                'md5': None,
                'type': None,
                'url': playlist['picture_xl']
            }
        self.playlist['title'] = playlist['title']
        self.playlist['mainArtist'] = {
            'id': playlist['various_artist']['id'],
            'name': playlist['various_artist']['name'],
            'pic': {
                'md5': playlist['various_artist']['picture_small'][
                       playlist['various_artist']['picture_small'].find('artist/') + 7:-24],
                'type': "artist",
                'url': None
            }
        }
        self.playlist['rootArtist'] = None
        if settings['albumVariousArtists']:
            self.playlist['artist'] = {"Main": [playlist['various_artist']['name'], ]}
            self.playlist['artists'] = [playlist['various_artist']['name'], ]
        else:
            self.playlist['artist'] = {"Main": []}
            self.playlist['artists'] = []
        self.playlist['trackTotal'] = playlist['nb_tracks']
        self.playlist['recordType'] = "compile"
        self.playlist['barcode'] = ""
        self.playlist['label'] = ""
        self.playlist['explicit'] = playlist['explicit']
        self.playlist['date'] = {
            'day': playlist["creation_date"][8:10],
            'month': playlist["creation_date"][5:7],
            'year': playlist["creation_date"][0:4]
        }
        self.playlist['discTotal'] = "1"
        self.playlist['playlistId'] = playlist['id']
        self.playlist['owner'] = playlist['creator']

    # Removes featuring from the title
    def getCleanTitle(self):
        return removeFeatures(self.title)

    # Removes featuring from the album name
    def getCleanAlbumTitle(self):
        return removeFeatures(self.album['title'])

    def getFeatTitle(self):
        if self.featArtistsString and not "(feat." in self.title.lower():
            return self.title + " ({})".format(self.featArtistsString)
        return self.title

    def generateMainFeatStrings(self):
        self.mainArtistsString = andCommaConcat(self.artist['Main'])
        self.featArtistsString = ""
        if 'Featured' in self.artist:
            self.featArtistsString = "feat. "+andCommaConcat(self.artist['Featured'])

    def getFilesizes(self, dz):
        try:
            guest_sid = dz.session.cookies.get('sid')
            site = requests.post(
                "https://api.deezer.com/1.0/gateway.php",
                params={
                    'api_key': "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE",
                    'sid': guest_sid,
                    'input': '3',
                    'output': '3',
                    'method': 'song_getData'
                },
                timeout=30,
                json={'sng_id': self.id},
                headers=dz.http_headers
            )
            result_json = site.json()
        except:
            eventlet.sleep(2)
            return self.getFilesizes(dz)
        if len(result_json['error']):
            raise APIError(json.dumps(result_json['error']))
        response = result_json.get("results")
        filesizes = {}
        for key, value in response.items():
            if key.startswith("FILESIZE_"):
                filesizes[key] = value
                filesizes[key+"_TESTED"] = False
        return filesizes

class TrackError(Exception):
    """Base class for exceptions in this module."""
    pass

class AlbumDoesntExists(TrackError):
    pass
