import sys
import wx
from wx._core import DefaultPosition, DefaultSize
from wx._core import TAB_TRAVERSAL, NO_BORDER
from openportit import open_port_file
from server import start_server_thread
from trayicon import OpenPortItTaskBarIcon
from dbhandler import DBHandler

class OpenPortItFrame(wx.Frame):

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title, size = (200, 150),
            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE)

        self.dbhandler = DBHandler()

        self.addTrayIcon()
        self.startServer()
        self.restart_sharing()
        self.show_shares()
#        VIEW_SHARES=wx.NewId()
#        STOP_SHARING=wx.NewId()
#        VIEW_LOG=wx.NewId()
#        CHECK_UPDATES=wx.NewId()
#        ABOUT=wx.NewId()
        self.Show(True)

    def addTrayIcon(self):
        self.tbicon = OpenPortItTaskBarIcon(self)
        self.tbicon.addItem('View shares', self.viewShares)
        self.tbicon.menu.AppendSeparator()
        self.tbicon.addItem('Exit', self.exitApp)

    def exitApp(self,event):
        self.tbicon.RemoveIcon()
        self.tbicon.Destroy()
        sys.exit()

    def viewShares(self,event):
        print 'view shares'
        files = self.dbhandler.get_files()
        for file in files:
            print file
        self.Show(True)

    def startServer(self):
        start_server_thread()

    def restart_sharing(self):
        pass
#        files = self.dbhandler.get_files()
#        for file in files:
#            open_port_file(file[1])

    def show_shares(self):
        panel = wx.Panel(self, id=-1, pos=DefaultPosition, size=DefaultSize, style=TAB_TRAVERSAL|NO_BORDER)



def main():
    app = wx.App(False)
    frame = OpenPortItFrame(None, -1, ' ')
    frame.Show(False)
#    frame.Show(True)
    app.MainLoop()

    pass

if __name__ == '__main__':
    main()