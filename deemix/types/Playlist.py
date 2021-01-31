from deemix.types.Artist import Artist
from deemix.types.Date import Date
from deemix.types.Picture import Picture

class Playlist:
    def __init__(self, playlistAPI):
        if 'various_artist' in playlistAPI:
            playlistAPI['various_artist']['role'] = "Main"
            self.variousArtists = Artist(
                id = playlistAPI['various_artist']['id'],
                name = playlistAPI['various_artist']['name'],
                pic_md5 = playlistAPI['various_artist']['picture_small'][
                       playlistAPI['various_artist']['picture_small'].find('artist/') + 7:-24],
                role = playlistAPI['various_artist']['role']
            )
            self.mainArtist = self.variousArtists

        self.id = "pl_" + str(playlistAPI['id'])
        self.title = playlistAPI['title']
        self.rootArtist = None
        self.artist = {"Main": []}
        self.artists = []
        self.trackTotal = playlistAPI['nb_tracks']
        self.recordType = "compile"
        self.barcode = ""
        self.label = ""
        self.explicit = playlistAPI['explicit']
        self.genre = ["Compilation", ]

        year = playlistAPI["creation_date"][0:4]
        month = playlistAPI["creation_date"][5:7]
        day = playlistAPI["creation_date"][8:10]
        self.date = Date(year, month, day)

        self.discTotal = "1"
        self.playlistId = playlistAPI['id']
        self.owner = playlistAPI['creator']
        if 'dzcdn.net' in playlistAPI['picture_small']:
            url = playlistAPI['picture_small']
            picType = url[url.find('images/')+7:]
            picType = picType[:picType.find('/')]
            md5 = url[url.find(picType+'/') + len(picType)+1:-24]
            self.pic = Picture(
                md5 = md5,
                type = picType
            )
        else:
            self.pic = Picture(url = playlistAPI['picture_xl'])
