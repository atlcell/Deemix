#!/usr/bin/env python3
import click

from deemix.app.cli import cli
from pathlib import Path

@click.command()
@click.option('--portable', is_flag=True, help='Creates the config folder in the same directory where the script is launched')
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.option('-p', '--path', type=str, help='Downloads in the given folder')
@click.argument('url', nargs=-1, required=True)
def download(url, bitrate, portable, path):

    localpath = Path('.')
    configFolder = localpath / 'config' if portable else None
    if path is not None:
        if path == '': path = '.'
        path = Path(path)

    app = cli(path, configFolder)
    app.login()
    url = list(url)

    try:
        isfile = Path(url[0]).is_file()
    except:
        isfile = False
    if isfile:
        filename = url[0]
        with open(filename) as f:
            url = f.readlines()

    app.downloadLink(url, bitrate)
    click.echo("All done!")

if __name__ == '__main__':
    download()
