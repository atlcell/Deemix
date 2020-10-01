import eventlet
from eventlet.green.subprocess import call as execute

from os.path import sep as pathSep
from pathlib import Path
import re
import errno

requests = eventlet.import_patched('requests')
get = requests.get
request_exception = requests.exceptions

from ssl import SSLError
from os import makedirs
from tempfile import gettempdir

from deemix.app.queueitem import QISingle, QICollection
from deemix.app.track import Track, AlbumDoesntExsists
from deemix.utils import changeCase
from deemix.utils.pathtemplates import generateFilename, generateFilepath, settingsRegexAlbum, settingsRegexArtist, settingsRegexPlaylistFile
from deemix.api.deezer import USER_AGENT_HEADER
from deemix.utils.taggers import tagID3, tagFLAC

from Cryptodome.Cipher import Blowfish
from mutagen.flac import FLACNoHeaderError, error as FLACError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deemix')

TEMPDIR = Path(gettempdir()) / 'deemix-imgs'
if not TEMPDIR.is_dir():
    makedirs(TEMPDIR)

extensions = {
    9: '.flac',
    0: '.mp3',
    3: '.mp3',
    1: '.mp3',
    8: '.mp3',
    15: '.mp4',
    14: '.mp4',
    13: '.mp4'
}

errorMessages = {
    'notOnDeezer': "Track not available on Deezer!",
    'notEncoded': "Track not yet encoded!",
    'notEncodedNoAlternative': "Track not yet encoded and no alternative found!",
    'wrongBitrate': "Track not found at desired bitrate.",
    'wrongBitrateNoAlternative': "Track not found at desired bitrate and no alternative found!",
    'no360RA': "Track is not available in Reality Audio 360.",
    'notAvailable': "Track not available on deezer's servers!",
    'notAvailableNoAlternative': "Track not available on deezer's servers and no alternative found!",
    'noSpaceLeft': "No space left on target drive, clean up some space for the tracks",
    'albumDoesntExsists': "Track's album does not exsist, failed to gather info"
}

def downloadImage(url, path, overwrite="n"):
    if not path.is_file() or overwrite in ['y', 't', 'b']:
        try:
            image = get(url, headers={'User-Agent': USER_AGENT_HEADER}, timeout=30)
            image.raise_for_status()
            with open(path, 'wb') as f:
                f.write(image.content)
            return path
        except request_exception.HTTPError:
            if 'cdns-images.dzcdn.net' in url:
                urlBase = url[:url.rfind("/")+1]
                pictureUrl = url[len(urlBase):]
                pictureSize = int(pictureUrl[:pictureUrl.find("x")])
                if pictureSize > 1200:
                    logger.warn("Couldn't download "+str(pictureSize)+"x"+str(pictureSize)+" image, falling back to 1200x1200")
                    eventlet.sleep(1)
                    return  downloadImage(urlBase+pictureUrl.replace(str(pictureSize)+"x"+str(pictureSize), '1200x1200'), path, overwrite)
            logger.error("Image not found: "+url)
        except (request_exception.ConnectionError, request_exception.ChunkedEncodingError) as e:
            logger.error("Couldn't download Image, retrying in 5 seconds...: "+url+"\n")
            eventlet.sleep(5)
            return downloadImage(url, path, overwrite)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                raise DownloadFailed("noSpaceLeft")
            else:
                logger.exception(f"Error while downloading an image, you should report this to the developers: {str(e)}")
        except Exception as e:
            logger.exception(f"Error while downloading an image, you should report this to the developers: {str(e)}")
        if path.is_file(): path.unlink()
        return None
    else:
        return path

def formatDate(date, template):
    elements = {
        'year': ['YYYY', 'YY', 'Y'],
        'month': ['MM', 'M'],
        'day': ['DD', 'D']
    }
    for element, placeholders in elements.items():
        for placeholder in placeholders:
            if placeholder in template:
                template = template.replace(placeholder, str(date[element]))
    return template

