import sys
import signal
import os
from UserDict import UserDict
import argparse

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))

from services import osinteraction
from services.logger_service import get_logger, set_log_level
from manager.globals import Globals
from common.session import Session
from services import key_registration_service
from services.config_service import get_and_save_manager_port
from services.app_service import get_restart_command
from manager import dbhandler
from apps.openport import Openport
from apps import openport_app_version

from manager.globals import DEFAULT_SERVER

logger = get_logger('openport_app')


class OpenportApp(object):

    def __init__(self):
        self.manager_app_started = False
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()
        self.args = UserDict()
        self.session = None
        self.openport = Openport()
        if self.os_interaction.is_compiled():
            from common.tee import TeeStdErr, TeeStdOut
            TeeStdOut(self.os_interaction.get_app_data_path('openport_app.out.log'), 'a')
            TeeStdErr(self.os_interaction.get_app_data_path('openport_app.error.log'), 'a')
        try:
            if not osinteraction.is_windows():
                signal.signal(signal.SIGINT, self.handleSigTERM)
                signal.signal(signal.SIGTERM, self.handleSigTERM)
            else:
                # To be honest, I don't think this does anything...
                self.os_interaction.handle_signals(self.handleSigTERM)
        except ValueError:
            pass
            # Do not handle the sigterm signal, otherwise the share will not be restored after reboot.
            #signal.signal(signal.SIGTERM, self.handleSigTERM)

        self.db_handler = None
        Globals().app = self

    def handleSigTERM(self, signum, frame=-1):
        logger.debug('got signal %s' % signum)
        if self.session:
            self.session.notify_stop()
        os._exit(3)

    def save_share(self, share):
        self.db_handler.add_share(share)

    def add_default_arguments(self, parser, local_port_required=True):

        group = parser.add_mutually_exclusive_group(required=local_port_required)
        group.add_argument('--local-port', type=int, help='The port you want to openport.', default=-1)
        group.add_argument('--register-key', default='', help='Use this to add your link your client to your account.')
        group.add_argument('port', nargs='?', type=int, help='The port you want to openport.', default=-1)
        # This is a hack to make the command to start the manager work.
        group.add_argument('--version', '-V', action='version', help='Print the version number and exit.',
                           version=openport_app_version.VERSION)

        parser.add_argument('--listener-port', type=int, default=-1, help=argparse.SUPPRESS)
        parser.add_argument('--database', type=str, default='', help=argparse.SUPPRESS)
        parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
        parser.add_argument('--http-forward', action='store_true', help='Request an http forward, so you can connect to port 80 on the server.')
        parser.add_argument('--server', default=DEFAULT_SERVER, help=argparse.SUPPRESS)
        parser.add_argument('--restart-on-reboot', '-R', action='store_true', help='Restart this share when the manager app is started.')

    def init_app(self, args):
        if args.verbose:
            from logging import DEBUG
            set_log_level(DEBUG)
        logger.debug('client pid:%s' % os.getpid())

        self.globals.server = args.server
        if args.port > 0:
            args.local_port = args.port

        self.args = args

        manager_port = get_and_save_manager_port(exit_on_fail=False)
        Globals().tcp_listeners.add(manager_port)

    def parse_args(self):
        parser = argparse.ArgumentParser()
        self.add_default_arguments(parser)
        self.args = parser.parse_args()

    def start(self):
       # print 'sys.argv: %s' % sys.argv

        key_registration_service.register_key(self.args, self.args.server)

        if self.args.database != '':
            dbhandler.db_location = self.args.database
        self.db_handler = dbhandler.getInstance()

        self.init_app(self.args)

        session = Session()
        session.local_port = int(self.args.local_port)
        session.server_port = self.args.request_port
        session.server_session_token = self.args.request_token
        if not session.server_session_token:
            db_share = self.db_handler.get_share_by_local_port(session.local_port)
            if db_share:
                logger.debug("retrieved db share session token: %s" % db_share[0].server_session_token)
                session.server_session_token = db_share[0].server_session_token
                session.server_port = db_share[0].server_port
            else:
                logger.debug('No db share session could be found.')
        session.http_forward = self.args.http_forward

        session.restart_command = get_restart_command(session)

        session.stop_observers.append(self.stop_callback)
        session.start_observers.append(self.save_share)
        session.error_observers.append(self.error_callback)
        session.success_observers.append(self.success_callback)

        self.session = session

        from app_tcp_server import start_server_thread
        start_server_thread()
        self.openport.start_port_forward(session, server=self.args.server)

    def error_callback(self, session, exception):
        logger.debug('error_callback')
        logger.error('exception in session %s' % session.id)
        logger.exception(exception)

    def success_callback(self, session):
        logger.debug('success_callback')

    def stop_callback(self, session):
        logger.debug('stop_callback')
        session.active = False
        self.save_share(session)

    def stop(self):
        self.openport.stop_port_forward()

if __name__ == '__main__':
    app = OpenportApp()
    app.parse_args()
    app.start()
