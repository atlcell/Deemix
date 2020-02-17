#!/usr/bin/env python3
import wx
from deemix.app.functions import downloadTrack, getIDFromLink, getTypeFromLink

class MainFrame(wx.Frame):
	def __init__(self):
		super().__init__(parent=None, title='deemix')
		panel = wx.Panel(self)
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		search_sizer = wx.BoxSizer(wx.HORIZONTAL)
		main_sizer.Add(search_sizer, 0, wx.EXPAND, 5)
		self.text_ctrl = wx.TextCtrl(panel)
		search_sizer.Add(self.text_ctrl, 1, wx.ALL, 5)
		my_btn = wx.Button(panel, label='Download')
		my_btn.Bind(wx.EVT_BUTTON, self.downloadTrack)
		search_sizer.Add(my_btn, 0, wx.ALL, 5)
		panel.SetSizer(main_sizer)
		self.Show()

	def downloadTrack(self, event):
		value = self.text_ctrl.GetValue()
		if not value:
			print("You didn't enter anything!")
			return None
		type = getTypeFromLink(value)
		id = getIDFromLink(value,type)
		print(type, id)
		if type == "track":
			downloadTrack(id,9)
		self.text_ctrl.SetValue("")
