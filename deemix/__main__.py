#!/usr/bin/env python3
import wx
from deemix.ui.MainFrame import MainFrame

if __name__ == '__main__':
	app = wx.App()
	frame = MainFrame()
	app.MainLoop()
