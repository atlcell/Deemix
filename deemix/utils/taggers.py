#!/usr/bin/env python3
from urllib.request import urlopen

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, ID3NoHeaderError, TXXX, TIT2, TPE1, TALB, TPE2, TRCK, TPOS, TCON, TYER, TDAT, TLEN, TBPM, \
	TPUB, TSRC, USLT, APIC, IPLS, TCOM, TCOP


def tagID3(stream, track):
	try:
		tag = ID3(stream)
	except ID3NoHeaderError:
		tag = ID3()

	tag.add(TIT2(text=track['title']))
	tag.add(TPE1(text=track['artists']))
	tag.add(TALB(text=track['album']['title']))
	tag.add(TPE2(text=track['album']['artist']['name']))
	tag.add(TRCK(text=str(track['trackNumber'])))
	tag.add(TPOS(text=str(track['discNumber'])))
	tag.add(TCON(text=track['album']['genre']))
	tag.add(TYER(text=str(track['date']['year'])))
	tag.add(TDAT(text=str(track['date']['month']) + str(track['date']['day'])))
	tag.add(TLEN(text=str(track['duration'])))
	tag.add(TBPM(text=str(track['bpm'])))
	tag.add(TPUB(text=track['album']['label']))
	tag.add(TSRC(text=track['ISRC']))
	tag.add(TXXX(desc="BARCODE", text=track['album']['barcode']))
	tag.add(TXXX(desc="ITUNESADVISORY", text="1" if track['explicit'] else "0"))
	tag.add(TXXX(desc="REPLAYGAIN_TRACK_GAIN", text=track['replayGain']))
	if 'unsync' in track['lyrics']:
		tag.add(USLT(text=track['lyrics']['unsync']))
	involved_people = []
	for role in track['contributors']:
		if role in ['author', 'engineer', 'mixer', 'producer', 'writer']:
			for person in track['contributors'][role]:
				involved_people.append([role, person])
		elif role == 'composer':
			tag.add(TCOM(text=track['contributors']['composer']))
	if len(involved_people) > 0:
		tag.add(IPLS(people=involved_people))
	tag.add(TCOP(text=track['copyright']))

	tag.add(APIC(3, 'image/jpeg', 3, data=urlopen(
		"http://e-cdn-images.deezer.com/images/cover/" + track["album"]['pic'] + "/800x800.jpg").read()))

	tag.save(stream, v1=2, v2_version=3, v23_sep=None)


def tagFLAC(stream, track):
	tag = FLAC(stream)

	tag["TITLE"] = track['title']
	tag["ARTIST"] = track['artists']
	tag["ALBUM"] = track['album']['title']
	tag["ALBUMARTIST"] = track['album']['artist']['name']
	tag["TRACKNUMBER"] = str(track['trackNumber'])
	tag["TRACKTOTAL"] = str(track['album']['trackTotal'])
	tag["DISCNUMBER"] = str(track['discNumber'])
	tag["DISCTOTAL"] = str(track['album']['discTotal'])
	tag["GENRE"] = track['album']['genre']
	tag["YEAR"] = str(track['date']['year'])
	tag["DATE"] = "{}-{}-{}".format(str(track['date']['year']), str(track['date']['month']), str(track['date']['day']))
	tag["LENGTH"] = str(track['duration'])
	tag["BPM"] = str(track['bpm'])
	tag["PUBLISHER"] = track['album']['label']
	tag["ISRC"] = track['ISRC']
	tag["BARCODE"] = track['album']['barcode']
	tag["ITUNESADVISORY"] = "1" if track['explicit'] else "0"
	tag["REPLAYGAIN_TRACK_GAIN"] = track['replayGain']
	if 'unsync' in track['lyrics']:
		tag["LYRICS"] = track['lyrics']['unsync']
	for role in track['contributors']:
		if role in ['author', 'engineer', 'mixer', 'producer', 'writer', 'composer']:
			tag[role.upper()] = track['contributors'][role]
		elif role == 'musicpublisher':
			tag["ORGANIZATION"] = track['contributors']['musicpublisher']
	tag["COPYRIGHT"] = track['copyright']

	image = Picture()
	image.type = 3
	image.mime = 'image/jpeg'
	image.data = urlopen("http://e-cdn-images.deezer.com/images/cover/" + track["album"]['pic'] + "/800x800.jpg").read()
	tag.add_picture(image)

	tag.save(deleteid3=True)
