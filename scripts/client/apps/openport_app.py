import sys
import urllib
import urllib2
from time import sleep
import signal
import getpass
import traceback

import os


sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))

from UserDict import UserDict
import argparse
import threading

from services import osinteraction
from services.logger_service import get_logger, set_log_level
from services.osinteraction import is_linux, OsInteraction
from manager.globals import Globals
from common.session import Session
from services import key_registration_service
from manager import openportmanager, dbhandler
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
            signal.signal(signal.SIGINT, self.handleSigTERM)
        except ValueError:
            pass
            # Do not handle the sigterm signal, otherwise the share will not be restored after reboot.
            #signal.signal(signal.SIGTERM, self.handleSigTERM)

        self.db_handler = None

    def handleSigTERM(self, signum, frame):
        logger.debug('got signal %s' % signum)
        if self.manager_app_started and self.session:
            self.inform_manager_app_stop(self.session, self.globals.manager_port)
        sys.exit(3)

    def inform_manager_app_stop(self, share, manager_port, start_manager=True):
        logger.debug('Informing manager we\'re stopping.')
        url = 'http://127.0.0.1:%s/stopShare' % manager_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=1).read()
            if response.strip() != 'ok':
                logger.error(response)
        except Exception, detail:
            logger.error("An error has occured while informing the manager: %s" % detail)

    def start_manager_application(self):
        if self.manager_app_started:
            return
        self.manager_app_started = True
        #logger.debug('setting cwd to: %s' % os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

        command = self.os_interaction.get_openport_exec()
        command.append('manager')
        if not self.globals.manager_port_from_config_file:
            command = OsInteraction.set_variable(command, '--manager-port', self.globals.manager_port)
        if self.args.database:
            command = OsInteraction.set_variable(command, '--database', self.args.database)
        if self.args.server and not self.args.server == DEFAULT_SERVER:
            command = OsInteraction.set_variable(command, '--server', self.args.server)
        logger.debug('starting manager: %s' % command)
        self.os_interaction.spawn_daemon(command)
        logger.debug("manager started")

    def check_manager_is_running(self, manager_port):
        url = 'http://127.0.0.1:%s/ping' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=5).read()
            logger.debug('check_manager_is_running response: %s' % response)
            if response.strip() != 'pong':
                return False
            else:
                self.manager_app_started = True
                return True
        except Exception:
            return False

    def inform_manager_app_new(self, share, manager_port, start_manager=True):
        url = 'http://127.0.0.1:%s/newShare' % manager_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=5).read()
            if response.strip() != 'ok':
                logger.error(response)
            else:
                self.manager_app_started = True
        except Exception, detail:
            logger.debug('Error occurred while informing the manager, starting the manager: %s' % start_manager)
            if not start_manager:
                tb = traceback.format_exc()
                logger.exception('Could not communicate with the manager app to inform of a new share.')
                logger.debug('%s\n%s'%(detail, tb))
                if type(detail) is urllib2.HTTPError and detail.getcode() == 500:
                    logger.error('error detail: ' + detail.read())
            else:
                self.start_manager_application()
                i = 0
                manager_is_running = self.check_manager_is_running(manager_port)
                while i < 30 and not manager_is_running:
                    sleep(1)
                    manager_is_running = self.check_manager_is_running(manager_port)
                if not manager_is_running:
                    logger.error('Could not start manager... Continuing...')
                else:
                    self.inform_manager_app_new(share, manager_port, start_manager=False)

    def inform_manager_app_error(self, share, manager_port):
        url = 'http://127.0.0.1:%s/errorShare' % manager_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=5).read()
            if response.strip() != 'ok':
                logger.error( response )
            if response.strip() == 'unknown':
                logger.critical('this share is no longer known by the manager, exiting')
                sys.exit(1)
        except urllib2.HTTPError, e:
            logger.error('error informing manager of error: ' + e)
            if e.getcode() == 500:
                logger.error('error detail: ' + e.read())
            sys.exit(1)
        except urllib2.URLError, error:
            logger.exception('Could not communicate with the manager app to inform of an error.')
            tb = traceback.format_exc()
            logger.debug('%s\n%s' % (error, tb))
            sys.exit(1)
        except Exception, detail:
            logger.exception(detail)

    def inform_manager_app_success(self, share, manager_port):
        url = 'http://127.0.0.1:%s/successShare' % manager_port
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=5).read()
            if response.strip() != 'ok':
                logger.error(response)
            if response.strip() == 'unknown':
                logger.critical('this share is no longer known by the manager, exiting')
                sys.exit(1)
        except urllib2.HTTPError, e:
            logger.error('error informing manager of success: %s ' % e)
            if e.getcode() == 500:
                logger.error('error detail: ' + e.read())
        except urllib2.URLError, error:
            logger.exception('Could not communicate with the manager app to inform of a success.')
            tb = traceback.format_exc()
            logger.debug('%s\n%s' % (error, tb))
        except Exception, detail:
            logger.exception('default exception')
            logger.exception(detail)

    def save_share(self, share):
        self.db_handler.add_share(share)

    def get_restart_command(self, session):
        command = []
        if not self.args.restart_on_reboot:
            return ''

        # Drop the openport part (for security reasons).
        command.extend(sys.argv[1:])

        #if not '--manager-port' in command:
        #    command.extend(['--manager-port', '%s' % manager_port] )
        command = OsInteraction.set_variable(command, '--request-port', session.server_port)
        if session.server_session_token != '':
            command = OsInteraction.set_variable(command, '--request-token', session.server_session_token)
        command = OsInteraction.set_variable(command, '--start-manager', False)
        command = OsInteraction.set_variable(command, '--manager-port', self.globals.manager_port)

        return command

    def add_default_arguments(self, parser, local_port_required=True):

        group = parser.add_mutually_exclusive_group(required=local_port_required)
        group.add_argument('--local-port', type=int, help='The port you want to openport.', default=-1)
        group.add_argument('--register-key', default='', help='Use this to add your link your client to your account.')
        group.add_argument('port', nargs='?', type=int, help='The port you want to openport.', default=-1)
        # This is a hack to make the command to start the manager work.
        group.add_argument('manager', nargs='?', type=int, help='Start the manager for openport.', default=-1)
        group.add_argument('--version', '-V', action='version', help='Print the version number and exit.',
                           version=openport_app_version.VERSION)

        parser.add_argument('--manager-port', type=int, default=-1, help=argparse.SUPPRESS)
        parser.add_argument('--start-manager', type=bool, default=True, help='Start a manager app if none can be found.')
        parser.add_argument('--database', type=str, default='', help=argparse.SUPPRESS)
        parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
        parser.add_argument('--http-forward', action='store_true', help='Request an http forward, so you can connect to port 80 on the server.')
        parser.add_argument('--server', default=DEFAULT_SERVER, help=argparse.SUPPRESS)
        parser.add_argument('--restart-on-reboot', '-R', action='store_true', help='Restart this share when the manager app is started.')
        parser.add_argument('--no-manager', action='store_true', help='Do not contact the manager.')

    def init_app(self, args):
        if args.verbose:
            from logging import DEBUG
            set_log_level(DEBUG)
        logger.debug('client pid:%s' % os.getpid())

        self.globals.server = args.server
        self.globals.manager_port = args.manager_port
        self.globals.contact_manager = not args.no_manager
        if args.port > 0:
            args.local_port = args.port

        self.args = args

        openportmanager.get_and_save_manager_port(manager_port_from_command_line=args.manager_port,  exit_on_fail=False)

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

        self.first_time = True

        def callback(ignore):
            if not self.first_time:
                return
            self.first_time = False

            session.restart_command = self.get_restart_command(session)

            if self.globals.contact_manager:
                inform_manager_app_new_thread = threading.Thread(target=self.inform_manager_app_new,
                                                                 args=(session, self.globals.manager_port,),
                                                                 kwargs={'start_manager': self.args.start_manager})
                inform_manager_app_new_thread.setDaemon(True)
                inform_manager_app_new_thread.start()

            self.save_share(session)

            session.error_observers.append(self.error_callback)
            session.success_observers.append(self.success_callback)
            session.stop_observers.append(self.stop_callback)

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

        #        app.MainLoop()

        def show_error(error_msg):
            print error_msg

        self.session = session

        self.openport.start_port_forward(session, callback, show_error, server=self.args.server)

    def error_callback(self, session, exception):
        logger.debug('error_callback')
        if self.globals.contact_manager and self.manager_app_started:
            self.inform_manager_app_error(session, self.globals.manager_port)

    def success_callback(self, session):
        logger.debug('success_callback')
        if self.globals.contact_manager and self.manager_app_started:
            self.inform_manager_app_success(session, self.globals.manager_port)

    def stop_callback(self, session):
        logger.debug('stop_callback')
        session.active = False
        self.save_share(session)
        if self.globals.contact_manager and self.manager_app_started:
            self.inform_manager_app_stop(session, self.globals.manager_port)

    def stop(self):
        self.openport.stop_port_forward()
        if self.session:
            self.session.notify_stop()


if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'manager':
        sys.argv.remove('manager')
        openportmanager.start_manager()
        sys.exit()

    app = OpenportApp()

    app.parse_args()
    app.start()