class DownloadJob:
    def __init__(self, dz, queueItem, interface=None):
        self.dz = dz
        self.interface = interface
        self.queueItem = queueItem
        self.settings = queueItem.settings
        self.bitrate = queueItem.bitrate
        self.downloadPercentage = 0
        self.lastPercentage = 0
        self.extrasPath = None
        self.playlistCoverName = None
        self.playlistURLs = []

    def start(self):
        if not self.queueItem.cancel:
            if isinstance(self.queueItem, QISingle):
                result = self.downloadWrapper(self.queueItem.single)
                if result:
                    self.singleAfterDownload(result)
            elif isinstance(self.queueItem, QICollection):
                tracks = [None] * len(self.queueItem.collection)
                pool = eventlet.GreenPool(size=self.settings['queueConcurrency'])
                for pos, track in enumerate(self.queueItem.collection, start=0):
                    tracks[pos] = pool.spawn(self.downloadWrapper, track)
                pool.waitall()
                self.collectionAfterDownload(tracks)
        if self.interface:
            if self.queueItem.cancel:
                self.interface.send('currentItemCancelled', self.queueItem.uuid)
                self.interface.send("removedFromQueue", self.queueItem.uuid)
            else:
                self.interface.send("finishDownload", self.queueItem.uuid)
        return self.extrasPath

    def singleAfterDownload(self, result):
        if not self.extrasPath:
            self.extrasPath = Path(self.settings['downloadLocation'])
        # Save Album Cover
        if self.settings['saveArtwork'] and 'albumPath' in result:
            for image in result['albumURLs']:
                downloadImage(image['url'], result['albumPath'] / f"{result['albumFilename']}.{image['ext']}", self.settings['overwriteFile'])
        # Save Artist Artwork
        if self.settings['saveArtworkArtist'] and 'artistPath' in result:
            for image in result['artistURLs']:
                downloadImage(image['url'], result['artistPath'] / f"{result['artistFilename']}.{image['ext']}", self.settings['overwriteFile'])
        # Create searched logfile
        if self.settings['logSearched'] and 'searched' in result:
            with open(self.extrasPath / 'searched.txt', 'wb+') as f:
                orig = f.read().decode('utf-8')
                if not result['searched'] in orig:
                    if orig != "":
                        orig += "\r\n"
                    orig += result['searched'] + "\r\n"
                f.write(orig.encode('utf-8'))
        # Execute command after download
        if self.settings['executeCommand'] != "":
            execute(self.settings['executeCommand'].replace("%folder%", str(self.extrasPath)).replace("%filename%", result['filename']), shell=True)

    def collectionAfterDownload(self, tracks):
        if not self.extrasPath:
            self.extrasPath = Path(self.settings['downloadLocation'])
        playlist = [None] * len(tracks)
        errors = ""
        searched = ""

        for index in range(len(tracks)):
            result = tracks[index].wait()
            # Check if queue is cancelled
            if not result:
                return None
            # Log errors to file
            if 'error' in result:
                if not 'data' in result['error']:
                    result['error']['data'] = {'id': "0", 'title': 'Unknown', 'artist': 'Unknown'}
                errors += f"{result['error']['data']['id']} | {result['error']['data']['artist']} - {result['error']['data']['title']} | {result['error']['message']}\r\n"
            # Log searched to file
            if 'searched' in result:
                searched += result['searched'] + "\r\n"
            # Save Album Cover
            if self.settings['saveArtwork'] and 'albumPath' in result:
                for image in result['albumURLs']:
                    downloadImage(image['url'], result['albumPath'] / f"{result['albumFilename']}.{image['ext']}", self.settings['overwriteFile'])
            # Save Artist Artwork
            if self.settings['saveArtworkArtist'] and 'artistPath' in result:
                for image in result['artistURLs']:
                    downloadImage(image['url'], result['artistPath'] / f"{result['artistFilename']}.{image['ext']}", self.settings['overwriteFile'])
            # Save filename for playlist file
            playlist[index] = ""
            if 'filename' in result:
                playlist[index] = result['filename']

        # Create errors logfile
        if self.settings['logErrors'] and errors != "":
            with open(self.extrasPath / 'errors.txt', 'wb') as f:
                f.write(errors.encode('utf-8'))
        # Create searched logfile
        if self.settings['logSearched'] and searched != "":
            with open(self.extrasPath / 'searched.txt', 'wb') as f:
                f.write(searched.encode('utf-8'))
        # Save Playlist Artwork
        if self.settings['saveArtwork'] and self.playlistCoverName and not self.settings['tags']['savePlaylistAsCompilation']:
            for image in self.playlistURLs:
                downloadImage(image['url'], self.extrasPath / f"{self.playlistCoverName}.{image['ext']}", self.settings['overwriteFile'])
        # Create M3U8 File
        if self.settings['createM3U8File']:
            filename = settingsRegexPlaylistFile(self.settings['playlistFilenameTemplate'], self.queueItem, self.settings) or "playlist"
            with open(self.extrasPath / f'{filename}.m3u8', 'wb') as f:
                for line in playlist:
                    f.write((line + "\n").encode('utf-8'))
        # Execute command after download
        if self.settings['executeCommand'] != "":
            execute(self.settings['executeCommand'].replace("%folder%", str(self.extrasPath)), shell=True)

    def download(self, trackAPI_gw, track=None):
        result = {}
        if self.queueItem.cancel: raise DownloadCancelled

        if trackAPI_gw['SNG_ID'] == "0":
            raise DownloadFailed("notOnDeezer")

        # Create Track object
        if not track:
            logger.info(f"[{trackAPI_gw['ART_NAME']} - {trackAPI_gw['SNG_TITLE']}] Getting the tags")
            try:
                track = Track(self.dz,
                              settings=self.settings,
                              trackAPI_gw=trackAPI_gw,
                              trackAPI=trackAPI_gw['_EXTRA_TRACK'] if '_EXTRA_TRACK' in trackAPI_gw else None,
                              albumAPI=trackAPI_gw['_EXTRA_ALBUM'] if '_EXTRA_ALBUM' in trackAPI_gw else None
                              )
            except AlbumDoesntExsists:
                raise DownloadError('albumDoesntExsists')
            if self.queueItem.cancel: raise DownloadCancelled

        if track.MD5 == '':
            if track.fallbackId != "0":
                logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not yet encoded, using fallback id")
                newTrack = self.dz.get_track_gw(track.fallbackId)
                track.parseEssentialData(self.dz, newTrack)
                return self.download(trackAPI_gw, track)
            elif not track.searched and self.settings['fallbackSearch']:
                logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not yet encoded, searching for alternative")
                searchedId = self.dz.get_track_from_metadata(track.mainArtist['name'], track.title, track.album['title'])
                if searchedId != "0":
                    newTrack = self.dz.get_track_gw(searchedId)
                    track.parseEssentialData(self.dz, newTrack)
                    track.searched = True
                    if self.interface:
                        self.interface.send('queueUpdate', {
                            'uuid': self.queueItem.uuid,
                            'searchFallback': True,
                            'data': {
                                'id': track.id,
                                'title': track.title,
                                'artist': track.mainArtist['name']
                            },
                        })
                    return self.download(trackAPI_gw, track)
                else:
                    raise DownloadFailed("notEncodedNoAlternative")
            else:
                raise DownloadFailed("notEncoded")

        selectedFormat = self.getPreferredBitrate(track)
        if selectedFormat == -100:
            if track.fallbackId != "0":
                logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not found at desired bitrate, using fallback id")
                newTrack = self.dz.get_track_gw(track.fallbackId)
                track.parseEssentialData(self.dz, newTrack)
                return self.download(trackAPI_gw, track)
            elif not track.searched and self.settings['fallbackSearch']:
                logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not found at desired bitrate, searching for alternative")
                searchedId = self.dz.get_track_from_metadata(track.mainArtist['name'], track.title, track.album['title'])
                if searchedId != "0":
                    newTrack = self.dz.get_track_gw(searchedId)
                    track.parseEssentialData(self.dz, newTrack)
                    track.searched = True
                    if self.interface:
                        self.interface.send('queueUpdate', {
                            'uuid': self.queueItem.uuid,
                            'searchFallback': True,
                            'data': {
                                'id': track.id,
                                'title': track.title,
                                'artist': track.mainArtist['name']
                            },
                        })
                    return self.download(trackAPI_gw, track)
                else:
                    raise DownloadFailed("wrongBitrateNoAlternative")
            else:
                raise DownloadFailed("wrongBitrate")
        elif selectedFormat == -200:
            raise DownloadFailed("no360RA")
        track.selectedFormat = selectedFormat

        if self.settings['tags']['savePlaylistAsCompilation'] and track.playlist:
            track.trackNumber = track.position
            track.discNumber = "1"
            track.album = {**track.album, **track.playlist}
            if 'picType' in track.playlist:
                track.playlist['picUrl'] = "https://e-cdns-images.dzcdn.net/images/{}/{}/{}x{}-{}".format(
                    track.playlist['picType'],
                    track.playlist['pic'],
                    self.settings['embeddedArtworkSize'], self.settings['embeddedArtworkSize'],
                    'none-100-0-0.png' if self.settings['embeddedArtworkPNG'] else f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg'
                )
            else:
                track.playlist['picUrl'] = track.playlist['pic']
            ext = track.playlist['picUrl'][-4:]
            if ext[0] != ".":
                ext = ".jpg"
            track.album['picPath'] = TEMPDIR / f"pl{trackAPI_gw['_EXTRA_PLAYLIST']['id']}_{self.settings['embeddedArtworkSize']}{ext}"
        else:
            if track.album['date']:
                track.date = track.album['date']
            track.album['picUrl'] = "https://e-cdns-images.dzcdn.net/images/cover/{}/{}x{}-{}".format(
                track.album['pic'],
                self.settings['embeddedArtworkSize'], self.settings['embeddedArtworkSize'],
                'none-100-0-0.png' if self.settings['embeddedArtworkPNG'] else f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg'
            )
            track.album['picPath'] = TEMPDIR / f"alb{track.album['id']}_{self.settings['embeddedArtworkSize']}{track.album['picUrl'][-4:]}"
        track.album['bitrate'] = selectedFormat

        track.dateString = formatDate(track.date, self.settings['dateFormat'])
        track.album['dateString'] = formatDate(track.album['date'], self.settings['dateFormat'])
        if track.playlist: track.playlist['dateString'] = formatDate(track.playlist['date'], self.settings['dateFormat'])

        # Check if user wants the feat in the title
        # 0 => do not change
        # 1 => remove from title
        # 2 => add to title
        # 3 => remove from title and album title
        if self.settings['featuredToTitle'] == "1":
            track.title = track.getCleanTitle()
        elif self.settings['featuredToTitle'] == "2":
            track.title = track.getFeatTitle()
        elif self.settings['featuredToTitle'] == "3":
            track.title = track.getCleanTitle()
            track.album['title'] = track.getCleanAlbumTitle()

        # Remove (Album Version) from tracks that have that
        if self.settings['removeAlbumVersion']:
            if "Album Version" in track.title:
                track.title = re.sub(r' ?\(Album Version\)', "", track.title).strip()

        # Change Title and Artists casing if needed
        if self.settings['titleCasing'] != "nothing":
            track.title = changeCase(track.title, self.settings['titleCasing'])
        if self.settings['artistCasing'] != "nothing":
            track.mainArtist['name'] = changeCase(track.mainArtist['name'], self.settings['artistCasing'])
            for i, artist in enumerate(track.artists):
                track.artists[i] = changeCase(artist, self.settings['artistCasing'])
            for type in track.artist:
                for i, artist in enumerate(track.artist[type]):
                    track.artist[type][i] = changeCase(artist, self.settings['artistCasing'])
            track.generateMainFeatStrings()

        # Generate artist tag if needed
        if self.settings['tags']['multiArtistSeparator'] == "default":
            track.artistsString = ", ".join(track.artists)
        elif self.settings['tags']['multiArtistSeparator'] == "andFeat":
            track.artistsString = track.mainArtistsString
            if track.featArtistsString and str(self.settings['featuredToTitle']) != "2":
                track.artistsString += " " + track.featArtistsString
        else:
            track.artistsString = self.settings['tags']['multiArtistSeparator'].join(track.artists)


        # Generate filename and filepath from metadata
        filename = generateFilename(track, self.settings, trackAPI_gw['FILENAME_TEMPLATE'])
        (filepath, artistPath, coverPath, extrasPath) = generateFilepath(track, self.settings)

        if self.queueItem.cancel: raise DownloadCancelled

        # Download and cache coverart
        logger.info(f"[{track.mainArtist['name']} - {track.title}] Getting the album cover")
        track.album['picPath'] = downloadImage(track.album['picUrl'], track.album['picPath'])

        # Save local album art
        if coverPath:
            result['albumURLs'] = []
            for format in self.settings['localArtworkFormat'].split(","):
                if format in ["png","jpg"]:
                    if self.settings['tags']['savePlaylistAsCompilation'] and track.playlist:
                        if track.playlist['picType']:
                            url = "https://e-cdns-images.dzcdn.net/images/{}/{}/{}x{}-{}".format(
                                track.album['picType'],
                                track.album['pic'],
                                self.settings['localArtworkSize'], self.settings['localArtworkSize'],
                                'none-100-0-0.png' if format == "png" else f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg'
                            )
                        else:
                            url = track.album['pic']
                            if format != "jpg":
                                continue
                    else:
                        url = "https://e-cdns-images.dzcdn.net/images/cover/{}/{}x{}-{}".format(
                            track.album['pic'],
                            self.settings['localArtworkSize'], self.settings['localArtworkSize'],
                            'none-100-0-0.png' if format == "png" else f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg'
                        )
                    result['albumURLs'].append({'url': url, 'ext': format})
            result['albumPath'] = coverPath
            result['albumFilename'] = f"{settingsRegexAlbum(self.settings['coverImageTemplate'], track.album, self.settings, track.playlist)}"

        # Save artist art
        if artistPath:
            result['artistURLs'] = []
            for format in self.settings['localArtworkFormat'].split(","):
                if format in ["png","jpg"]:
                    url = ""
                    if track.album['mainArtist']['pic'] != "":
                        url = "https://e-cdns-images.dzcdn.net/images/artist/{}/{}x{}-{}".format(
                            track.album['mainArtist']['pic'], self.settings['localArtworkSize'], self.settings['localArtworkSize'],
                            'none-100-0-0.png' if format == "png" else f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg')
                    elif format == "jpg":
                        url = "https://e-cdns-images.dzcdn.net/images/artist//{}x{}-{}".format(
                            self.settings['localArtworkSize'], self.settings['localArtworkSize'], f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg')
                    if url:
                        result['artistURLs'].append({'url': url, 'ext': format})
            result['artistPath'] = artistPath
            result['artistFilename'] = f"{settingsRegexArtist(self.settings['artistImageTemplate'], track.album['mainArtist'], self.settings)}"

        # Remove subfolders from filename and add it to filepath
        if pathSep in filename:
            tempPath = filename[:filename.rfind(pathSep)]
            filepath = filepath / tempPath
            filename = filename[filename.rfind(pathSep) + len(pathSep):]

        # Make sure the filepath exsists
        makedirs(filepath, exist_ok=True)
        writepath = filepath / f"{filename}{extensions[track.selectedFormat]}"

        # Save lyrics in lrc file
        if self.settings['syncedLyrics'] and track.lyrics['sync']:
            if not (filepath / f"{filename}.lrc").is_file() or self.settings['overwriteFile'] in ['y', 't']:
                with open(filepath / f"{filename}.lrc", 'wb') as f:
                    f.write(track.lyrics['sync'].encode('utf-8'))

        trackAlreadyDownloaded = writepath.is_file()
        if not trackAlreadyDownloaded and self.settings['overwriteFile'] == 'e':
            exts = ['.mp3', '.flac', '.opus', '.m4a']
            baseFilename = str(filepath / filename)
            for ext in exts:
                trackAlreadyDownloaded = Path(baseFilename+ext).is_file()
                if trackAlreadyDownloaded:
                    break
        if trackAlreadyDownloaded and self.settings['overwriteFile'] == 'b':
            baseFilename = str(filepath / filename)
            i = 1
            currentFilename = baseFilename+' ('+str(i)+')'+ extensions[track.selectedFormat]
            while Path(currentFilename).is_file():
                i += 1
                currentFilename = baseFilename+' ('+str(i)+')'+ extensions[track.selectedFormat]
            trackAlreadyDownloaded = False
            writepath = Path(currentFilename)


        if extrasPath:
            if not self.extrasPath: self.extrasPath = extrasPath
            result['filename'] = str(writepath)[len(str(extrasPath))+ len(pathSep):]

        # Save playlist cover
        if track.playlist:
            if not len(self.playlistURLs):
                if track.playlist['picType']:
                    for format in self.settings['localArtworkFormat'].split(","):
                        if format in ["png","jpg"]:
                            url = "https://e-cdns-images.dzcdn.net/images/{}/{}/{}x{}-{}".format(
                                track.playlist['picType'],
                                track.playlist['pic'],
                                self.settings['localArtworkSize'], self.settings['localArtworkSize'],
                                'none-100-0-0.png' if format == "png" else f'000000-{self.settings["jpegImageQuality"]}-0-0.jpg'
                            )
                            self.playlistURLs.append({'url': url, 'ext': format})
                else:
                    self.playlistURLs.append({'url': track.playlist['pic'], 'ext': 'jpg'})
            if not self.playlistCoverName:
                track.playlist['id'] = "pl_" + str(trackAPI_gw['_EXTRA_PLAYLIST']['id'])
                track.playlist['genre'] = ["Compilation", ]
                track.playlist['bitrate'] = selectedFormat
                track.playlist['dateString'] = formatDate(track.playlist['date'], self.settings['dateFormat'])
                self.playlistCoverName = f"{settingsRegexAlbum(self.settings['coverImageTemplate'], track.playlist, self.settings, track.playlist)}"

        if not trackAlreadyDownloaded or self.settings['overwriteFile'] == 'y':
            logger.info(f"[{track.mainArtist['name']} - {track.title}] Downloading the track")
            track.downloadUrl = self.dz.get_track_stream_url(track.id, track.MD5, track.mediaVersion, track.selectedFormat)

            def downloadMusic(track, trackAPI_gw):
                try:
                    with open(writepath, 'wb') as stream:
                        self.streamTrack(stream, track)
                except DownloadCancelled:
                    if writepath.is_file(): writepath.unlink()
                    raise DownloadCancelled
                except (request_exception.HTTPError, DownloadEmpty):
                    if writepath.is_file(): writepath.unlink()
                    if track.fallbackId != "0":
                        logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not available, using fallback id")
                        newTrack = self.dz.get_track_gw(track.fallbackId)
                        track.parseEssentialData(self.dz, newTrack)
                        return False
                    elif not track.searched and self.settings['fallbackSearch']:
                        logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not available, searching for alternative")
                        searchedId = self.dz.get_track_from_metadata(track.mainArtist['name'], track.title, track.album['title'])
                        if searchedId != "0":
                            newTrack = self.dz.get_track_gw(searchedId)
                            track.parseEssentialData(self.dz, newTrack)
                            track.searched = True
                            if self.interface:
                                self.interface.send('queueUpdate', {
                                    'uuid': self.queueItem.uuid,
                                    'searchFallback': True,
                                    'data': {
                                        'id': track.id,
                                        'title': track.title,
                                        'artist': track.mainArtist['name']
                                    },
                                })
                            return False
                        else:
                            raise DownloadFailed("notAvailableNoAlternative")
                    else:
                        raise DownloadFailed("notAvailable")
                except (request_exception.ConnectionError, request_exception.ChunkedEncodingError) as e:
                    if writepath.is_file(): writepath.unlink()
                    logger.warn(f"[{track.mainArtist['name']} - {track.title}] Error while downloading the track, trying again in 5s...")
                    eventlet.sleep(5)
                    return downloadMusic(track, trackAPI_gw)
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        raise DownloadFailed("noSpaceLeft")
                    else:
                        if writepath.is_file(): writepath.unlink()
                        logger.exception(f"[{track.mainArtist['name']} - {track.title}] Error while downloading the track, you should report this to the developers: {str(e)}")
                        raise e
                except Exception as e:
                    if writepath.is_file(): writepath.unlink()
                    logger.exception(f"[{track.mainArtist['name']} - {track.title}] Error while downloading the track, you should report this to the developers: {str(e)}")
                    raise e
                return True

            try:
                trackDownloaded = downloadMusic(track, trackAPI_gw)
            except DownloadFailed as e:
                raise e
            except Exception as e:
                raise e

            if not trackDownloaded:
                return self.download(trackAPI_gw, track)
        else:
            logger.info(f"[{track.mainArtist['name']} - {track.title}] Skipping track as it's already downloaded")
            self.completeTrackPercentage()

        # Adding tags
        if (not trackAlreadyDownloaded or self.settings['overwriteFile'] in ['t', 'y']) and not track.localTrack:
            logger.info(f"[{track.mainArtist['name']} - {track.title}] Applying tags to the track")
            if track.selectedFormat in [3, 1, 8]:
                tagID3(writepath, track, self.settings['tags'])
            elif track.selectedFormat == 9:
                try:
                    tagFLAC(writepath, track, self.settings['tags'])
                except (FLACNoHeaderError, FLACError):
                    if writepath.is_file(): writepath.unlink()
                    logger.warn(f"[{track.mainArtist['name']} - {track.title}] Track not available in FLAC, falling back if necessary")
                    self.removeTrackPercentage()
                    track.filesizes['FILESIZE_FLAC'] = "0"
                    track.filesizes['FILESIZE_FLAC_TESTED'] = True
                    return self.download(trackAPI_gw, track)
            if track.searched:
                result['searched'] = f"{track.mainArtist['name']} - {track.title}"

        logger.info(f"[{track.mainArtist['name']} - {track.title}] Track download completed\n{str(writepath)}")
        self.queueItem.downloaded += 1
        self.queueItem.files.append(str(writepath))
        self.queueItem.extrasPath = str(self.extrasPath)
        if self.interface:
            self.interface.send("updateQueue", {'uuid': self.queueItem.uuid, 'downloaded': True, 'downloadPath': str(writepath), 'extrasPath': str(self.extrasPath)})
        return result

    def getPreferredBitrate(self, track):
        if track.localTrack:
            return 0

        fallback = self.settings['fallbackBitrate']
        falledBack = False

        formats_non_360 = {
            9: "FLAC",
            3: "MP3_320",
            1: "MP3_128",
        }
        formats_360 = {
            15: "MP4_RA3",
            14: "MP4_RA2",
            13: "MP4_RA1",
        }

        if not fallback:
            error_num = -100
            formats = formats_360
            formats.update(formats_non_360)
        elif int(self.bitrate) in formats_360:
            error_num = -200
            formats = formats_360
        else:
            error_num = 8
            formats = formats_non_360

        for format_num, format in formats.items():
            if format_num <= int(self.bitrate):
                if f"FILESIZE_{format}" in track.filesizes:
                    if int(track.filesizes[f"FILESIZE_{format}"]) != 0:
                        return format_num
                    elif not track.filesizes[f"FILESIZE_{format}_TESTED"]:
                        request = requests.head(self.dz.get_track_stream_url(track.id, track.MD5, track.mediaVersion, format_num), headers={'User-Agent': USER_AGENT_HEADER}, timeout=30)
                        try:
                            request.raise_for_status()
                            return format_num
                        except request_exception.HTTPError: # if the format is not available, Deezer returns a 403 error
                            pass
                if fallback:
                    if not falledBack:
                        falledBack = True
                        logger.info(f"[{track.mainArtist['name']} - {track.title}] Fallback to lower bitrate")
                        if self.interface:
                            self.interface.send('queueUpdate', {
                                'uuid': self.queueItem.uuid,
                                'bitrateFallback': True,
                                'data': {
                                    'id': track.id,
                                    'title': track.title,
                                    'artist': track.mainArtist['name']
                                },
                            })
                    continue
                else:
                    return error_num

        return error_num # fallback is enabled and loop went through all formats

    def streamTrack(self, stream, track, start=0):
        if self.queueItem.cancel: raise DownloadCancelled

        headers=dict(self.dz.http_headers)
        if range != 0:
            headers['Range'] = f'bytes={start}-'
        chunkLength = start
        percentage = 0

        itemName = f"[{track.mainArtist['name']} - {track.title}]"

        try:
            with self.dz.session.get(track.downloadUrl, headers=headers, stream=True, timeout=10) as request:
                request.raise_for_status()

                blowfish_key = str.encode(self.dz._get_blowfish_key(str(track.id)))

                complete = int(request.headers["Content-Length"])
                if complete == 0:
                    raise DownloadEmpty
                if start != 0:
                    responseRange = request.headers["Content-Range"]
                    logger.info(f'{itemName} downloading range {responseRange}')
                else:
                    logger.info(f'{itemName} downloading {complete} bytes')

                for chunk in request.iter_content(2048 * 3):
                    if self.queueItem.cancel: raise DownloadCancelled

                    if len(chunk) >= 2048:
                        chunk = Blowfish.new(blowfish_key, Blowfish.MODE_CBC, b"\x00\x01\x02\x03\x04\x05\x06\x07").decrypt(chunk[0:2048]) + chunk[2048:]

                    stream.write(chunk)
                    chunkLength += len(chunk)

                    if isinstance(self.queueItem, QISingle):
                        percentage = (chunkLength / (complete + start)) * 100
                        self.downloadPercentage = percentage
                    else:
                        chunkProgres = (len(chunk) / (complete + start)) / self.queueItem.size * 100
                        self.downloadPercentage += chunkProgres

                    self.updatePercentage()

        except SSLError as e:
            logger.info(f'{itemName} retrying from byte {chunkLength}')
            return self.streamTrack(stream, track, chunkLength)
        except (request_exception.ConnectionError, requests.exceptions.ReadTimeout):
            eventlet.sleep(2)
            return self.streamTrack(stream, track, start)

    def updatePercentage(self):
        if round(self.downloadPercentage) != self.lastPercentage and round(self.downloadPercentage) % 2 == 0:
            self.lastPercentage = round(self.downloadPercentage)
            self.queueItem.progress = self.lastPercentage
            if self.interface:
                self.interface.send("updateQueue", {'uuid': self.queueItem.uuid, 'progress': self.lastPercentage})

    def completeTrackPercentage(self):
        if isinstance(self.queueItem, QISingle):
            self.downloadPercentage = 100
        else:
            self.downloadPercentage += (1 / self.queueItem.size) * 100
        self.updatePercentage()

    def removeTrackPercentage(self):
        if isinstance(self.queueItem, QISingle):
            self.downloadPercentage = 0
        else:
            self.downloadPercentage -= (1 / self.queueItem.size) * 100
        self.updatePercentage()

    def downloadWrapper(self, trackAPI_gw):
        track = {
            'id': trackAPI_gw['SNG_ID'],
            'title': trackAPI_gw['SNG_TITLE'] + (trackAPI_gw['VERSION'] if 'VERSION' in trackAPI_gw and trackAPI_gw['VERSION'] and not trackAPI_gw['VERSION'] in trackAPI_gw['SNG_TITLE'] else ""),
            'artist': trackAPI_gw['ART_NAME']
        }

        try:
            result = self.download(trackAPI_gw)
        except DownloadCancelled:
            return None
        except DownloadFailed as error:
            logger.error(f"[{track['artist']} - {track['title']}] {error.message}")
            result = {'error': {
                        'message': error.message,
                        'errid': error.errid,
                        'data': track
                    }}
        except Exception as e:
            logger.exception(f"[{track['artist']} - {track['title']}] {str(e)}")
            result = {'error': {
                        'message': str(e),
                        'data': track
                    }}

        if 'error' in result:
            self.completeTrackPercentage()
            self.queueItem.failed += 1
            self.queueItem.errors.append(result['error'])
            if self.interface:
                error = result['error']
                self.interface.send("updateQueue", {
                    'uuid': self.queueItem.uuid,
                    'failed': True,
                    'data': error['data'],
                    'error': error['message'],
                    'errid': error['errid'] if 'errid' in error else None
                })
        return result

class DownloadError(Exception):
    """Base class for exceptions in this module."""
    pass

class DownloadFailed(DownloadError):
    def __init__(self, errid):
        self.errid = errid
        self.message = errorMessages[self.errid]

class DownloadCancelled(DownloadError):
    pass

class DownloadEmpty(DownloadError):
    pass
