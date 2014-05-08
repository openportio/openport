import subprocess
import sys
import os
import urllib, urllib2
from time import sleep
import signal
import getpass
import traceback

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))

from UserDict import UserDict
import argparse
from services import osinteraction
from services.logger_service import get_logger, set_log_level
from services.osinteraction import is_linux, OsInteraction
from tray.globals import Globals
from apps.openport_api import open_port
from common.session import Session

logger = get_logger('openport_app')


def quote_path(path):
    split = path.split(os.sep)
    logger.debug( split )
    quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
    return os.sep.join(quoted)

class OpenportApp(object):

    def __init__(self):
        self.tray_app_started = False
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()
        self.args = UserDict()
        self.session = None
        if self.os_interaction.is_compiled():
            sys.stdout = open(self.os_interaction.get_app_data_path('apps.out.log'), 'a')
            sys.stderr = open(self.os_interaction.get_app_data_path('apps.error.log'), 'a')
        try:
            signal.signal(signal.SIGINT, self.handleSigTERM)
        except ValueError:
            pass
            # Do not handle the sigterm signal, otherwise the share will not be restored after reboot.
            #signal.signal(signal.SIGTERM, self.handleSigTERM)

    def handleSigTERM(self, signum, frame):
        logger.debug('got signal %s' % signum)
        if self.tray_app_started and self.session:
            self.inform_tray_app_stop(self.session, self.args.tray_port)
        sys.exit(3)

    def inform_tray_app_stop(self, share, tray_port, start_tray=True):
        logger.debug('Informing tray we\'re stopping.')
        url = 'http://127.0.0.1:%s/stopShare' % tray_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=1).read()
            if response.strip() != 'ok':
                logger.error(response)
        except Exception, detail:
            logger.error("An error has occured while informing the tray: %s" % detail)

    def start_tray_application(self):
        if self.tray_app_started:
            return
        self.tray_app_started = True

        command = self.os_interaction.get_python_exec()
        if self.os_interaction.is_compiled():
            command.extend([quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openporttray.exe'))])
        else:
            command.extend(['-m', 'tray.openporttray'])
        command = OsInteraction.set_variable(command, '--tray-port', self.args.tray_port)
        command = OsInteraction.set_variable(command, '--database', self.args.tray_database)
        command = OsInteraction.set_variable(command, '--server', self.args.server)
        if self.args.no_gui:
            command = OsInteraction.set_variable(command, '--no-gui')
        logger.debug('starting tray: %s' % command)
    #    output = self.os_interaction.run_command_silent(command) #hangs
    #    logger.debug('tray stopped: %s ' % output)

        def start_tray():
            try:
                output = self.os_interaction.run_command_silent(command) #hangs
                logger.debug('tray stopped: %s ' % output)
            except Exception, e:
                logger.error(e)
        self.os_interaction.spawnDaemon(start_tray)

    def inform_tray_app_new(self, share, tray_port, start_tray=True):
        url = 'http://127.0.0.1:%s/newShare' % tray_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=5).read()
            if response.strip() != 'ok':
                logger.error(response)
            else:
                self.tray_app_started = True
        except Exception, detail:
            logger.debug('Error occurred while informing the tray, starting the tray: %s' % start_tray)
            if not start_tray:
                tb = traceback.format_exc()
                logger.error('An error has occurred while informing the tray: %s\n%s' % (detail, tb))
            else:
                self.start_tray_application()
                sleep(5)
                self.inform_tray_app_new(share, tray_port, start_tray=False)


    def inform_tray_app_error(self, share, tray_port):
        url = 'http://127.0.0.1:%s/errorShare' % tray_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=5).read()
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

    def inform_tray_app_success(self, share, tray_port):
        url = 'http://127.0.0.1:%s/successShare' % tray_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=5).read()
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

    def copy_share_to_clipboard(self, share):
        self.os_interaction.copy_to_clipboard(share.get_link().strip())

    def get_restart_command(self, session):
        if is_linux():
            command = ['sudo', '-u', getpass.getuser()]
        else:
            command = []
        if sys.argv[0][-3:] == '.py':
            if os.path.exists('env/bin/python'):
                command.extend(['env/bin/python'])
            else:
                command.extend(['python'])
        command.extend(sys.argv)

        #if not '--tray-port' in command:
        #    command.extend(['--tray-port', '%s' % tray_port] )
        command = OsInteraction.set_variable(command, '--request-port', session.server_port)
        command = OsInteraction.set_variable(command, '--local-port', session.local_port)
        if session.server_session_token != '':
            command = OsInteraction.set_variable(command, '--request-token', session.server_session_token)
        command = OsInteraction.set_variable(command, '--hide-message')
        command = OsInteraction.set_variable(command, '--no-clipboard')
        command = OsInteraction.set_variable(command, '--start-tray', False)
        command = OsInteraction.unset_variable(command, '--tray-database')
        command = OsInteraction.set_variable(command, '--tray-port', self.args.tray_port)

        return command

    def add_default_arguments(self, parser, local_port_required=True):
        parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
        parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
        parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new share.')
        parser.add_argument('--start-tray', type=bool, default=True, help='Do not start a tray app if none can be found.')
        parser.add_argument('--tray-database', type=str, default='', help='The database the tray should use if launched from this app.')
        parser.add_argument('--local-port', type=int, help='The port you want to openport.', required=local_port_required, default=-1)
        parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--no-gui', action='store_true', help='Start the app without a gui.')
        parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
        parser.add_argument('--http-forward', action='store_true', help='Request an http forward, so you can connect to port 80 on the server.')
        parser.add_argument('--server', default='www.openport.be', help=argparse.SUPPRESS)

    def init_app(self, args):
        logger.debug('client pid:%s' % os.getpid())
        if args.verbose:
            from logging import DEBUG
            set_log_level(DEBUG)

        if args.no_gui:
            args.hide_message = True
            args.no_clipboard = True

        if not args.start_tray:
            args.tray_port = -1

        self.globals.server = args.server

        self.args = args

    def start(self):
        parser = argparse.ArgumentParser()
        self.add_default_arguments(parser)
        self.args = parser.parse_args()

        self.init_app(self.args)

        if not self.args.hide_message:
            import wx
            self.app = wx.App(redirect=False)

        def show_message_box(session):
            if not self.args.hide_message:
                wx.MessageBox('Your local port %s is now reachable on %s' % ( session.local_port, session.get_link()), 'Info',
                          wx.OK | wx.ICON_INFORMATION)

        self.first_time = True

        def callback(ignore):
            if not self.first_time:
                return
            self.first_time = False

            session.restart_command = self.get_restart_command(session)
            if self.args.tray_port > 0:
                self.inform_tray_app_new(session, self.args.tray_port, start_tray=self.args.start_tray)

            session.error_observers.append(self.error_callback)
            session.success_observers.append(self.success_callback)

            if not self.args.no_clipboard:
                self.copy_share_to_clipboard(session)
            if not self.args.hide_message:
                show_message_box(session)

        session = Session()
        session.local_port = int(self.args.local_port)
        session.server_port = self.args.request_port
        session.server_session_token = self.args.request_token
        session.http_forward = self.args.http_forward

        #        app.MainLoop()

        def show_error(error_msg):
            if not self.args.hide_message:
                import wx
                wx.MessageBox(error_msg, 'Error', wx.OK | wx.ICON_ERROR)
            else:
                print error_msg

        self.session = session

        open_port(session, callback, show_error, server=self.args.server)

    def error_callback(self, session):
        logger.debug('error')
        if self.args.tray_port > 0 and self.tray_app_started:
            self.inform_tray_app_error(session, self.args.tray_port)

    def success_callback(self, session):
        logger.debug('success')
        if self.args.tray_port > 0 and self.tray_app_started:
            self.inform_tray_app_success(session, self.args.tray_port)


if __name__ == '__main__':
    app = OpenportApp()

    app.start()
