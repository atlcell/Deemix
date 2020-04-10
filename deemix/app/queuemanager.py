from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt
from deemix.utils.spotifyHelper import get_trackid_spotify, get_albumid_spotify
from concurrent.futures import ProcessPoolExecutor
from deemix.app.downloader import download

queue = []
queueList = {}
currentItem = ""
currentJob = None

"""
queueItem base structure
	title
	artist
	cover
	size
	downloaded
	failed
	progress
	type
	id
	bitrate
	uuid: type+id+bitrate
if its a single track
	single
if its an album/playlist
	collection
"""

def generateQueueItem(dz, url, settings, bitrate=None, albumAPI=None):
	forcedBitrate = getBitrateInt(bitrate)
	bitrate = forcedBitrate if forcedBitrate else settings['maxBitrate']
	type = getTypeFromLink(url)
	id = getIDFromLink(url, type)
	result = {}
	if type == None or id == None:
		print("URL not recognized")
		result['error'] = "URL not recognized"
	elif type == "track":
		trackAPI = dz.get_track_gw(id)
		if albumAPI:
			trackAPI['_EXTRA_ALBUM'] = albumAPI
		trackAPI['FILENAME_TEMPLATE'] = settings['tracknameTemplate']
		trackAPI['SINGLE_TRACK'] = True

		result['title'] = trackAPI['SNG_TITLE']
		if 'VERSION' in trackAPI and trackAPI['VERSION']:
			result['title'] += " " + trackAPI['VERSION']
		result['artist'] = trackAPI['ART_NAME']
		result['cover'] = f"https://e-cdns-images.dzcdn.net/images/cover/{trackAPI['ART_PICTURE']}/128x128-000000-80-0-0.jpg"
		result['size'] = 1
		result['downloaded'] = 0
		result['failed'] = 0
		result['progress'] = 0
		result['type'] = 'track'
		result['id'] = id
		result['bitrate'] = bitrate
		result['uuid'] = f"{result['type']}:{id}:{bitrate}"
		result['settings'] = settings or {}
		result['single'] = trackAPI

	elif type == "album":
		albumAPI = dz.get_album(id)
		albumAPI_gw = dz.get_album_gw(id)
		albumAPI['nb_disk'] = albumAPI_gw['NUMBER_DISK']
		albumAPI['copyright'] = albumAPI_gw['COPYRIGHT']
		if albumAPI['nb_tracks'] == 1:
			return generateQueueItem(dz, f"https://www.deezer.com/track/{albumAPI['tracks']['data'][0]['id']}", settings, bitrate, albumAPI)
		tracksArray = dz.get_album_tracks_gw(id)

		result['title'] = albumAPI['title']
		result['artist'] = albumAPI['artist']['name']
		result['cover'] = albumAPI['cover_small'][:-24]+'/128x128-000000-80-0-0.jpg'
		result['size'] = albumAPI['nb_tracks']
		result['downloaded'] = 0
		result['failed'] = 0
		result['progress'] = 0
		result['type'] = 'album'
		result['id'] = id
		result['bitrate'] = bitrate
		result['uuid'] = f"{result['type']}:{id}:{bitrate}"
		result['settings'] = settings or {}
		result['collection'] = []
		for pos, trackAPI in enumerate(tracksArray, start=1):
			trackAPI['_EXTRA_ALBUM'] = albumAPI
			trackAPI['POSITION'] = pos
			trackAPI['FILENAME_TEMPLATE'] = settings['albumTracknameTemplate']
			result['collection'].append(trackAPI)

	elif type == "playlist":
		playlistAPI = dz.get_playlist(id)
		playlistTracksAPI = dz.get_playlist_tracks_gw(id)

		result['title'] = playlistAPI['title']
		result['artist'] = playlistAPI['creator']['name']
		result['cover'] = playlistAPI['picture_small'][:-24]+'/128x128-000000-80-0-0.jpg'
		result['size'] = playlistAPI['nb_tracks']
		result['downloaded'] = 0
		result['failed'] = 0
		result['progress'] = 0
		result['type'] = 'playlist'
		result['id'] = id
		result['bitrate'] = bitrate
		result['uuid'] = f"{result['type']}:{id}:{bitrate}"
		result['settings'] = settings or {}
		result['collection'] = []
		for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
			trackAPI['_EXTRA_PLAYLIST'] = playlistAPI
			trackAPI['POSITION'] = pos
			trackAPI['FILENAME_TEMPLATE'] = settings['playlistTracknameTemplate']
			result['collection'].append(trackAPI)

	elif type == "artist":
		artistAPI = dz.get_artist_albums(id)
		albumList = []
		for album in artistAPI['data']:
			albumList.append(generateQueueItem(dz, album['link'], settings, bitrate))
		return albumList
	elif type == "spotifytrack":
		track_id = get_trackid_spotify(dz, id, settings['fallbackSearch'])
		result = {}
		if track_id == "Not Enabled":
			print("Spotify Features is not setted up correctly.")
			result['error'] = "Spotify Features is not setted up correctly."
		elif track_id != 0:
			return generateQueueItem(dz, f'https://www.deezer.com/track/{track_id}', settings, bitrate)
		else:
			print("Track not found on deezer!")
			result['error'] = "Track not found on deezer!"
	elif type == "spotifyalbum":
		album_id = get_albumid_spotify(dz, id)
		if album_id == "Not Enabled":
			print("Spotify Features is not setted up correctly.")
			result['error'] = "Spotify Features is not setted up correctly."
		elif album_id != 0:
			return generateQueueItem(dz, f'https://www.deezer.com/album/{track_id}', settings, bitrate)
		else:
			print("Album not found on deezer!")
			result['error'] = "Album not found on deezer!"
	else:
		print("URL not supported yet")
		result['error'] = "URL not supported yet"
	return result

def addToQueue(dz, url, settings, bitrate=None, socket=None):
	global currentItem, currentJob, queueList, queue
	queueItem = generateQueueItem(dz, url, settings, bitrate)
	if 'error' in queueItem:
		if socket:
			socket.emit("message", queueItem['error'])
		return None
	if queueItem['uuid'] in list(queueList.keys()):
		print("Already in queue!")
		if socket:
			socket.emit("message", "Already in queue!")
		return None
	if type(queueItem) is list:
		for x in queueItem:
			if socket:
				socket.emit("addedToQueue", x)
			queue.append(x['uuid'])
			queueList[x['uuid']] = x
	else:
		if socket:
			socket.emit("addedToQueue", queueItem)
		queue.append(queueItem['uuid'])
		queueList[queueItem['uuid']] = queueItem
	nextItem(dz, socket)

def nextItem(dz, socket=None):
	global currentItem, currentJob, queueList, queue
	if currentItem != "":
		return None
	else:
		if len(queue)>0:
			currentItem = queue.pop(0)
		else:
			return None
		if socket:
			socket.emit("message", f"Started downloading {currentItem}")
		result = download(dz, queueList[currentItem], socket)
		callbackQueueDone(result)

def callbackQueueDone(result):
	global currentItem, currentJob, queueList, queue
	result['socket']
	del queueList[currentItem]
	currentItem = ""
	nextItem(result['dz'], result['socket'])
