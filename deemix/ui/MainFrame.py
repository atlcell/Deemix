#!/usr/bin/env python3
import wx

from deemix.ui.SettingsDialog import SettingsDialog
from deemix.utils.misc import getIDFromLink, getTypeFromLink
from deemix.app.downloader import download_track, download_album, download_playlist
from deemix.app.settings import initSettings

menuIDs = {
	"SETTINGS": 1
}

class MainFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		super().__init__(parent=None, title='deemix')
		panel = wx.Panel(self)

		self.settings = initSettings()

		# Menubar
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		settingsItem = fileMenu.Append(menuIDs['SETTINGS'], 'Settings', 'Edit Settings')
		fileMenu.AppendSeparator()
		quitItem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
		menubar.Append(fileMenu, '&File')
		self.SetMenuBar(menubar)
		self.Bind(wx.EVT_MENU, self.close_app, quitItem)
		self.Bind(wx.EVT_MENU, self.open_settings, settingsItem)

		# Main app
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		search_sizer = wx.BoxSizer(wx.HORIZONTAL)
		main_sizer.Add(search_sizer, 0, wx.EXPAND, 5)
		self.text_ctrl = wx.TextCtrl(panel)
		search_sizer.Add(self.text_ctrl, 1, wx.ALL, 5)
		my_btn = wx.Button(panel, label='Download')
		my_btn.Bind(wx.EVT_BUTTON, self.download_track)
		search_sizer.Add(my_btn, 0, wx.ALL, 5)
		panel.SetSizer(main_sizer)
		self.Show()

	def download_track(self, event):
		value = self.text_ctrl.GetValue()
		if not value:
			print("You didn't enter anything!")
			return None
		type = getTypeFromLink(value)
		id = getIDFromLink(value, type)
		print(type, id)
		if type == "track":
			download_track(id, self.settings)
		elif type == "album":
			download_album(id, self.settings)
		elif type == "playlist":
			download_playlist(id, self.settings)
		self.text_ctrl.SetValue("")

	def close_app(self, event):
		self.Close()

	def open_settings(self, event):
		settings_dialog = SettingsDialog(self.settings, self)
		res = settings_dialog.ShowModal()
		if res == wx.ID_OK:
			self.settings = settings_dialog.GetSettings()
		settings_dialog.Destroy()
