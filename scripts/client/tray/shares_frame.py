import os
import datetime
import wx
from wx._core import EVT_PAINT
from wx._gdi import PaintDC
from common.share import Share
from services.osinteraction import OsInteraction
from tray.globals import Globals
from tray.trayicon import OpenPortItTaskBarIcon
from services.logger_service import get_logger
from services import qr_service, image_service

logger = get_logger(__name__)

noColor = True
BYTES_PER_MB = 1024*1024

class SharesFrame(wx.Frame):

    def onClose(self, evt):
        self.Hide()

    def __init__(self, parent, id, title, application):
        wx.Frame.__init__(self, parent, -1, title,
            style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.application = application
        self.addMenuBar()
        self.rebuild()
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.os_interaction = OsInteraction()
        self.globals = Globals()

        iconFile = self.os_interaction.get_resource_path('logo-base.ico')
        icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.addTrayIcon()

    def exitApp(self,event):
        self.tbicon.RemoveIcon()
        self.tbicon.Destroy()
        self.application.exitApp(event)

    def addTrayIcon(self):
        self.tbicon = OpenPortItTaskBarIcon(self)
        self.tbicon.addItem('View shares', self.application.viewShares)
        self.tbicon.menu.AppendSeparator()
        self.tbicon.addItem('Exit', self.exitApp)
        self.tbicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.application.viewShares)


    def addMenuBar(self):
        menubar = wx.MenuBar()
        file = wx.Menu()
#        help = wx.Menu()
        file.Append(101, '&New share', 'Share a new document')
        self.Bind(wx.EVT_MENU, self.showOpenportItDialog, id=101)

        file.Append(102, '&Open Port', 'Open a new port')
        self.Bind(wx.EVT_MENU, self.showOpenportDialog, id=102)
        file.AppendSeparator()
        quit = wx.MenuItem(file, 105, '&Quit\tCtrl+Q', 'Quit the Application')
        self.Bind(wx.EVT_MENU, self.application.exitApp, id=105)
        file.AppendItem(quit)
        menubar.Append(file, '&File')
