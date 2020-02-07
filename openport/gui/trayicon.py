import wx
from openport.services import osinteraction
import os


class OpenPortItTaskBarIcon(wx.TaskBarIcon):

    def __init__(self, parent):
        super(OpenPortItTaskBarIcon, self).__init__()
        self.frame = parent
        self.parentApp = parent
        self.os_interaction = osinteraction.getInstance()
        if osinteraction.is_mac():
            icon_file = self.os_interaction.get_resource_path('resources/icon.icns')
            self.icon = wx.Icon(icon_file, wx.BITMAP_TYPE_ICON)
        else:
            icon_file = self.os_interaction.get_resource_path('resources/icon.ico')
            self.icon = wx.Icon(icon_file, wx.BITMAP_TYPE_ICO)
        self.SetIcon(self.icon, "Openport")
        self.imgidx = 1

   #     self.CreateMenu()
        self.items = []

    def CreatePopupMenu(self):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        self.menu = wx.Menu()
        #menu.Append(self.TBMENU_RESTORE, "Restore wxPython Demo")
        #menu.Append(self.TBMENU_CLOSE,   "Close wxPython Demo")
        for label, callback in self.items:
            if label == '---':
                self.menu.AppendSeparator()
            else:
                self._addItem(label, callback)

        return self.menu

    def addItem(self, label, callBackFunction):
        self.items.append((label, callBackFunction))

    def _addItem(self, label, callBackFunction):
        newItem = wx.NewId()
        self.menu.Append(newItem, label)
        self.Bind(wx.EVT_MENU, callBackFunction, id=newItem)

    def ShowMenu(self, event):
        print('event %s' % event)
        print("ShowMenu")
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