from pathlib import Path
import sys
from os import getenv

userdata = ""
homedata = Path.home()

if getenv("APPDATA"):
    userdata = Path(getenv("APPDATA")) / "deemix"
elif sys.platform.startswith('darwin'):
    userdata = homedata / 'Library' / 'Application Support' / 'deemix'
elif getenv("XDG_CONFIG_HOME"):
    userdata = Path(getenv("XDG_CONFIG_HOME")) / 'deemix'
else:
    userdata = homedata / '.config' / 'deemix'

def getHomeFolder():
    return homedata

def getConfigFolder():
    return userdata
