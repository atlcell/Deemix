#!/usr/bin/env python3
from deemix.api.deezer import Deezer
from deemix.app.settings import Settings
from deemix.app.queuemanager import QueueManager
from deemix.app.spotify import SpotifyHelper

class deemix:
    def __init__(self):
        self.set = Settings()
        self.dz = Deezer()
        self.sp = SpotifyHelper()
        self.qm = QueueManager()
