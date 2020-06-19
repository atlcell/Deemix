#!/usr/bin/env python3
import click

import deemix.app.cli as app
from deemix.app.settings import initSettings
from os.path import isfile


@click.command()
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.option('-l', '--local', is_flag=True, help='Downloads in a local folder insted of using the default')
@click.argument('url', nargs=-1, required=True)
def download(bitrate, local, url):
    settings = initSettings(local)
    app.login()
    url = list(url)
    if isfile(url[0]):
        filename = url[0]
        with open(filename) as f:
            url = f.readlines()
    app.downloadLink(url, settings, bitrate)
    click.echo("All done!")
    if local:
        click.echo(settings['downloadLocation']) #folder name output

def main():
    download()

if __name__ == '__main__':
    main()
