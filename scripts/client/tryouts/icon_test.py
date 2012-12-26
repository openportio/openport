import json
import os
import sys
import threading
import time
import datetime
import wx
import urllib2

class TestFrame(wx.Frame):

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title, size = (200, 150),
            style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)

        iconFile = '../resources/logo-base.ico'
        icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

def main():
    app = wx.App(False)
    frame = TestFrame(None, -1, "hello")
    frame.Show()

    app.MainLoop()

if __name__ == '__main__':
    main()