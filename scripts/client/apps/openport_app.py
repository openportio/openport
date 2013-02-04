import subprocess
import sys
import os
import urllib, urllib2
from time import sleep
import wx

print os.getcwd()
sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))
from services.osinteraction import OsInteraction
from services.logger_service import get_logger

logger = get_logger('openport_app')

app = wx.App(redirect=False)

os_interaction = None

def init():
    global app
    global os_interaction
    os_interaction = OsInteraction()
    if os_interaction.is_compiled():
        sys.stdout = open(os_interaction.get_app_data_path('apps.out.log'), 'a')
        sys.stderr = open(os_interaction.get_app_data_path('apps.error.log'), 'a')

tray_app_started = False

def start_tray_application():
    global tray_app_started
    if tray_app_started:
        return
    tray_app_started = True

    if sys.argv[0][-3:] == '.py':
        command = ['start', 'python', '-m', 'tray.openporttray']
    else:
        command = ['start', quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openporttray.exe'))]
    logger.debug( command )
    subprocess.call(' '.join(command), shell=True)


def quote_path(path):
    split = path.split(os.sep)
    logger.debug( split )
    quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
    return os.sep.join(quoted)



def inform_tray_app_new(share, tray_port, start_tray=True):
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
            inform_tray_app_new(share, tray_port, start_tray=False)


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

def copy_share_to_clipboard(share):
    os_interaction.copy_to_clipboard(share.get_link().strip())




if __name__ == '__main__':
    init()
    logger.debug('client pid:%s' % os.getpid())
    import argparse
    from apps.openport_api import open_port
    from common.session import Session

    parser = argparse.ArgumentParser()
    parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
    parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
    parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new session.')
    parser.add_argument('--local-port', type=int, help='The port you want to openport.', required=True)
    parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
    parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
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
    session.restart_command = ' '.join(sys.argv)
    session.server_port = args.request_port
    session.server_session_token = args.request_token

    app.MainLoop()
    open_port(session, callback)
