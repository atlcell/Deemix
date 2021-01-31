import eventlet
requests = eventlet.import_patched('requests')

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

from deezer.gw import APIError as gwAPIError
from deezer.api import APIError
from deemix.utils import removeFeatures, andCommaConcat, removeDuplicateArtists, generateReplayGainString
from deemix.types.Album import Album
from deemix.types.Artist import Artist
from deemix.types.Date import Date
from deemix.types.Picture import Picture
from deemix.types.Playlist import Playlist
from deemix.types.Lyrics import Lyrics
from deemix import VARIOUS_ARTISTS

class Track:
    def __init__(self, id="0", name=""):
        self.id = id
        self.title = name
        self.MD5 = ""
        self.mediaVersion = ""
        self.duration = 0
        self.fallbackId = "0"
        self.filesizes = {}
        self.localTrack = False
        self.mainArtist = None
        self.artist = {"Main": []}
        self.artists = []
        self.album = None
        self.trackNumber = "0"
        self.discNumber = "0"
        self.date = None
        self.lyrics = None
        self.bpm = 0
        self.contributors = {}
        self.copyright = ""
        self.explicit = False
        self.ISRC = ""
        self.replayGain = ""
        self.playlist = None
        self.position = None
        self.searched = False
        self.selectedFormat = 0
        self.singleDownload = False
        self.dateString = None
        self.artistsString = ""
        self.mainArtistsString = ""
        self.featArtistsString = ""

    def parseEssentialData(self, trackAPI_gw, trackAPI=None):
        self.id = str(trackAPI_gw['SNG_ID'])
        self.duration = trackAPI_gw['DURATION']
        self.MD5 = trackAPI_gw.get('MD5_ORIGIN')
        if not self.MD5:
            if trackAPI and trackAPI.get('md5_origin'):
                self.MD5 = trackAPI['md5_origin']
            else:
                raise MD5NotFound
        self.mediaVersion = trackAPI_gw['MEDIA_VERSION']
        self.fallbackId = "0"
        if 'FALLBACK' in trackAPI_gw:
            self.fallbackId = trackAPI_gw['FALLBACK']['SNG_ID']
        self.localTrack = int(self.id) < 0

    def retriveFilesizes(self, dz):
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
            return self.retriveFilesizes(dz)
        if len(result_json['error']):
            raise APIError(json.dumps(result_json['error']))
        response = result_json.get("results")
        filesizes = {}
        for key, value in response.items():
            if key.startswith("FILESIZE_"):
                filesizes[key] = value
                filesizes[key+"_TESTED"] = False
        self.filesizes = filesizes

    def parseData(self, dz, id=None, trackAPI_gw=None, trackAPI=None, albumAPI_gw=None, albumAPI=None, playlistAPI=None):
        if id:
            if not trackAPI_gw: trackAPI_gw = dz.gw.get_track_with_fallback(id)
        elif not trackAPI_gw: raise NoDataToParse
        if not trackAPI:
            try: trackAPI = dz.api.get_track(trackAPI_gw['SNG_ID'])
            except APIError: trackAPI = None

        self.parseEssentialData(trackAPI_gw, trackAPI)

        if self.localTrack:
            self.parseLocalTrackData(trackAPI_gw)
        else:
            self.retriveFilesizes(dz)

            self.parseTrackGW(trackAPI_gw)
            # Get Lyrics data
            if not "LYRICS" in trackAPI_gw and self.lyrics.id != "0":
                try: trackAPI_gw["LYRICS"] = dz.gw.get_track_lyrics(self.id)
                except gwAPIError: self.lyrics.id = "0"
            if self.lyrics.id != "0": self.lyrics.parseLyrics(trackAPI_gw["LYRICS"])

            # Parse Album data
            self.album = Album(
                id = trackAPI_gw['ALB_ID'],
                title = trackAPI_gw['ALB_TITLE'],
                pic_md5 = trackAPI_gw.get('ALB_PICTURE')
            )

            # Get album Data
            if not albumAPI:
                try: albumAPI = dz.api.get_album(self.album.id)
                except APIError: albumAPI = None

            # Get album_gw Data
            if not albumAPI_gw:
                try: albumAPI_gw = dz.gw.get_album(self.album.id)
                except gwAPIError: albumAPI_gw = None

            if albumAPI:
                self.album.parseAlbum(albumAPI)
            elif albumAPI_gw:
                self.album.parseAlbumGW(albumAPI_gw)
                # albumAPI_gw doesn't contain the artist cover
                # Getting artist image ID
                # ex: https://e-cdns-images.dzcdn.net/images/artist/f2bc007e9133c946ac3c3907ddc5d2ea/56x56-000000-80-0-0.jpg
                artistAPI = dz.api.get_artist(self.album.mainArtist.id)
                self.album.mainArtist.pic.md5 = artistAPI['picture_small'][artistAPI['picture_small'].find('artist/') + 7:-24]
            else:
                raise AlbumDoesntExists

            # Fill missing data
            if self.album.date and not self.date: self.date = self.album.date
            if not self.album.discTotal: self.album.discTotal = albumAPI_gw.get('NUMBER_DISK', "1")
            if not self.copyright: self.copyright = albumAPI_gw['COPYRIGHT']
            self.parseTrack(trackAPI)

        # Remove unwanted charaters in track name
        # Example: track/127793
        self.title = ' '.join(self.title.split())

        # Make sure there is at least one artist
        if not len(self.artist['Main']):
            self.artist['Main'] = [self.mainArtist['name']]

        self.singleDownload = trackAPI_gw.get('SINGLE_TRACK', False)
        self.position = trackAPI_gw.get('POSITION')

        # Add playlist data if track is in a playlist
        if playlistAPI: self.playlist = Playlist(playlistAPI)

        self.generateMainFeatStrings()
        return self

    def parseLocalTrackData(self, trackAPI_gw):
        # Local tracks has only the trackAPI_gw page and
        # contains only the tags provided by the file
        self.title = trackAPI_gw['SNG_TITLE']
        self.album = Album(title=trackAPI_gw['ALB_TITLE'])
        self.album.pic = Picture(
            md5 = trackAPI_gw.get('ALB_PICTURE', ""),
            type = "cover"
        )
        self.mainArtist = Artist(name=trackAPI_gw['ART_NAME'])
        self.artists = [trackAPI_gw['ART_NAME']]
        self.artist = {
            'Main': [trackAPI_gw['ART_NAME']]
        }
        self.album.artist = self.artist
        self.album.artists = self.artists
        self.album.date = self.date
        self.album.mainArtist = self.mainArtist
        self.date = Date()

    def parseTrackGW(self, trackAPI_gw):
        self.title = trackAPI_gw['SNG_TITLE'].strip()
        if trackAPI_gw.get('VERSION') and not trackAPI_gw['VERSION'] in trackAPI_gw['SNG_TITLE']:
            self.title += " " + trackAPI_gw['VERSION'].strip()

        self.discNumber = trackAPI_gw.get('DISK_NUMBER')
        self.explicit = bool(int(trackAPI_gw.get('EXPLICIT_LYRICS', "0")))
        self.copyright = trackAPI_gw.get('COPYRIGHT')
        if 'GAIN' in trackAPI_gw: self.replayGain = generateReplayGainString(trackAPI_gw['GAIN'])
        self.ISRC = trackAPI_gw.get('ISRC')
        self.trackNumber = trackAPI_gw['TRACK_NUMBER']
        self.contributors = trackAPI_gw['SNG_CONTRIBUTORS']

        self.lyrics = Lyrics(trackAPI_gw.get('LYRICS_ID', "0"))

        self.mainArtist = Artist(
            id = trackAPI_gw['ART_ID'],
            name = trackAPI_gw['ART_NAME'],
            pic_md5 = trackAPI_gw.get('ART_PICTURE')
        )

        if 'PHYSICAL_RELEASE_DATE' in trackAPI_gw:
            day = trackAPI_gw["PHYSICAL_RELEASE_DATE"][8:10]
            month = trackAPI_gw["PHYSICAL_RELEASE_DATE"][5:7]
            year = trackAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
            self.date = Date(year, month, day)

    def parseTrack(self, trackAPI):
        self.bpm = trackAPI['bpm']

        if not self.replayGain and 'gain' in trackAPI:
            self.replayGain = generateReplayGainString(trackAPI['gain'])
        if not self.explicit:
            self.explicit = trackAPI['explicit_lyrics']
        if not self.discNumber:
            self.discNumber = trackAPI['disk_number']

        for artist in trackAPI['contributors']:
            isVariousArtists = str(artist['id']) == VARIOUS_ARTISTS
            isMainArtist = artist['role'] == "Main"

            if len(trackAPI['contributors']) > 1 and isVariousArtists:
                continue

            if artist['name'] not in self.artists:
                self.artists.append(artist['name'])

            if isMainArtist or artist['name'] not in self.artist['Main'] and not isMainArtist:
                if not artist['role'] in self.artist:
                    self.artist[artist['role']] = []
                self.artist[artist['role']].append(artist['name'])

    def removeDuplicateArtists(self):
        (self.artist, self.artists) = removeDuplicateArtists(self.artist, self.artists)

    # Removes featuring from the title
    def getCleanTitle(self):
        return removeFeatures(self.title)

    def getFeatTitle(self):
        if self.featArtistsString and not "(feat." in self.title.lower():
            return self.title + " ({})".format(self.featArtistsString)
        return self.title

    def generateMainFeatStrings(self):
        self.mainArtistsString = andCommaConcat(self.artist['Main'])
        self.featArtistsString = ""
        if 'Featured' in self.artist:
            self.featArtistsString = "feat. "+andCommaConcat(self.artist['Featured'])

class TrackError(Exception):
    """Base class for exceptions in this module."""
    pass

class AlbumDoesntExists(TrackError):
    pass

class MD5NotFound(TrackError):
    pass

class NoDataToParse(TrackError):
    pass
