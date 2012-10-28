import subprocess
import sys
from osinteraction import OsInteraction
from portforwarding import PortForwardingService
from services import crypt_service
from share import Share
from time import sleep
from loggers import get_logger
import urllib, urllib2
from keyhandling import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE

SERVER_SSH_PORT = 22
SERVER_SSH_USER = 'open'
clients = {}

if __name__ == '__main__':
    import wx

    app = wx.App(redirect=False)

import os
from sys import argv

working_dir = os.getcwd()
os.chdir(os.path.realpath(os.path.dirname(argv[0])))
from servefile import serve_file_on_port
from openport_win import open_port

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

    local_port = get_open_port()
    thr = threading.Thread(target=serve_file_on_port, args=(share.filePath, local_port, share.token))
    thr.setDaemon(True)
    thr.start()

    from time import sleep
    while True:
        try:
            response = open_port(
                local_port,
                request_server_port=share.server_port,
                restart_session_token=share.server_session_token
            )

            share.server = response.server
            share.server_port = response.remote_port
            share.pid = os.getpid()
            share.local_port = local_port
            share.account_id = response.account_id
            share.key_id = response.key_id
            share.server_session_token = response.session_token

            if callback is not None:
                import threading
                thr = threading.Thread(target=callback, args=(share,))
                thr.setDaemon(True)
                thr.start()

            portForwardingService = PortForwardingService(
                local_port,
                response.remote_port,
                response.server,
                SERVER_SSH_PORT,
                SERVER_SSH_USER,
                PUBLIC_KEY_FILE,
                PRIVATE_KEY_FILE,
                success_callback=share.notify_success,
                error_callback=share.notify_error)

            clients[local_port] = portForwardingService
            portForwardingService.start() #hangs
        except Exception as e:
            logger.error(e)
        finally:
            sleep(10)

def forward_port(port):
    open_port(port)
    forward_port(port)


def start_tray_application():
    #todo: linux/mac
    if sys.argv[0][-3:] == '.py':
        command = ['start', 'python', 'application.py']
    else:
        command = ['start', quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'application.exe'))]
    logger.debug( command )
    subprocess.call(' '.join(command), shell=True)

def quote_path(path):
    split = path.split(os.sep)
    logger.debug( split )
    quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
    return os.sep.join(quoted)


if __name__ == '__main__':

    os_interaction = OsInteraction()
    if os_interaction.is_compiled():
        sys.stdout = open(os_interaction.get_app_data_path('openportit.out.log'), 'a')
        sys.stderr = open(os_interaction.get_app_data_path('openportit.error.log'), 'a')

    logger.debug('client pid:%s' % os.getpid())
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
    parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
    parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new share.')
    parser.add_argument('filename', help='The file you want to openport.')
    args = parser.parse_args()

    def copy_share_to_clipboard(share):
        os_interaction.copy_to_clipboard(share.get_link().strip())

    def show_message_box(share):
        wx.MessageBox('You can now download your file(s) from %s\nThis link has been copied to your clipboard.' % (
        share.get_link()), 'Info', wx.OK | wx.ICON_INFORMATION)

    def inform_tray_app(share, tray_port, start_tray=True):
        url = 'http://127.0.0.1:%s/newShare' % tray_port
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req).read()
            if response.strip() != 'ok':
                logger.error( response )
        except Exception, detail:
            if not start_tray:
                logger.error( "An error has occured while informing the tray: %s" % detail )
            else:
                start_tray_application()
                sleep(3)
                inform_tray_app(share, tray_port, start_tray=False)


    def inform_tray_app_error(share, tray_port):
        url = 'http://127.0.0.1:%s/errorShare' % tray_port
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req).read()
            if response.strip() != 'ok':
                logger.error( response )
            if response.strip() == 'unknown':
                logger.critical('this share is no longer known by the tray, exiting')
                sys.exit(1)
        except urllib2.URLError, error:
            logger.exception(error)
            sys.exit(1)
        except Exception, detail:
            logger.exception(detail)

    def inform_tray_app_success(share, tray_port):
        url = 'http://127.0.0.1:%s/successShare' % tray_port
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req).read()
            if response.strip() != 'ok':
                logger.error( response )
            if response.strip() == 'unknown':
                logger.critical('this share is no longer known by the tray, exiting')
                sys.exit(1)
        except urllib2.URLError, error:
            logger.exception(error)
            sys.exit(1)
        except Exception, detail:
            logger.exception(detail)

    first_time = True
    def callback(ignore):
        global first_time
        if not first_time:
            return
        first_time = False
        if args.tray_port > 0:
            inform_tray_app(share, args.tray_port)

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
    share.filePath = os.path.join(working_dir, args.filename)

    app.MainLoop()
    open_port_file(share, callback)



