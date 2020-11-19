from deezer import Deezer
from deemix.app.settings import Settings
from deemix.app.queuemanager import QueueManager
from deemix.app.spotifyhelper import SpotifyHelper

class deemix:
    def __init__(self, configFolder=None, overwriteDownloadFolder=None):
        self.set = Settings(configFolder, overwriteDownloadFolder=overwriteDownloadFolder)
        self.dz = Deezer()
        self.dz.set_accept_language(self.set.settings.get('tagsLanguage'))
        self.sp = SpotifyHelper(configFolder)
        self.qm = QueueManager(self.sp)
