#!/usr/bin/env python3
from urllib.request import urlopen
import requests
import json
import re

import hashlib
import pyaes
import binascii
import blowfish

class Deezer:
	def __init__(self):
		self.api_url = "http://www.deezer.com/ajax/gw-light.php"
		self.legacy_api_url = "https://api.deezer.com/"
		self.http_headers = {
			"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
			}
		self.album_pictures_host = "https://e-cdns-images.dzcdn.net/images/cover/"
		self.artist_pictures_host = "https://e-cdns-images.dzcdn.net/images/artist/"
		self.user = {}
		self.session = requests.Session()
		self.logged_in = False
		self.session.post("http://www.deezer.com/", headers=self.http_headers)
		self.sid = self.session.cookies.get_dict()['sid']

	def get_token(self):
		tokenData = self.gw_api_call('deezer.getUserData')
		return tokenData["results"]["checkForm"]

	def get_track_MD5(self, id):
		site = self.session.post("https://api.deezer.com/1.0/gateway.php",
			params = {
				'api_key' : "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE",
				'sid' : self.sid,
				'input' : '3',
				'output': '3',
				'method' : 'song_getData'
			},
			data = json.dumps({'sng_id': id}),
			headers = self.http_headers
		)
		response = json.loads(site.text)
		return response['results']['PUID']

	def gw_api_call(self, method, args={}):
		result = self.session.post(
			self.api_url,
			params = {
				'api_version' : "1.0",
				'api_token' : 'null' if method == 'deezer.getUserData' else self.get_token(),
				'input' : '3',
				'method' : method
			},
			data = json.dumps(args),
			headers = self.http_headers
		)
		result = json.loads(result.text)
		return result

	def api_call(self, method, args={}):
		result = self.session.get(
			self.legacy_api_url+method,
			params = args,
			headers = self.http_headers
		)
		result_json = json.loads(result.text)
		if 'error' in result_json.keys():
			raise APIError()
		return result_json

	def login(self, email, password, reCaptchaToken):
		checkFormLogin = self.gw_api_call("deezer.getUserData")
		login = self.session.post(
			"https://www.deezer.com/ajax/action.php",
			data={
				'type':'login',
				'mail':email,
				'password':password,
				'checkFormLogin':checkFormLogin['results']['checkFormLogin'],
				'reCaptchaToken': reCaptchaToken
			},
			headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}.update(self.http_headers)
		)
		if not 'success' in login.text:
			self.logged_in = False
			return False
		userData = self.gw_api_call("deezer.getUserData")
		self.user = {
			'email': email,
			'id': userData["results"]["USER"]["USER_ID"],
			'name': userData["results"]["USER"]["BLOG_NAME"],
			'picture': userData["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in userData["results"]["USER"] else ""
		}
		self.logged_in = True
		return True

	def login_via_arl(self, arl):
		cookie_obj = requests.cookies.create_cookie(
			domain='deezer.com',
			name='arl',
			value=arl,
			path="/",
			rest={'HttpOnly': True}
		)
		self.session.cookies.set_cookie(cookie_obj)
		userData = self.gw_api_call("deezer.getUserData")
		if (userData["results"]["USER"]["USER_ID"] == 0):
			self.logged_in = False
			return False
		self.user = {
			'id': userData["results"]["USER"]["USER_ID"],
			'name': userData["results"]["USER"]["BLOG_NAME"],
			'picture': userData["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in userData["results"]["USER"] else ""
		}
		self.logged_in = True
		return True

	def get_track_gw(self, id):
		if (int(id)<0):
			body = self.gw_api_call('song.getData', {'sng_id': id})
		else:
			body = self.gw_api_call('deezer.pageTrack', {'sng_id': id})
			if 'LYRICS' in body['results']:
				body['results']['DATA']['LYRICS'] = body['results']['LYRICS']
			body['results'] = body['results']['DATA']
		return body['results']

	def get_tracks_gw(self, ids):
		tracksArray = []
		body = self.gw_api_call('song.getListData', {'sng_ids': ids})
		errors = 0
		for i in range(len(ids)):
			if ids[i] != 0:
				tracksArray.append(body['results']['data'][i-errors])
			else:
				errors += 1
				tracksArray.append({
					'SNG_ID': 0,
					'SNG_TITLE': '',
					'DURATION': 0,
					'MD5_ORIGIN': 0,
					'MEDIA_VERSION': 0,
					'FILESIZE': 0,
					'ALB_TITLE': "",
					'ALB_PICTURE': "",
					'ART_ID': 0,
					'ART_NAME': ""
				})
		return tracksArray

	def get_album_gw(self, id):
		body = self.gw_api_call('album.getData', {'alb_id': id})
		return body['results']

	def get_album_tracks_gw(self, id):
		tracksArray = []
		body = self.gw_api_call('song.getListByAlbum', {'alb_id': id, 'nb': -1})
		for track in body['results']['data']:
			_track = track
			_track['position'] = body['results']['data'].index(track)
			tracksArray.append(_track)
		return tracksArray

	def get_artist_gw(self, id):
		body = self.gw_api_call('deezer.pageArtist', {'art_id': id})
		return body

	def get_playlist_gw(self, id):
		body = self.gw_api_call('deezer.pagePlaylist', {'playlist_id': id})
		return body

	def get_playlist_tracks_gw(self, id):
		tracksArray = []
		body = self.gw_api_call('playlist.getSongs', {'playlist_id': id, 'nb': -1})
		for track in body['results']['data']:
			_track = track
			_track['position'] = body['results']['data'].index(track)
			tracksArray.append(_track)
		return tracksArray

	def get_artist_toptracks_gw(self, id):
		tracksArray = []
		body = self.gw_api_call('artist.getTopTrack', {'art_id': id, 'nb': 100})
		for track in body['results']['data']:
			_track = track
			_track['position'] = body['results']['data'].index(track)
			tracksArray.append(_track)
		return tracksArray

	def get_lyrics_gw(self, id):
		body = self.gw_api_call('song.getLyrics', {'sng_id': id})
		lyr = {}
		lyr['unsyncLyrics'] = {
			'description': "",
			'lyrics': body["results"]["LYRICS_TEXT"]
		}
		lyr['syncLyrics'] = ""
		for i in range(len(body["results"]["LYRICS_SYNC_JSON"])):
			if "lrc_timestamp" in body["results"]["LYRICS_SYNC_JSON"][i]:
				lyr['syncLyrics'] += body["results"]["LYRICS_SYNC_JSON"][i]["lrc_timestamp"] + body["results"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
			elif i+1 < len(body["results"]["LYRICS_SYNC_JSON"]):
				lyr['syncLyrics'] += body["results"]["LYRICS_SYNC_JSON"][i+1]["lrc_timestamp"] + body["results"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
		return lyr

	def get_user_playlist(self, id):
		body = self.api_call('user/'+str(id)+'/playlists', {'limit': -1})
		return body

	def get_track(self, id):
		body = self.api_call('track/'+str(id))
		return body

	def get_track_by_ISRC(self, isrc):
		body = self.api_call('track/isrc:'+isrc)
		return body

	def get_charts_top_country(self):
		return self.get_user_playlist('637006841')

	def get_playlist(self, id):
		body = self.api_call('playlist/'+str(id))
		return body

	def get_playlist_tracks(self, id):
		body = self.api_call('playlist/'+str(id)+'/tracks', {'limit': -1})
		return body

	def get_album(self, id):
		body = self.api_call('album/'+str(id))
		return body

	def get_album_by_UPC(self, upc):
		body = self.api_call('album/upc:'+str(upc))

	def get_album_tracks(self, id):
		body = self.api_call('album/'+str(id)+'/tracks', {'limit': -1})
		return body

	def get_artist(self, id):
		body = self.api_call('artist/'+str(id))
		return body

	def get_artist_albums(self, id):
		body = self.api_call('artist/'+str(id)+'/albums', {'limit': -1})
		return body

	def search(self, term, type, limit = 30):
		body = self.api_call('search/'+type, {'q': term, 'limit': limit})
		return body

	def decrypt_track(self, trackId, input, output):
		response = open(input, 'rb')
		outfile = open(output, 'wb')
		cipher = blowfish.Cipher(str.encode(self._get_blowfish_key(str(trackId))))
		i=0
		while True:
			chunk = response.read(2048)
			if not chunk:
				break
			if (i % 3)==0 and len(chunk)==2048:
				chunk = b"".join(cipher.decrypt_cbc(chunk,b"\x00\x01\x02\x03\x04\x05\x06\x07"))
			outfile.write(chunk)
			i += 1

	def stream_track(self, trackId, url, stream):
		response = urlopen(url)
		cipher = blowfish.Cipher(str.encode(self._get_blowfish_key(str(trackId))))
		i=0
		while True:
			chunk = response.read(2048)
			if not chunk:
				break
			if (i % 3)==0 and len(chunk)==2048:
				chunk = b"".join(cipher.decrypt_cbc(chunk,b"\x00\x01\x02\x03\x04\x05\x06\x07"))
			stream.write(chunk)
			i += 1

	def _md5(self, data):
		h=hashlib.new("md5")
		h.update(str.encode(data) if isinstance(data, str) else data)
		return h.hexdigest()

	def _ecb_crypt(self, key, data):
		res = b''
		for x in range(int(len(data)/16)):
			res += binascii.hexlify(pyaes.AESModeOfOperationECB(key).encrypt(data[:16]))
			data = data[16:]
		return res

	def _get_blowfish_key(self, trackId):
		SECRET = 'g4el58wc'+'0zvf9na1'
		idMd5 = self._md5(trackId)
		bfKey = ""
		for i in range(16):
			bfKey += chr(ord(idMd5[i]) ^ ord(idMd5[i+16]) ^ ord(SECRET[i]))
		return bfKey

	def get_track_stream_url(self, sng_id, md5, media_version, format):
		urlPart = b'\xa4'.join([str.encode(md5), str.encode(str(format)), str.encode(str(sng_id)), str.encode(str(media_version))])
		md5val = self._md5(urlPart)
		step2 = str.encode(md5val)+b'\xa4'+urlPart+b'\xa4'
		while len(step2)%16 > 0:
			step2 += b'.'
		urlPart = self._ecb_crypt(b'jo6aey6haid2Teih', step2)
		return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/mobile/1/" + urlPart.decode("utf-8")

class APIError(Exception):
	pass
