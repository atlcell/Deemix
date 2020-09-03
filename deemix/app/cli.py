#!/usr/bin/env python3
import os.path as path
from os import makedirs

from deemix.app import deemix

class cli(deemix):
    def __init__(self, path, configFolder=None):
        super().__init__(configFolder)
        if path:
            self.set.settings['downloadLocation'] = str(path)
            makedirs(path, exist_ok=True)
            print("Using folder: "+self.set.settings['downloadLocation'])

    def downloadLink(self, url, bitrate=None):
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    self.qm.addToQueue(self.dz, self.sp, l, self.set.settings, bitrate)
            else:
                self.qm.addToQueue(self.dz, self.sp, link, self.set.settings, bitrate)

    def requestValidArl(self):
        while True:
            arl = input("Paste here your arl:")
            if self.dz.login_via_arl(arl):
                break
        return arl

    def login(self):
        configFolder = self.set.configFolder
        if not path.isdir(configFolder):
            makedirs(configFolder, exist_ok=True)
        if path.isfile(path.join(configFolder, '.arl')):
            with open(path.join(configFolder, '.arl'), 'r') as f:
                arl = f.readline().rstrip("\n")
            if not self.dz.login_via_arl(arl):
                arl = self.requestValidArl()
        else:
            arl = self.requestValidArl()
        with open(path.join(configFolder, '.arl'), 'w') as f:
            f.write(arl)
