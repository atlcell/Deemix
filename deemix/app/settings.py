import json
from pathlib import Path
from os import makedirs, listdir
from deemix import __version__ as deemixVersion
from deezer import TrackFormats
from deemix.utils import checkFolder
import logging
import datetime
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

import deemix.utils.localpaths as localpaths

class OverwriteOption():
    """Should the lib overwrite files?"""

    OVERWRITE = 'y'
    """Yes, overwrite the file"""

    DONT_OVERWRITE = 'n'
    """No, don't overwrite the file"""

    DONT_CHECK_EXT = 'e'
    """No, and don't check for extensions"""

    KEEP_BOTH = 'b'
    """No, and keep both files"""

    ONLY_TAGS = 't'
    """Overwrite only the tags"""

class FeaturesOption():
    """What should I do with featured artists?"""

    NO_CHANGE = "0"
    """Do nothing"""

    REMOVE_TITLE = "1"
    """Remove from track title"""

    REMOVE_TITLE_ALBUM = "3"
    """Remove from track title and album title"""

    MOVE_TITLE = "2"
    """Move to track title"""

DEFAULT_SETTINGS = {
  "downloadLocation": str(localpaths.getMusicFolder()),
  "tracknameTemplate": "%artist% - %title%",
  "albumTracknameTemplate": "%tracknumber% - %title%",
  "playlistTracknameTemplate": "%position% - %artist% - %title%",
  "createPlaylistFolder": True,
  "playlistNameTemplate": "%playlist%",
  "createArtistFolder": False,
  "artistNameTemplate": "%artist%",
  "createAlbumFolder": True,
  "albumNameTemplate": "%artist% - %album%",
  "createCDFolder": True,
  "createStructurePlaylist": False,
  "createSingleFolder": False,
  "padTracks": True,
  "paddingSize": "0",
  "illegalCharacterReplacer": "_",
  "queueConcurrency": 3,
  "maxBitrate": str(TrackFormats.MP3_320),
  "fallbackBitrate": True,
  "fallbackSearch": False,
  "logErrors": True,
  "logSearched": False,
  "saveDownloadQueue": False,
  "overwriteFile": OverwriteOption.DONT_OVERWRITE,
  "createM3U8File": False,
  "playlistFilenameTemplate": "playlist",
  "syncedLyrics": False,
  "embeddedArtworkSize": 800,
  "embeddedArtworkPNG": False,
  "localArtworkSize": 1400,
  "localArtworkFormat": "jpg",
  "saveArtwork": True,
  "coverImageTemplate": "cover",
  "saveArtworkArtist": False,
  "artistImageTemplate": "folder",
  "jpegImageQuality": 80,
  "dateFormat": "Y-M-D",
  "albumVariousArtists": True,
  "removeAlbumVersion": False,
  "removeDuplicateArtists": False,
  "tagsLanguage": "",
  "featuredToTitle": FeaturesOption.NO_CHANGE,
  "titleCasing": "nothing",
  "artistCasing": "nothing",
  "executeCommand": "",
  "tags": {
    "title": True,
    "artist": True,
    "album": True,
    "cover": True,
    "trackNumber": True,
    "trackTotal": False,
    "discNumber": True,
    "discTotal": False,
    "albumArtist": True,
    "genre": True,
    "year": True,
    "date": True,
    "explicit": False,
    "isrc": True,
    "length": True,
    "barcode": True,
    "bpm": True,
    "replayGain": False,
    "label": True,
    "lyrics": False,
    "syncedLyrics": False,
    "copyright": False,
    "composer": False,
    "involvedPeople": False,
    "source": False,
    "savePlaylistAsCompilation": False,
    "useNullSeparator": False,
    "saveID3v1": True,
    "multiArtistSeparator": "default",
    "singleAlbumArtist": False,
    "coverDescriptionUTF8": False
  }
}

