import re
from os.path import sep as pathSep
from pathlib import Path
from unicodedata import normalize
from deezer import TrackFormats

bitrateLabels = {
    TrackFormats.MP4_RA3: "360 HQ",
    TrackFormats.MP4_RA2: "360 MQ",
    TrackFormats.MP4_RA1: "360 LQ",
    TrackFormats.FLAC   : "FLAC",
    TrackFormats.MP3_320: "320",
    TrackFormats.MP3_128: "128",
    TrackFormats.DEFAULT: "128",
    TrackFormats.LOCAL  : "MP3"
}

def fixName(txt, char='_'):
    txt = str(txt)
    txt = re.sub(r'[\0\/\\:*?"<>|]', char, txt)
    txt = normalize("NFC", txt)
    return txt

def fixEndOfData(bString):
    try:
        bString.decode()
        return True
    except:
        return False

def fixLongName(name):
    if pathSep in name:
        sepName = name.split(pathSep)
        name = ""
        for txt in sepName:
            txt = fixLongName(txt)
            name += txt + pathSep
        name = name[:-1]
    else:
        name = name.encode('utf-8')[:200]
        while not fixEndOfData(name):
            name = name[:-1]
        name = name.decode()
    return name


def antiDot(string):
    while string[-1:] == "." or string[-1:] == " " or string[-1:] == "\n":
        string = string[:-1]
    if len(string) < 1:
        string = "dot"
    return string


def pad(num, max, settings):
    if int(settings['paddingSize']) == 0:
        paddingSize = len(str(max))
    else:
        paddingSize = len(str(10 ** (int(settings['paddingSize']) - 1)))
    if paddingSize == 1:
        paddingSize = 2
    if settings['padTracks']:
        return str(num).zfill(paddingSize)
    else:
        return str(num)

def generateFilename(track, settings, template):
    filename = template or "%artist% - %title%"
    return settingsRegex(filename, track, settings)

def generateFilepath(track, settings):
    filepath = Path(settings['downloadLocation'])
    artistPath = None
    coverPath = None
    extrasPath = None

    if settings['createPlaylistFolder'] and track.playlist and not settings['tags']['savePlaylistAsCompilation']:
        filepath = filepath / settingsRegexPlaylist(settings['playlistNameTemplate'], track.playlist, settings)

    if track.playlist and not settings['tags']['savePlaylistAsCompilation']:
        extrasPath = filepath

    if (
        (settings['createArtistFolder'] and not track.playlist) or
        (settings['createArtistFolder'] and track.playlist and settings['tags']['savePlaylistAsCompilation']) or
        (settings['createArtistFolder'] and track.playlist and settings['createStructurePlaylist'])
    ):
        filepath = filepath / settingsRegexArtist(settings['artistNameTemplate'], track.album['mainArtist'], settings, rootArtist=track.album['rootArtist'])
        artistPath = filepath

    if (settings['createAlbumFolder'] and
            (not track.singleDownload or (track.singleDownload and settings['createSingleFolder'])) and
            (not track.playlist or
                (track.playlist and settings['tags']['savePlaylistAsCompilation']) or
                (track.playlist and settings['createStructurePlaylist'])
            )
    ):
        filepath = filepath / settingsRegexAlbum(settings['albumNameTemplate'], track.album, settings, track.playlist)
        coverPath = filepath

    if not (track.playlist and not settings['tags']['savePlaylistAsCompilation']):
        extrasPath = filepath

    if (
            int(track.album['discTotal']) > 1 and (
            (settings['createAlbumFolder'] and settings['createCDFolder']) and
            (not track.singleDownload or (track.singleDownload and settings['createSingleFolder'])) and
            (not track.playlist or
                (track.playlist and settings['tags']['savePlaylistAsCompilation']) or
                (track.playlist and settings['createStructurePlaylist'])
            )
    )):
        filepath = filepath / f'CD{str(track.discNumber)}'

    return (filepath, artistPath, coverPath, extrasPath)


