#!/usr/bin/env python3
import click

import deemix.app.cli as app
from deemix.app.settings import initSettings
from os.path import isfile


@click.command()
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.option('-bot', '--botmode', is_flag=True, help='Enables bot mode')
@click.argument('url', nargs=-1, required=True)
def download(bitrate, botmode, url):
    settings = initSettings(botmode)
    app.login()
    if isfile(url[0]):
        filename = url[0]
        with open(filename) as f:
            url = f.readlines()
    for u in url:
        app.downloadLink(u, settings, bitrate)
    click.echo("All done!")
    if botmode:
        click.echo(settings['downloadLocation']) #folder name output


if __name__ == '__main__':
    download()
