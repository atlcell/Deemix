#!/usr/bin/env python3
import click
from deemix.utils.misc import getIDFromLink, getTypeFromLink, getBitrateInt
from deemix.app.downloader import download_track, download_album, download_playlist
from deemix.app.settings import initSettings

@click.command()
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.argument('url')
def download(bitrate, url):
	settings = initSettings()
	forcedBitrate = getBitrateInt(bitrate)
	type = getTypeFromLink(url)
	id = getIDFromLink(url, type)
	if type == None or id == None:
		click.echo("URL not recognized")
	if type == "track":
		download_track(id, settings, forcedBitrate)
	elif type == "album":
		download_album(id, settings, forcedBitrate)
	elif type == "playlist":
		download_playlist(id, settings, forcedBitrate)
	else:
		click.echo("URL not supported yet")
	click.echo("All done!")

if __name__ == '__main__':
	download()
