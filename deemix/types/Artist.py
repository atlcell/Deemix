from deemix.types.Picture import Picture
from deemix import VARIOUS_ARTISTS

class Artist:
    def __init__(self, id="0", name="", pic_md5="", role=""):
        self.id = str(id)
        self.name = name
        self.pic = Picture(md5=pic_md5, type="artist")
        self.role = ""
        self.save = True

    def isVariousArtists(self):
        return self.id == VARIOUS_ARTISTS
