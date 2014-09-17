import os
import sys

from apps.openport_app import OpenportApp
from services import crypt_service
from common.share import Share
from services.logger_service import get_logger
from apps.servefile import serve_file_on_port
from time import sleep
logger = get_logger('openportit')

def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


class OpenportItApp(OpenportApp):

    def __init__(self):
        super(OpenportItApp, self).__init__()

    def open_port_file(self, share, callback=None):
        import threading

        if share.local_port == -1:
            share.local_port = get_open_port()
        thr = threading.Thread(target=serve_file_on_port, args=(share.filePath, share.local_port, share.token))
        thr.setDaemon(True)
        thr.start()

        self.openport.start_port_forward(share, callback=callback, server=self.args.server)

    def start(self):
        logger.debug('client pid:%s' % os.getpid())
        import argparse


        parser = argparse.ArgumentParser()
        self.add_default_arguments(parser, local_port_required=False)
        parser.add_argument('--file-token', default='', help='The token needed to download the file.')
        parser.add_argument('filename', help='The file you want to openport.')
        args = parser.parse_args()

        self.init_app(args)

        def show_message_box(share):
            if not args.hide_message:
                import wx
                wx.MessageBox('You can now download your file(s) from %s\nThis link has been copied to your clipboard.' % (
                share.get_link()), 'Info', wx.OK | wx.ICON_INFORMATION)

        def get_restart_command_for_share(share):
            command = self.get_restart_command(share)
            if not '--file-token' in command:
                command.extend(['--file-token', share.token])
            return command

        self.first_time = True

        def callback(ignore):
#            global first_time
            if not self.first_time:
                return
            self.first_time = False

            share.restart_command = get_restart_command_for_share(share)
            if args.manager_port > 0:
                self.inform_manager_app_new(share, args.manager_port, start_manager=(not args.no_manager))

            share.error_observers.append(self.error_callback)
            share.success_observers.append(self.success_callback)

            if not args.no_clipboard:
                self.copy_share_to_clipboard(share)
            if args.hide_message:
                logger.info('Your file can be downloaded from %s' % share.get_link())
            else:
                show_message_box(share)

        share = Share()
        if args.file_token == '':
            share.token = crypt_service.get_token()
        else:
            share.token = args.file_token
        share.filePath = os.path.join(os.getcwd(), args.filename)
        share.server_port = args.request_port
        share.local_port = args.local_port
        share.server_session_token = args.request_token

        self.session = share
        self.open_port_file(share, callback)

        while True:
            sleep(1)

if __name__ == '__main__':
    app = OpenportItApp()
    app.start()