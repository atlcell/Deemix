from pathlib import Path
from os import makedirs

from deemix.app import deemix
from deemix.utils import checkFolder

class cli(deemix):
    def __init__(self, downloadpath, configFolder=None):
        super().__init__(configFolder, overwriteDownloadFolder=downloadpath)
        if downloadpath:
            print("Using folder: "+self.set.settings['downloadLocation'])

    def downloadLink(self, url, bitrate=None):
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    self.qm.addToQueue(self.dz, l, self.set.settings, bitrate)
            else:
                self.qm.addToQueue(self.dz, link, self.set.settings, bitrate)

    def requestValidArl(self):
        while True:
            arl = input("Paste here your arl:")
            if self.dz.login_via_arl(arl):
                break
        return arl

    def login(self):
        configFolder = Path(self.set.configFolder)
        if not configFolder.is_dir():
            makedirs(configFolder, exist_ok=True)
        if (configFolder / '.arl').is_file():
            with open(configFolder / '.arl', 'r') as f:
                arl = f.readline().rstrip("\n")
            if not self.dz.login_via_arl(arl):
                arl = self.requestValidArl()
        else:
            arl = self.requestValidArl()
        with open(configFolder / '.arl', 'w') as f:
            f.write(arl)
