# WARNING
The webUI is not finished, some functions may not work.

# deemix
## What is deemix?
deemix is a deezer downloader built from the ashes of Deezloader Remix. The base library (or core) can be used as a stand alone CLI app or implemented in an UI using the API.

## How can I use this?
Currently there are no available builds as it's still in development.<br>
But you can try to run it yourself!<br>

## Running instructions
### Standard way
NOTE: Python 3 is required for this app. Make sure you tick the option to add Python to PATH when installing.<br>
NOTE: If `python3` is "not a recognized command" try using `python` instead.<br>
<br>
After installing Python open a terminal/command prompt and install the dependencies using `python3 -m pip install -r requirements.txt --user`<br>
Run `python3 -m deemix --help` to see how to use the app in CLI mode.<br>
Run `python3 server.py` to start the server and then connect to `127.0.0.1:33333`. The GUI should show up.<br>
Enjoy!<br>

### Easy Windows way
Download `install.bat` file to your PC and place it in the folder where you want Deemix to live<br>
Start the `install.bat` as administrator<br>
Wait for it to finish, then run the `start.bat`<br>

## What's left to do?
Library:
- Add a log system
- Write the API Documentation

in the WebUI:
- Lock the UI until it connects to the socket.io server
- Make the UI look coherent
- Home tab
	- Login warning if the user is not logged in
	- Loading circle while the ui is still not connected to the server
- Search tab
	- Hide buttons and add a placeholder before search
	- Better loading feadback fot the user (maybe with a loading circle)
- Charts tab
  - Fix Country selection display
	- On country selection, move scrolled window to top
- Link Analyzer
	- Add placeholder before link analyzer
	- Implement large header (like in the artist and tracklist tab)
- Settings tab
	- Stylize and separate the options
	- Maybe tabbing the section for easy navigation
- About tab
	- Write stuff about the app
- ?

# License
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
