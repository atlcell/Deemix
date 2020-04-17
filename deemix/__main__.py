#!/usr/bin/env python3
import click

import deemix.app.cli as app
from deemix.app.settings import initSettings


@click.command()
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.argument('url')
def download(bitrate, url):
    settings = initSettings()
    app.login()
    app.downloadLink(url, settings, bitrate)
    click.echo("All done!")


if __name__ == '__main__':
    download()