def settingsRegex(filename, track, settings):
    filename = filename.replace("%title%", fixName(track.title, settings['illegalCharacterReplacer']))
    filename = filename.replace("%artist%", fixName(track.mainArtist['name'], settings['illegalCharacterReplacer']))
    filename = filename.replace("%artists%", fixName(", ".join(track.artists), settings['illegalCharacterReplacer']))
    filename = filename.replace("%allartists%", fixName(track.artistsString, settings['illegalCharacterReplacer']))
    filename = filename.replace("%mainartists%", fixName(track.mainArtistsString, settings['illegalCharacterReplacer']))
    if track.featArtistsString:
        filename = filename.replace("%featartists%", fixName('('+track.featArtistsString+')', settings['illegalCharacterReplacer']))
    else:
        filename = filename.replace("%featartists%", '')
    filename = filename.replace("%album%", fixName(track.album['title'], settings['illegalCharacterReplacer']))
    filename = filename.replace("%albumartist%", fixName(track.album['mainArtist']['name'], settings['illegalCharacterReplacer']))
    filename = filename.replace("%tracknumber%", pad(track.trackNumber, track.album['trackTotal'], settings))
    filename = filename.replace("%tracktotal%", str(track.album['trackTotal']))
    filename = filename.replace("%discnumber%", str(track.discNumber))
    filename = filename.replace("%disctotal%", str(track.album['discTotal']))
    if len(track.album['genre']) > 0:
        filename = filename.replace("%genre%",
                                    fixName(track.album['genre'][0], settings['illegalCharacterReplacer']))
    else:
        filename = filename.replace("%genre%", "Unknown")
    filename = filename.replace("%year%", str(track.date['year']))
    filename = filename.replace("%date%", track.dateString)
    filename = filename.replace("%bpm%", str(track.bpm))
    filename = filename.replace("%label%", fixName(track.album['label'], settings['illegalCharacterReplacer']))
    filename = filename.replace("%isrc%", track.ISRC)
    filename = filename.replace("%upc%", track.album['barcode'])
    filename = filename.replace("%explicit%", "(Explicit)" if track.explicit else "")

    filename = filename.replace("%track_id%", str(track.id))
    filename = filename.replace("%album_id%", str(track.album['id']))
    filename = filename.replace("%artist_id%", str(track.mainArtist['id']))
    if track.playlist:
        filename = filename.replace("%playlist_id%", str(track.playlist['playlistId']))
        filename = filename.replace("%position%", pad(track.position, track.playlist['trackTotal'], settings))
    else:
        filename = filename.replace("%playlist_id%", '')
        filename = filename.replace("%position%", pad(track.trackNumber, track.album['trackTotal'], settings))
    filename = filename.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(filename))


def settingsRegexAlbum(foldername, album, settings, playlist=None):
    if playlist and settings['tags']['savePlaylistAsCompilation']:
        foldername = foldername.replace("%album_id%", "pl_" + str(playlist['playlistId']))
        foldername = foldername.replace("%genre%", "Compile")
    else:
        foldername = foldername.replace("%album_id%", str(album['id']))
        if len(album['genre']) > 0:
            foldername = foldername.replace("%genre%", fixName(album['genre'][0], settings['illegalCharacterReplacer']))
        else:
            foldername = foldername.replace("%genre%", "Unknown")
    foldername = foldername.replace("%album%", fixName(album['title'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%artist%", fixName(album['mainArtist']['name'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%artist_id%", str(album['mainArtist']['id']))
    if album['rootArtist']:
        foldername = foldername.replace("%root_artist%", fixName(album['rootArtist']['name'], settings['illegalCharacterReplacer']))
        foldername = foldername.replace("%root_artist_id%", str(album['rootArtist']['id']))
    else:
        foldername = foldername.replace("%root_artist%", fixName(album['mainArtist']['name'], settings['illegalCharacterReplacer']))
        foldername = foldername.replace("%root_artist_id%", str(album['mainArtist']['id']))
    foldername = foldername.replace("%tracktotal%", str(album['trackTotal']))
    foldername = foldername.replace("%disctotal%", str(album['discTotal']))
    foldername = foldername.replace("%type%", fixName(album['recordType'].capitalize(), settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%upc%", album['barcode'])
    foldername = foldername.replace("%explicit%", "(Explicit)" if album['explicit'] else "")
    foldername = foldername.replace("%label%", fixName(album['label'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%year%", str(album['date']['year']))
    foldername = foldername.replace("%date%", album['dateString'])
    foldername = foldername.replace("%bitrate%", bitrateLabels[int(album['bitrate'])])

    foldername = foldername.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(foldername))


def settingsRegexArtist(foldername, artist, settings, rootArtist=None):
    foldername = foldername.replace("%artist%", fixName(artist['name'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%artist_id%", str(artist['id']))
    if rootArtist:
        foldername = foldername.replace("%root_artist%", fixName(rootArtist['name'], settings['illegalCharacterReplacer']))
        foldername = foldername.replace("%root_artist_id%", str(rootArtist['id']))
    else:
        foldername = foldername.replace("%root_artist%", fixName(artist['name'], settings['illegalCharacterReplacer']))
        foldername = foldername.replace("%root_artist_id%", str(artist['id']))
    foldername = foldername.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(foldername))


def settingsRegexPlaylist(foldername, playlist, settings):
    foldername = foldername.replace("%playlist%", fixName(playlist['title'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%playlist_id%", fixName(playlist['playlistId'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%owner%", fixName(playlist['owner']['name'], settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%owner_id%", str(playlist['owner']['id']))
    foldername = foldername.replace("%year%", str(playlist['date']['year']))
    foldername = foldername.replace("%date%", str(playlist['dateString']))
    foldername = foldername.replace("%explicit%", "(Explicit)" if playlist['explicit'] else "")
    foldername = foldername.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(foldername))

def settingsRegexPlaylistFile(foldername, queueItem, settings):
    foldername = foldername.replace("%title%", fixName(queueItem.title, settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%artist%", fixName(queueItem.artist, settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%size%", str(queueItem.size))
    foldername = foldername.replace("%type%", fixName(queueItem.type, settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%id%", fixName(queueItem.id, settings['illegalCharacterReplacer']))
    foldername = foldername.replace("%bitrate%", bitrateLabels[int(queueItem.bitrate)])
    foldername = foldername.replace('\\', pathSep).replace('/', pathSep).replace(pathSep, settings['illegalCharacterReplacer'])
    return antiDot(fixLongName(foldername))
