import datetime
import os
import sys

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))
from manager import dbhandler
import wx
from wx._core import EVT_PAINT
from wx._gdi import PaintDC
from common.share import Share
from services import osinteraction
from manager.globals import Globals
from services.logger_service import get_logger
from services import qr_service, image_service
from gui.trayicon import OpenPortItTaskBarIcon

from gui_tcp_server import start_server_thread, app_communicate, register_with_app

from services.logger_service import set_log_level
import logging


logger = get_logger(__name__)

noColor = True
BYTES_PER_MB = 1024*1024

COLOR_NO_APP_RUNNING = (204, 204, 204)
COLOR_APP_ERROR = (255, 52, 0)
COLOR_OK = wx.NullColour


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
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()

        iconFile = self.os_interaction.get_resource_path('logo-base.ico')
        icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.addTrayIcon()

    def exitApp(self, event):
        self.tbicon.RemoveIcon()
        self.tbicon.Destroy()
        os._exit(0)
        #self.application.exitApp(event)

    def addTrayIcon(self):
        self.tbicon = OpenPortItTaskBarIcon(self)
        self.tbicon.addItem('View shares', self.Show)
        self.tbicon.menu.AppendSeparator()
        self.tbicon.addItem('Exit', self.exitApp)
        self.tbicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.Show)

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
        self.Bind(wx.EVT_MENU, self.exitApp, id=105)
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
                #self.application.startOpenportItProcess(path)
                pass
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

        self.account_panel = wx.Panel(self, style=wx.BORDER_NONE)
        self.frame_sizer.Add(self.account_panel, 0, wx.EXPAND|wx.ALL, 0)
        self.account_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        self.account_amount_text = wx.StaticText(self.account_panel, -1, 'Openport - Easy and secure reverse SSH')
        self.account_amount_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.account_amount_text.SetSize(self.account_amount_text.GetBestSize())
        self.account_panel_sizer.Add(self.account_amount_text, 0, wx.EXPAND|wx.ALL,5)

        self.account_reset_text = wx.StaticText(self.account_panel, -1, ' ')
        self.account_reset_text.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        self.account_reset_text.SetSize(self.account_reset_text.GetBestSize())
        self.account_panel_sizer.Add(self.account_reset_text, 0, wx.EXPAND|wx.ALL, 5)
        self.account_panel.SetSizer(self.account_panel_sizer)
        self.account_panel.SetMinSize((400, 50))

        self.account_panel.Layout()
        self.Layout()


        self.scrolling_window = wx.ScrolledWindow(self)
        if not noColor:
            self.scrolling_window.SetBackgroundColour('green')
        self.SetSize((400, 300))

        self.scrolling_window.SetScrollRate(8,8)
        self.scrolling_window.EnableScrolling(True,True)
        self.scrolling_window_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll_panel_sizer = wx.BoxSizer( wx.VERTICAL )
        self.scrolling_window_sizer.Add(self.scroll_panel_sizer, 1, wx.EXPAND)
        self.scrolling_window.SetSizer(self.scrolling_window_sizer)

        self.frame_sizer.Add(self.scrolling_window, 1, wx.EXPAND|wx.ALL)

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

    def onFocus(self, event):
        self.scrolling_window.SetFocus()

    def add_share(self, share):

        if isinstance(share, Share):
            filename = share.filePath
        else:
            filename = str(share.local_port)

        share_panel = wx.Panel(self.scrolling_window, id=2, style=wx.BORDER_RAISED)
        self.scrolling_window_sizer.Add(share_panel, 0, wx.EXPAND, 0)
        share_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        top_panel = wx.Panel(share_panel)
        top_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        text_panel = wx.Panel(top_panel)
        text_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        filename_text = wx.StaticText(text_panel, -1, os.path.basename(filename))
        filename_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        filename_text.SetSize(filename_text.GetBestSize())
        text_panel_sizer.Add(filename_text, 1, wx.EXPAND|wx.ALL, 5)

        link_text = wx.StaticText(text_panel, -1, share.get_link())
        link_text.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD))
        link_text.SetSize(link_text.GetBestSize())
        text_panel_sizer.Add(link_text, 1, wx.EXPAND|wx.ALL, 5)

        text_panel.SetSizer(text_panel_sizer)
        top_panel_sizer.Add(text_panel, 1, wx.EXPAND)

        button_panel = wx.Panel(top_panel)
        button_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_panel_sizer)
        if not noColor:
            button_panel.SetBackgroundColour((255, 52, 0))
        top_panel_sizer.Add(button_panel, 0, wx.ALIGN_LEFT | wx.EXPAND)

        def copy_link(evt):
            self.os_interaction.copy_to_clipboard(share.get_link())
        copy_link_button = wx.Button(button_panel, -1, label="Copy link")
        copy_link_button.Bind(wx.EVT_BUTTON, copy_link)
        button_panel_sizer.Add(copy_link_button, 0, wx.EXPAND|wx.ALL)

        def send_stop_share(evt):
