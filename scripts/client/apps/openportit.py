import os
import sys
import wx
from apps.openport_app import inform_tray_app_new, inform_tray_app_error, inform_tray_app_success, app, copy_share_to_clipboard, init

print os.getcwd()
from services import crypt_service
from common.share import Share
from services.logger_service import get_logger

clients = {}

from apps.servefile import serve_file_on_port
from apps.openport_win import open_port

logger = get_logger('openportit')

def get_open_port():
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def open_port_file(share, callback=None):
    import threading

    if share.local_port == -1:
        share.local_port = get_open_port()
    thr = threading.Thread(target=serve_file_on_port, args=(share.filePath, share.local_port, share.token))
    thr.setDaemon(True)
    thr.start()
    open_port(share, callback=callback)

if __name__ == '__main__':

    init()
    logger.debug('client pid:%s' % os.getpid())
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
    parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
    parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new share.')
    parser.add_argument('--local-port', type=int, default=-1, help='The local port to start the share on.')
    parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
    parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
    parser.add_argument('filename', help='The file you want to openport.')
    args = parser.parse_args()

    def show_message_box(share):
        wx.MessageBox('You can now download your file(s) from %s\nThis link has been copied to your clipboard.' % (
        share.get_link()), 'Info', wx.OK | wx.ICON_INFORMATION)


    first_time = True
    def callback(ignore):
        global first_time
        if not first_time:
            return
        first_time = False
        if args.tray_port > 0:
            inform_tray_app_new(share, args.tray_port)

        share.error_observers.append(error_callback)
        share.success_observers.append(success_callback)

        if not args.no_clipboard:
            copy_share_to_clipboard(share)
        if not args.hide_message:
            show_message_box(share)

    def error_callback(share):
        logger.debug('error')
        if args.tray_port > 0:
            inform_tray_app_error(share, args.tray_port)

    def success_callback(share):
        logger.debug('success')
        if args.tray_port > 0:
            inform_tray_app_success(share, args.tray_port)

    share = Share()
    share.token = crypt_service.get_token()
    share.filePath = os.path.join(os.getcwd(), args.filename)
    share.server_port = args.request_port
    share.local_port = args.local_port
    share.server_session_token = args.request_token
    share.restart_command = ' '.join(sys.argv)

    app.MainLoop()
    open_port_file(share, callback)



