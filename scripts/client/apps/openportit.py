import os
import sys
from apps.openport_app import inform_tray_app_new, inform_tray_app_error, inform_tray_app_success,  \
    copy_share_to_clipboard, init, get_restart_command, add_default_arguments

from services import crypt_service
from common.share import Share
from services.logger_service import get_logger

clients = {}

from apps.servefile import serve_file_on_port
from apps.openport_api import open_port

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
    import wx

    init()
    logger.debug('client pid:%s' % os.getpid())
    import argparse

    parser = argparse.ArgumentParser()
    add_default_arguments(parser, local_port_required=False)
    parser.add_argument('--file-token', default='', help='The token needed to download the file.')
    parser.add_argument('filename', help='The file you want to openport.')
    args = parser.parse_args()

    def show_message_box(share):
        wx.MessageBox('You can now download your file(s) from %s\nThis link has been copied to your clipboard.' % (
        share.get_link()), 'Info', wx.OK | wx.ICON_INFORMATION)

    def get_restart_command_for_share(share):
        command = get_restart_command(share)
        if not '--file-token' in command:
            command.extend(['--file-token', share.token])
        return command

    first_time = True
    def callback(ignore):
        global first_time
        if not first_time:
            return
        first_time = False

        share.restart_command = get_restart_command_for_share(share)
        if args.tray_port > 0:
            inform_tray_app_new(share, args.tray_port, start_tray=(not args.no_tray))

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
    if args.file_token == '':
        share.token = crypt_service.get_token()
    else:
        share.token = args.file_token
    share.filePath = os.path.join(os.getcwd(), args.filename)
    share.server_port = args.request_port
    share.local_port = args.local_port
    share.server_session_token = args.request_token

    app = wx.App(redirect=False)
    app.MainLoop()
    open_port_file(share, callback)