class Settings:
    def __init__(self, configFolder=None, overwriteDownloadFolder=None):
        self.settings = {}
        self.configFolder = Path(configFolder or localpaths.getConfigFolder())

        # Create config folder if it doesn't exsist
        makedirs(self.configFolder, exist_ok=True)

        # Create config file if it doesn't exsist
        if not (self.configFolder / 'config.json').is_file():
            with open(self.configFolder / 'config.json', 'w') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)

        # Read config file
        with open(self.configFolder / 'config.json', 'r') as configFile:
            self.settings = json.load(configFile)

        # Check for overwriteDownloadFolder
        # This prevents the creation of the original download folder when
        # using overwriteDownloadFolder
        originalDownloadFolder = self.settings['downloadLocation']
        if overwriteDownloadFolder:
            overwriteDownloadFolder = str(overwriteDownloadFolder)
            self.settings['downloadLocation'] = overwriteDownloadFolder

        # Make sure the download path exsits, fallback to default
        invalidDownloadFolder = False
        if self.settings['downloadLocation'] == "" or not checkFolder(self.settings['downloadLocation']):
            self.settings['downloadLocation'] = DEFAULT_SETTINGS['downloadLocation']
            originalDownloadFolder = self.settings['downloadLocation']
            invalidDownloadFolder = True

        # Check the settings and save them if something changed
        if self.settingsCheck() > 0 or invalidDownloadFolder:
            makedirs(self.settings['downloadLocation'], exist_ok=True)
            self.settings['downloadLocation'] = originalDownloadFolder # Prevents the saving of the overwritten path
            self.saveSettings()
            self.settings['downloadLocation'] = overwriteDownloadFolder or originalDownloadFolder # Restores the correct path

        # LOGFILES

        # Create logfile name and path
        logspath = self.configFolder / 'logs'
        now = datetime.datetime.now()
        logfile = now.strftime("%Y-%m-%d_%H%M%S")+".log"
        makedirs(logspath, exist_ok=True)

        # Add handler for logging
        fh = logging.FileHandler(logspath / logfile, 'w', 'utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] %(message)s'))
        logger.addHandler(fh)
        logger.info(f"{platform.platform(True, True)} - Python {platform.python_version()}, deemix {deemixVersion}")

        # Only keep last 5 logfiles (to preserve disk space)
        logslist = listdir(logspath)
        logslist.sort()
        if len(logslist)>5:
            for i in range(len(logslist)-5):
                (logspath / logslist[i]).unlink()

    # Saves the settings
    def saveSettings(self, newSettings=None, dz=None):
        if newSettings:
            if dz and newSettings.get('tagsLanguage') != self.settings.get('tagsLanguage'): dz.set_accept_language(newSettings.get('tagsLanguage'))
            if newSettings.get('downloadLocation') != self.settings.get('downloadLocation') and not checkFolder(newSettings.get('downloadLocation')):
                    newSettings['downloadLocation'] = DEFAULT_SETTINGS['downloadLocation']
                    makedirs(newSettings['downloadLocation'], exist_ok=True)
            self.settings = newSettings
        with open(self.configFolder / 'config.json', 'w') as configFile:
            json.dump(self.settings, configFile, indent=2)

    # Checks if the default settings have changed
    def settingsCheck(self):
        changes = 0
        for set in DEFAULT_SETTINGS:
            if not set in self.settings or type(self.settings[set]) != type(DEFAULT_SETTINGS[set]):
                self.settings[set] = DEFAULT_SETTINGS[set]
                changes += 1
        for set in DEFAULT_SETTINGS['tags']:
            if not set in self.settings['tags'] or type(self.settings['tags'][set]) != type(DEFAULT_SETTINGS['tags'][set]):
                self.settings['tags'][set] = DEFAULT_SETTINGS['tags'][set]
                changes += 1
        if self.settings['downloadLocation'] == "":
            self.settings['downloadLocation'] = DEFAULT_SETTINGS['downloadLocation']
            changes += 1
        for template in ['tracknameTemplate', 'albumTracknameTemplate', 'playlistTracknameTemplate', 'playlistNameTemplate', 'artistNameTemplate', 'albumNameTemplate', 'playlistFilenameTemplate', 'coverImageTemplate', 'artistImageTemplate', 'paddingSize']:
            if self.settings[template] == "":
                self.settings[template] = DEFAULT_SETTINGS[template]
                changes += 1
        return changes
