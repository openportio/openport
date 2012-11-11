#!/usr/bin/env python
import os

import sys
import wx
from apps.keyhandling import get_or_create_public_key, PUBLIC_KEY_FILE, PRIVATE_KEY_FILE
from apps.portforwarding import PortForwardingService
from common.session import Session
from services.logger_service import get_logger

from apps.openport import request_port

logger = get_logger('openport_win')

SERVER_SSH_PORT = 22
SERVER_SSH_USER = 'open'

class PortForwardResponse():
    def __init__(self, server='', remote_port=-1, message='', account_id=-1, key_id=-1, local_port=-1, session_token=''):
        self.server = server
        self.remote_port = remote_port
        self.message = message
        self.account_id = account_id
        self.key_id = key_id
        self.session_token = session_token

    def __init__(self,dict):
        self.from_dict(dict)

    def from_dict(self, dict):
        self.server = dict['server_ip']
        self.remote_port = dict['server_port']
        self.message = dict['message']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        self.session_token = dict['session_token']

def request_open_port(local_port, restart_session_token = '', request_server_port=-1):

    public_key = get_or_create_public_key()

    logger.debug("requesting port forward - remote port: %s, restart session token: %s" % (request_server_port, restart_session_token))
    dict = request_port( public_key, restart_session_token=restart_session_token, request_server_port=request_server_port )

    if 'error' in dict:
        wx.MessageBox('An error has occured:\n%s' %(dict['error']), 'Error', wx.OK | wx.ICON_ERROR)
        sys.exit(8)
    logger.debug(dict)

    response = PortForwardResponse(dict)

    if request_server_port != '' and request_server_port != response.remote_port:
        logger.error( 'Did not get requested server port (%s), but got %s' % (request_server_port, response.remote_port))

    return response

def open_port(session, callback=None):

    import threading
    from time import sleep

    while True:
        try:
            response = request_open_port(
                session.local_port,
                request_server_port=session.server_port,
                restart_session_token=session.server_session_token
            )

            session.server = response.server
            session.server_port = response.remote_port
            session.pid = os.getpid()
            session.account_id = response.account_id
            session.key_id = response.key_id
            session.server_session_token = response.session_token

            if callback is not None:
                import threading
                thr = threading.Thread(target=callback, args=(session,))
                thr.setDaemon(True)
                thr.start()

            portForwardingService = PortForwardingService(
                session.local_port,
                response.remote_port,
                response.server,
                SERVER_SSH_PORT,
                SERVER_SSH_USER,
                PUBLIC_KEY_FILE,
                PRIVATE_KEY_FILE,
                success_callback=session.notify_success,
                error_callback=session.notify_error)
            portForwardingService.start() #hangs
        except Exception as e:
            logger.error(e)
        finally:
            sleep(10)


if __name__ == '__main__':
    from apps.openport_app import inform_tray_app_new, inform_tray_app_error, inform_tray_app_success, app, copy_share_to_clipboard, init

    init()
    logger.debug('client pid:%s' % os.getpid())
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
    parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
    parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new session.')
    parser.add_argument('local_port', help='The port you want to openport.')
    args = parser.parse_args()

    def show_message_box(session):
        wx.MessageBox('Your local port %s is now reachable on %s' % ( session.local_port, session.get_link()), 'Info',
            wx.OK | wx.ICON_INFORMATION)

    first_time = True
    def callback(ignore):
        global first_time
        if not first_time:
            return
        first_time = False
        if args.tray_port > 0:
            inform_tray_app_new(session, args.tray_port)

        session.error_observers.append(error_callback)
        session.success_observers.append(success_callback)

        if not args.no_clipboard:
            copy_share_to_clipboard(session)
        if not args.hide_message:
            show_message_box(session)

    def error_callback(session):
        logger.debug('error')
        if args.tray_port > 0:
            inform_tray_app_error(session, args.tray_port)

    def success_callback(session):
        logger.debug('success')
        if args.tray_port > 0:
            inform_tray_app_success(session, args.tray_port)

    session = Session()
    session.local_port = int(args.local_port)

    app.MainLoop()
    open_port(session, callback)