#        menubar.Append(help, '&Help')
        self.SetMenuBar(menubar)

    def showOpenportItDialog(self, event):
        dlg = wx.FileDialog(
            self, message="Choose a file to share",
            defaultFile="",
            wildcard="*",
            style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR
        )
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            for path in paths:
                self.application.startOpenportItProcess(path)
        dlg.Destroy()

    def showOpenportDialog(self, event):
        dialog = wx.NumberEntryDialog(self,
            'Choose a port you want to open',
            '( 1 - 65535 )',
            'Openport - Choose a port you want to open', 80, 1, 65535)
        dialog.ShowModal()

        if dialog.GetReturnCode() == wx.ID_OK:
            self.application.startOpenportProcess(dialog.GetValue())


    def rebuild(self):
        self.share_panels = {}
        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)

        self.account_panel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.frame_sizer.Add(self.account_panel, 0, wx.EXPAND|wx.ALL, 0)
        self.account_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        self.account_amount_text = wx.StaticText(self.account_panel, -1, 'Updating...')
        self.account_amount_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.account_amount_text.SetSize(self.account_amount_text.GetBestSize())
        self.account_panel_sizer.Add(self.account_amount_text, 0, wx.EXPAND|wx.ALL,5)

        self.account_reset_text = wx.StaticText(self.account_panel, -1, ' ')
        self.account_reset_text.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        self.account_reset_text.SetSize(self.account_reset_text.GetBestSize())
        self.account_panel_sizer.Add(self.account_reset_text, 0, wx.EXPAND|wx.ALL,5)
        self.account_panel.SetSizer(self.account_panel_sizer)

        self.account_panel.Layout()
        self.Layout()


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

        self.frame_sizer.Add(self.scrolling_window, wx.EXPAND)

        self.scrolling_window.SetFocus()
        self.Bind(wx.EVT_SET_FOCUS, self.onFocus)

        self.scrolling_window.Layout()
        self.SetSizer(self.frame_sizer)
        self.Layout()

    def update_account( self,
        bytes_this_month = -1,
        next_counter_reset_time = datetime.datetime.now(),
        max_bytes = -1,
        ):
        self.account_amount_text.SetLabel( '%sMB / %sMB used' %(bytes_this_month/BYTES_PER_MB, max_bytes / BYTES_PER_MB ))
        self.account_reset_text.SetLabel('Counters will be reset on %s' % next_counter_reset_time)

    def OnSize(self, event):
        (frame_width, frame_height) = self.GetClientSize()
        account_panel_height = self.account_panel.GetSize()[1]

        self.account_panel.SetSize((frame_width, account_panel_height))
        self.scrolling_window.SetSize((frame_width, frame_height - account_panel_height))

    def onFocus(self, event):
        self.scrolling_window.SetFocus()

    def add_share(self, share, callbacks={}):
        if isinstance(share, Share):
            filename = share.filePath
        else:
            filename = share.local_port

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
            self.os_interaction.copy_to_clipboard(share.get_link())
        copy_link_button = wx.Button(button_panel, -1, label="Copy link")
        copy_link_button.Bind(wx.EVT_BUTTON, copy_link)
        button_panel_sizer.Add(copy_link_button, 0, wx.EXPAND|wx.ALL, 5)

        def stop_sharing(evt):
            if 'stop' in callbacks:
                callbacks['stop'](share)
        stop_sharing_button = wx.Button(button_panel, -1, label="Stop sharing")
        stop_sharing_button.Bind(wx.EVT_BUTTON, stop_sharing)
        button_panel_sizer.Add(stop_sharing_button, 0, wx.EXPAND|wx.ALL, 5)

        def show_qr_evt(evt):
            if isinstance(share, Share):
                title = share.filePath
            else:
                title = share.local_port
            self.show_qr(title, share.get_link())
        qr_button = wx.Button(button_panel, -1, label="Show QR")
        qr_button.Bind(wx.EVT_BUTTON, show_qr_evt)
        button_panel_sizer.Add(qr_button, 0, wx.EXPAND|wx.ALL, 5)

        top_panel.SetSizer(top_panel_sizer)
        share_panel_sizer.Add(top_panel, 0, wx.EXPAND, 5)

        dir_text = wx.StaticText(share_panel, -1, os.path.dirname(filename))
        dir_text.SetSize(dir_text.GetBestSize())
        share_panel_sizer.Add(dir_text, 0, wx.EXPAND|wx.ALL, 5)

        share_panel.SetSizer(share_panel_sizer)
        share_panel.Layout()
        self.share_panels[share.local_port] = share_panel
        self.scrolling_window.Layout()
        #self.frame_sizer.Fit(self)
        #self.Layout()

    def show_qr(self, title, data):
        pil_img = qr_service.get_qr_image(data)
        wx_img = image_service.PilImageToWxImage(pil_img)
        qr_frame = QrFrame(None, -1, title)
        qr_frame.add_img(wx_img)
        qr_frame.Show(True)

    def notify_error(self, share):
        share_panel = self.share_panels[share.local_port]
        share_panel.SetBackgroundColour((240,0,0))
        share_panel.Refresh()
        logger.error('error in share')

    def notify_success(self, share):
        share_panel = self.share_panels[share.local_port]
        share_panel.SetBackgroundColour(wx.NullColour)
        share_panel.Refresh()

    def remove_share(self, share):
        share_panel = self.share_panels[share.local_port]
        self.scrolling_window.RemoveChild(share_panel)
        self.scrolling_window_sizer.Remove(share_panel)
        share_panel.Destroy()
        self.share_panels.pop(share.local_port)
        self.scrolling_window.Layout()
      #  self.Layout()

class QrFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title,
            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE|wx.NO_BORDER|wx.FRAME_TOOL_WINDOW|wx.STAY_ON_TOP)

    def add_img(self, wx_img):
        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)


        self.img_panel = ImagePanel(self, -1)
        self.img_panel.display(wx_img)
        self.frame_sizer.Add(self.img_panel, 0, wx.EXPAND|wx.ALL, 0)
        self.img_panel.Layout()
        self.SetSize((470,480))
        self.Layout()

class ImagePanel(wx.Panel):
    def __init__(self, parent, id):
        wx.Panel.__init__(self, parent, id)
        self.image = None
        EVT_PAINT(self, self.OnPaint)

    def display(self, image):
        self.image = image
        self.Refresh(True)

    def OnPaint(self, evt):
        dc = PaintDC(self)
        if self.image:
            dc.DrawBitmap(self.image.ConvertToBitmap(), 0,0)

def main():
    from openporttray.dbhandler import DBHandler

    def stop_sharing(share):
        logger.info( "stopping %s" % share.id )
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