import os
import sys, wx, webbrowser

class OpenPortItTaskBarIcon(wx.TaskBarIcon):

    def __init__(self, parent):  
        wx.TaskBarIcon.__init__(self)  
        self.parentApp = parent
        dir = os.path.dirname( os.path.realpath( __file__ ) )
        if dir[-3:] == 'zip':
            dir = os.path.dirname(dir)
        self.icon = wx.Icon(os.path.join(dir, "logo-base.png"),wx.BITMAP_TYPE_PNG)
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

class OpenPortItFrame(wx.Frame):

    def __init__(self, parent, id, title):  
        wx.Frame.__init__(self, parent, -1, title, size = (1, 1),  
            style=wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE)  

        self.tbicon = OpenPortItTaskBarIcon(self)
        self.tbicon.Bind(wx.EVT_MENU, self.exitApp, id=wx.ID_EXIT)   
        self.Show(True)  

    def exitApp(self,event):
        self.tbicon.RemoveIcon()
        self.tbicon.Destroy()
        sys.exit()

    def viewShares(self,event):
        pass  

#---------------- run the program -----------------------  
def main(argv=None):  
    app = wx.App(False)  
    frame = OpenPortItFrame(None, -1, ' ')
    frame.Show(False)
    app.MainLoop()  

if __name__ == '__main__':  
    main()