#            self.add_share(share)
           # return
            logger.info("stopping %s" % share.id)
            s = dbhandler.getInstance().get_share_by_local_port(share.local_port)
            if len(s) > 0 and s[0].app_port and osinteraction.getInstance().pid_is_openport_process(s[0].pid):
                self.notify_app_down(s[0])
                app_communicate(s[0], 'exit')
            else:
                self.remove_share(share)
                dbhandler.getInstance().stop_share(share)

        stop_sharing_button = wx.Button(button_panel, -1, label="Stop sharing")
        stop_sharing_button.Bind(wx.EVT_BUTTON, send_stop_share)
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
        self.share_panels[share.local_port] = share_panel

        share_panel.GetParent().Layout()
        self.frame_sizer.Layout()

    def show_qr(self, title, data):
        pil_img = qr_service.get_qr_image(data)
        wx_img = image_service.PilImageToWxImage(pil_img)
        qr_frame = QrFrame(None, -1, title)
        qr_frame.add_img(wx_img)
        qr_frame.Show(True)

    def notify_error(self, share):
        logger.debug('notify_error')
        if share.local_port in self.share_panels:
            share_panel = self.share_panels[share.local_port]
            share_panel.SetBackgroundColour(COLOR_APP_ERROR)
            share_panel.Refresh()
        else:
            logger.debug('share not found while notify error')

    def notify_app_down(self, share):
        logger.debug('notify_error')
        if share.local_port in self.share_panels:
            share_panel = self.share_panels[share.local_port]
            share_panel.SetBackgroundColour(COLOR_NO_APP_RUNNING)
            share_panel.Refresh()
        else:
            logger.debug('share not found while notify error')

    def notify_success(self, share):
        logger.debug('notify_success')
        if share.local_port in self.share_panels:
            share_panel = self.share_panels[share.local_port]
            share_panel.SetBackgroundColour(COLOR_OK)
            share_panel.Refresh()
        else:
            logger.debug('share not found while notify success')

    def remove_share(self, share):
        logger.debug('remove_share %s' % share.local_port)
        if share.local_port in self.share_panels:
            share_panel = self.share_panels[share.local_port]
            self.scrolling_window.RemoveChild(share_panel)
            self.scrolling_window_sizer.Remove(share_panel)
            share_panel.Destroy()
            self.share_panels.pop(share.local_port)
            self.Layout()
        else:
            logger.debug('share not found while removing')


class QrFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id)#, title,
            #style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE|wx.NO_BORDER|
             #     wx.FRAME_TOOL_WINDOW|wx.STAY_ON_TOP)

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
            dc.DrawBitmap(self.image.ConvertToBitmap(), 0, 0)

if __name__ == '__main__':
    set_log_level(logging.DEBUG)

    app = wx.App(False)
    frame = SharesFrame(None, -1, ' ', None)
    db_handler = dbhandler.getInstance()

    shares = db_handler.get_shares()

    for share in shares:
        frame.add_share(share)
        if not osinteraction.getInstance().pid_is_openport_process(share.pid):
            frame.notify_app_down(share)

    frame.Show(True)
    Globals().app = frame

    start_server_thread()

    for share in shares:
        register_with_app(share)

    app.MainLoop()
