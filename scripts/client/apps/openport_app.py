import subprocess
import sys
import os
import urllib, urllib2
from time import sleep

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))
from services import osinteraction
from services.logger_service import get_logger

logger = get_logger('openport_app')


def quote_path(path):
    split = path.split(os.sep)
    logger.debug( split )
    quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
    return os.sep.join(quoted)


class OpenportApp():

    def __init__(self):
        self.tray_app_started = False
        self.os_interaction = osinteraction.getInstance()
        if self.os_interaction.is_compiled():
            sys.stdout = open(self.os_interaction.get_app_data_path('apps.out.log'), 'a')
            sys.stderr = open(self.os_interaction.get_app_data_path('apps.error.log'), 'a')

    def start_tray_application(self):
        if self.tray_app_started:
            return
        self.tray_app_started = True

        extra_options = []
        if self.args.no_gui:
            extra_options.append('--no-gui')
        command = self.os_interaction.get_python_exec()
        if self.os_interaction.is_compiled():
            command.extend([quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openporttray.exe'))])
        else:
            command.extend(['-m', 'tray.openporttray'])
        command.extend(extra_options)
        logger.debug(command)
        try:
            self.os_interaction.start_process(command)
        except Exception, e:
            logger.error(e)

    def inform_tray_app_new(self, share, tray_port, start_tray=True):
        url = 'http://127.0.0.1:%s/newShare' % tray_port
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req).read()
            if response.strip() != 'ok':
                logger.error(response)
            else:
                self.tray_app_started = True
        except Exception, detail:
            if not start_tray:
                logger.error( "An error has occured while informing the tray: %s" % detail )
            else:
                self.start_tray_application()
                sleep(3)
                self.inform_tray_app_new(share, tray_port, start_tray=False)


    def inform_tray_app_error(self, share, tray_port):
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

    def inform_tray_app_success(self, share, tray_port):
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

    def copy_share_to_clipboard(self, share):
        self.os_interaction.copy_to_clipboard(share.get_link().strip())

    def get_restart_command(self, session):
        command = []
        if sys.argv[0][-3:] == '.py':
            command.extend(['python'])
        command.extend(sys.argv)
        if os.path.exists('env/bin/python'):
            command[0] = 'env/bin/python'

        #if not '--tray-port' in command:
        #    command.extend(['--tray-port', '%s' % tray_port] )
        if not '--request-port' in command:
            command.extend(['--request-port', '%s' % session.server_port])
        if not '--local-port' in command:
            command.extend(['--local-port', '%s' % session.local_port])
        if session.server_session_token != '' and not '--request-token' in command:
            command.extend(['--request-token', session.server_session_token ])
        if not '--hide-message' in command:
            command.extend(['--hide-message'])
        if not '--no-clipboard' in command:
            command.extend(['--no-clipboard'])
        if not '--no-tray' in command:
            command.extend(['--no-tray'])

        return command

    def add_default_arguments(self, parser, local_port_required=True):
        parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
        parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
        parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new share.')
        parser.add_argument('--no-tray', action="store_true", default=False, help='Do not start a tray app if none can be found.')
        parser.add_argument('--local-port', type=int, help='The port you want to openport.', required=local_port_required, default=-1)
        parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--no-gui', action='store_true', help='Start the app without a gui.')

    def start(self):
        logger.debug('client pid:%s' % os.getpid())
        import argparse
        from apps.openport_api import open_port
        from common.session import Session

        parser = argparse.ArgumentParser()
        self.add_default_arguments(parser)
        args = parser.parse_args()
        if args.no_gui:
            args.hide_message = True
            args.no_clipboard = True
        self.args = args

        def show_message_box(session):
            import wx
            wx.MessageBox('Your local port %s is now reachable on %s' % ( session.local_port, session.get_link()), 'Info',
                wx.OK | wx.ICON_INFORMATION)

        self.first_time = True

        def callback(ignore):
            if not self.first_time:
                return
            self.first_time = False

            session.restart_command = self.get_restart_command(session)
            if args.tray_port > 0:
                self.inform_tray_app_new(session, args.tray_port, start_tray=(not args.no_tray))

            session.error_observers.append(self.error_callback)
            session.success_observers.append(self.success_callback)

            if not args.no_clipboard:
                self.copy_share_to_clipboard(session)
            if not args.hide_message:
                show_message_box(session)

        session = Session()
        session.local_port = int(args.local_port)
        session.server_port = args.request_port
        session.server_session_token = args.request_token

#        app.MainLoop()

        def show_error(error_msg):
            import wx
            wx.MessageBox(error_msg, 'Error', wx.OK | wx.ICON_ERROR)

        open_port(session, callback, show_error)

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
