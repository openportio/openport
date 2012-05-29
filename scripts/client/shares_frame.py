import os
import wx

noColor = True

class SharesFrame(wx.Frame):

    def onClose(self, evt):
        self.Hide()

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title,
            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE|wx.NO_BORDER|wx.FRAME_TOOL_WINDOW|wx.STAY_ON_TOP)
        self.rebuild()
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def rebuild(self):
        self.share_panels = {}
        self.scrolling_window = wx.ScrolledWindow( self )
        if not noColor:self.scrolling_window.SetBackgroundColour('green')
        self.SetSize((400, 300))

        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.scrolling_window.SetScrollRate(8,8)
        self.scrolling_window.EnableScrolling(True,True)
        self.scrolling_window_sizer = wx.BoxSizer( wx.VERTICAL )
        self.scroll_panel_sizer = wx.BoxSizer( wx.VERTICAL )
        self.scrolling_window_sizer.Add(self.scroll_panel_sizer,0,wx.ALIGN_LEFT,wx.EXPAND)
        self.scrolling_window.SetSizer(self.scrolling_window_sizer)

        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)
        self.frame_sizer.Add(self.scrolling_window, wx.EXPAND)

        self.scrolling_window.SetFocus()
        self.Bind(wx.EVT_SET_FOCUS, self.onFocus)

        self.scrolling_window.Layout()
        self.SetSizer(self.frame_sizer)
        self.Layout()

    def OnSize(self, event):
        self.scrolling_window.SetSize(self.GetClientSize())

    def onFocus(self, event):
        self.scrolling_window.SetFocus()

    def add_share(self, share, callbacks={}):
        filename = share.filePath

        share_panel = wx.Panel(self.scrolling_window, id=share.id, style=wx.SIMPLE_BORDER)
        self.scrolling_window_sizer.Add(share_panel, 0, wx.EXPAND, 0)
        share_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        top_panel = wx.Panel(share_panel)
        top_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        filename_text = wx.StaticText(top_panel, -1, os.path.basename(filename))
        filename_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        filename_text.SetSize(filename_text.GetBestSize())
        top_panel_sizer.Add(filename_text, 1, wx.EXPAND|wx.ALL, 5)

        button_panel = wx.Panel(top_panel)
        button_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_panel_sizer)
        if not noColor:button_panel.SetBackgroundColour('red')
        top_panel_sizer.Add(button_panel, 0, wx.ALIGN_LEFT, 5)

        def copy_link(evt):
            if 'copy_link' in callbacks:
                callbacks['copy_link'](share)
        copy_link_button = wx.Button(button_panel, -1, label="Copy link")
        copy_link_button.Bind(wx.EVT_BUTTON, copy_link)
        button_panel_sizer.Add(copy_link_button, 0, wx.EXPAND|wx.ALL, 5)

        def stop_sharing(evt):
            if 'stop' in callbacks:
                callbacks['stop'](share)
        stop_sharing_button = wx.Button(button_panel, -1, label="Stop sharing")
        stop_sharing_button.Bind(wx.EVT_BUTTON, stop_sharing)
        button_panel_sizer.Add(stop_sharing_button, 0, wx.EXPAND|wx.ALL, 5)


        top_panel.SetSizer(top_panel_sizer)
        share_panel_sizer.Add(top_panel, 0, wx.EXPAND, 5)

        dir_text = wx.StaticText(share_panel, -1, os.path.dirname(filename))
        dir_text.SetSize(dir_text.GetBestSize())
        share_panel_sizer.Add(dir_text, 0, wx.EXPAND|wx.ALL, 5)

        share_panel.SetSizer(share_panel_sizer)
        share_panel.Layout()
        self.share_panels[share.id] = share_panel
        self.scrolling_window.Layout()
        #self.frame_sizer.Fit(self)
        #self.Layout()

    def remove_share(self, share):
        share_panel = self.share_panels[share.id]
        self.scrolling_window.RemoveChild(share_panel)
        self.scrolling_window_sizer.Remove(share_panel)
        share_panel.Destroy()
        self.share_panels.pop(share.id)
        self.scrolling_window.Layout()
      #  self.Layout()

def main():
    from dbhandler import DBHandler

    def stop_sharing(share):
        print "stopping %s" % share.id
        frame.remove_share(share)

    def add_share1(ignore):
        frame.add_share(share1, callbacks=callbacks)

    app = wx.App(False)
    frame = SharesFrame(None, -1, ' ')
    dbhandler = DBHandler()

    shares = dbhandler.get_shares()
    callbacks = {'stop': add_share1}
    share1 = shares[0]

    for share in shares:
        frame.add_share(share, callbacks=callbacks)
        callbacks = {'stop': stop_sharing}


    #    frame.Show(False)
    frame.Show(True)
    app.MainLoop()

    pass

if __name__ == '__main__':
    main()