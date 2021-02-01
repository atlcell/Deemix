from deezer.gw import LyricsStatus

from deemix.utils import removeDuplicateArtists, removeFeatures
from deemix.types.Artist import Artist
from deemix.types.Date import Date
from deemix.types.Picture import Picture
from deemix import VARIOUS_ARTISTS

class Album:
    def __init__(self, id="0", title="", pic_md5=""):
        self.id = id
        self.title = title
        self.pic = Picture(md5=pic_md5, type="cover")
        self.artist = {"Main": []}
        self.artists = []
        self.mainArtist = None
        self.dateString = None
        self.barcode = "Unknown"
        self.date = None
        self.discTotal = "0"
        self.embeddedCoverPath = None
        self.embeddedCoverURL = None
        self.explicit = False
        self.genre = []
        self.label = "Unknown"
        self.recordType = "album"
        self.rootArtist = None
        self.trackTotal = "0"
        self.bitrate = 0
        self.variousArtists = None

    def parseAlbum(self, albumAPI):
        self.title = albumAPI['title']

        # Getting artist image ID
        # ex: https://e-cdns-images.dzcdn.net/images/artist/f2bc007e9133c946ac3c3907ddc5d2ea/56x56-000000-80-0-0.jpg
        artistPicture = albumAPI['artist']['picture_small']
        artistPicture = artistPicture[artistPicture.find('artist/') + 7:-24]
        self.mainArtist = Artist(
            id = albumAPI['artist']['id'],
            name = albumAPI['artist']['name'],
            pic_md5 = artistPicture
        )
        if albumAPI.get('root_artist'):
            self.rootArtist = Artist(
                id = albumAPI['root_artist']['id'],
                name = albumAPI['root_artist']['name']
            )

        for artist in albumAPI['contributors']:
            isVariousArtists = str(artist['id']) == VARIOUS_ARTISTS
            isMainArtist = artist['role'] == "Main"

            if isVariousArtists:
                self.variousArtists = Artist(
                    id = artist['id'],
                    name = artist['name'],
                    role = artist['role']
                )
                continue

            if artist['name'] not in self.artists:
                self.artists.append(artist['name'])

            if isMainArtist or artist['name'] not in self.artist['Main'] and not isMainArtist:
                if not artist['role'] in self.artist:
                    self.artist[artist['role']] = []
                self.artist[artist['role']].append(artist['name'])

        self.trackTotal = albumAPI['nb_tracks']
        self.recordType = albumAPI['record_type']

        self.barcode = albumAPI.get('upc', self.barcode)
        self.label = albumAPI.get('label', self.label)
        self.explicit = bool(albumAPI.get('explicit_lyrics', False))
        if 'release_date' in albumAPI:
            day = albumAPI["release_date"][8:10]
            month = albumAPI["release_date"][5:7]
            year = albumAPI["release_date"][0:4]
            self.date = Date(year, month, day)

        self.discTotal = albumAPI.get('nb_disk')
        self.copyright = albumAPI.get('copyright')

        if not self.pic.md5:
            # Getting album cover MD5
            # ex: https://e-cdns-images.dzcdn.net/images/cover/2e018122cb56986277102d2041a592c8/56x56-000000-80-0-0.jpg
            self.pic.md5 = albumAPI['cover_small'][albumAPI['cover_small'].find('cover/') + 6:-24]

        if albumAPI.get('genres') and len(albumAPI['genres'].get('data', [])) > 0:
            for genre in albumAPI['genres']['data']:
                self.genre.append(genre['name'])

    def parseAlbumGW(self, albumAPI_gw):
        self.title = albumAPI_gw['ALB_TITLE']
        self.mainArtist = Artist(
            id = albumAPI_gw['ART_ID'],
            name = albumAPI_gw['ART_NAME']
        )

        self.artists = [albumAPI_gw['ART_NAME']]
        self.trackTotal = albumAPI_gw['NUMBER_TRACK']
        self.discTotal = albumAPI_gw['NUMBER_DISK']
        self.label = albumAPI_gw.get('LABEL_NAME', self.label)

        explicitLyricsStatus = albumAPI_gw.get('EXPLICIT_ALBUM_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN)
        self.explicit = explicitLyricsStatus in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]

        if not self.pic.md5:
            self.pic.md5 = albumAPI_gw['ALB_PICTURE']
        if 'PHYSICAL_RELEASE_DATE' in albumAPI_gw:
            day = albumAPI_gw["PHYSICAL_RELEASE_DATE"][8:10]
            month = albumAPI_gw["PHYSICAL_RELEASE_DATE"][5:7]
            year = albumAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
            self.date = Date(year, month, day)

    def makePlaylistCompilation(self, playlist):
        self.variousArtists = playlist.variousArtists
        self.mainArtist = playlist.mainArtist
        self.title = playlist.title
        self.rootArtist = playlist.rootArtist
        self.artist = playlist.artist
        self.artists = playlist.artists
        self.trackTotal = playlist.trackTotal
        self.recordType = playlist.recordType
        self.barcode = playlist.barcode
        self.label = playlist.label
        self.explicit = playlist.explicit
        self.date = playlist.date
        self.discTotal = playlist.discTotal
        self.playlistId = playlist.playlistId
        self.owner = playlist.owner
        self.pic = playlist.pic

    def removeDuplicateArtists(self):
        (self.artist, self.artists) = removeDuplicateArtists(self.artist, self.artists)

    # Removes featuring from the album name
    def getCleanTitle(self):
        return removeFeatures(self.title)
