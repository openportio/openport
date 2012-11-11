import subprocess
import sys
import os
import urllib, urllib2
from time import sleep
import wx

print os.getcwd()
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


def start_tray_application():
    #todo: linux/mac
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
