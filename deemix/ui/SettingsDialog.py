#!/usr/bin/env python3
import wx

class SettingsDialog(wx.Dialog):
	def __init__(self, settings, *args, **kwargs):
		wx.Dialog.__init__(self, title="Settings", size=wx.Size(600,400), *args, **kwargs)
		self.settings = settings

		panel = wx.Panel(self)
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		nb = wx.Notebook(panel, style=wx.NB_LEFT)
		nb.AddPage(wx.Window(nb), "App Settings")
		nb.AddPage(wx.Window(nb), "Path Settings")
		nb.AddPage(wx.Window(nb), "Tagging Settings")
		main_sizer.Add(nb, 1, wx.ALL, 5)

		button_ok = wx.Button(panel, label="OK")
		button_cancel = wx.Button(panel, label="Cancel")
		button_ok.Bind(wx.EVT_BUTTON, self.onOk)
		button_cancel.Bind(wx.EVT_BUTTON, self.onCancel)

		footer_sizer = wx.BoxSizer(wx.HORIZONTAL)
		footer_sizer.Add(button_ok, 0, wx.ALL, 5)
		footer_sizer.Add(button_cancel, 0, wx.ALL, 5)
		main_sizer.Add(footer_sizer, 0, wx.ALIGN_RIGHT)

		panel.SetSizerAndFit(main_sizer)

	def onCancel(self, e):
		self.EndModal(wx.ID_CANCEL)

	def onOk(self, e):
		# Check each page and save all data
		self.EndModal(wx.ID_OK)

	def GetSettings(self):
		return self.settings
