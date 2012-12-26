import wx
from services.osinteraction import OsInteraction
import os

class OpenPortItTaskBarIcon(wx.TaskBarIcon):

    def __init__(self, parent):
        wx.TaskBarIcon.__init__(self)
        self.parentApp = parent
        osinteraction = OsInteraction()

        self.icon = wx.Icon(osinteraction.get_resource_path('logo-base.ico'), wx.BITMAP_TYPE_ICO)
        self.SetIcon(self.icon, "OpenPort-It")
        self.CreateMenu()
        self.items = {}

    def CreateMenu(self):
        self.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.ShowMenu)
        self.menu=wx.Menu()

    def addItem(self, label, callBackFunction):
        newItem = wx.NewId()
        self.menu.Append(newItem, label)
        self.Bind(wx.EVT_MENU, callBackFunction, id=newItem)

    def ShowMenu(self,event):
        self.PopupMenu(self.menu)

def main(argv=None):

    class OpenPortItFrame(wx.Frame):
        def __init__(self, parent, id, title):
            wx.Frame.__init__(self, parent, -1, title, size = (1, 1),
                style=wx.NO_FULL_REPAINT_ON_RESIZE)

            self.tbicon = OpenPortItTaskBarIcon(self)
            self.tbicon.Bind(wx.EVT_MENU, self.exitApp, id=wx.ID_EXIT)
            self.Show(True)

    app = wx.App(False)
    frame = OpenPortItFrame(None, -1, ' ')
    frame.Show(False)
    app.MainLoop()

if __name__ == '__main__':
    main()