#!/usr/bin/env python3
import click

from deemix.app.cli import cli
from os.path import isfile

@click.command()
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.option('-l', '--local', is_flag=True, help='Downloads in a local folder insted of using the default')
@click.argument('url', nargs=-1, required=True)
def download(bitrate, local, url):
    app = cli(local)
    app.login()
    url = list(url)
    if isfile(url[0]):
        filename = url[0]
        with open(filename) as f:
            url = f.readlines()
    app.downloadLink(url, bitrate)
    click.echo("All done!")
    if local:
        click.echo(app.set.settings['downloadLocation']) #folder name output

if __name__ == '__main__':
    download()
