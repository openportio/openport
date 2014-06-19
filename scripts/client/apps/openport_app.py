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
from services import osinteraction
from services.logger_service import get_logger, set_log_level
from services.osinteraction import is_linux, OsInteraction
from manager.globals import Globals
from apps.openport_api import open_port
from common.session import Session
from services import key_registration_service

logger = get_logger('openport_app')


def quote_path(path):
    split = path.split(os.sep)
    #logger.debug( split )
    quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
    return os.sep.join(quoted)

class OpenportApp(object):

    def __init__(self):
        self.manager_app_started = False
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()
        self.args = UserDict()
        self.session = None
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

    def handleSigTERM(self, signum, frame):
        logger.debug('got signal %s' % signum)
        if self.manager_app_started and self.session:
            self.inform_manager_app_stop(self.session, self.args.manager_port)
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

        if self.os_interaction.is_compiled():
            command = []
            path = quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openportmanager.exe'))
            if not os.path.exists(path):
                path = quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openportmanager'))
            command.extend([path])
        else:
            command = self.os_interaction.get_python_exec()
            command.extend(['-m', 'manager.openportmanager'])
        command = OsInteraction.set_variable(command, '--manager-port', self.args.manager_port)
        if self.args.manager_database:
            command = OsInteraction.set_variable(command, '--database', self.args.manager_database)
        if self.args.server:
            command = OsInteraction.set_variable(command, '--server', self.args.server)
        logger.debug('starting manager: %s' % command)
    #    output = self.os_interaction.run_command_silent(command) #hangs
    #    logger.debug('manager stopped: %s ' % output)

        def start_manager():
            try:
                output = self.os_interaction.run_command_silent(command) #hangs
                logger.debug('manager stopped: %s ' % output)
            except Exception, e:
                logger.error(e)
        self.os_interaction.spawnDaemon(start_manager)

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
                sleep(5)
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
                logger.error( response )
            if response.strip() == 'unknown':
                logger.critical('this share is no longer known by the manager, exiting')
                sys.exit(1)
        except urllib2.HTTPError, e:
            logger.error('error informing manager of success: ' + e)
            if e.getcode() == 500:
                logger.error('error detail: ' + e.read())
            sys.exit(1)
        except urllib2.URLError, error:
            logger.exception('Could not communicate with the manager app to inform of a success.')
            tb = traceback.format_exc()
            logger.debug('%s\n%s' % (error, tb))
            sys.exit(1)
        except Exception, detail:
            logger.exception(detail)

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

        #if not '--manager-port' in command:
        #    command.extend(['--manager-port', '%s' % manager_port] )
        command = OsInteraction.set_variable(command, '--request-port', session.server_port)
        command = OsInteraction.set_variable(command, '--local-port', session.local_port)
        if session.server_session_token != '':
            command = OsInteraction.set_variable(command, '--request-token', session.server_session_token)
        command = OsInteraction.set_variable(command, '--start-manager', False)
        command = OsInteraction.unset_variable(command, '--manager-database')
        command = OsInteraction.set_variable(command, '--manager-port', self.args.manager_port)

        return command

    def add_default_arguments(self, parser, local_port_required=True):

        group = parser.add_mutually_exclusive_group(required=local_port_required)
        group.add_argument('--local-port', type=int, help='The port you want to openport.', default=-1)
        group.add_argument('--register-key', default='', help='Use this to add your link your client to your account.')

        parser.add_argument('--manager-port', type=int, default=8001, help='Inform the manager app of the new share.')
        parser.add_argument('--start-manager', type=bool, default=True, help='Do not start a manager app if none can be found.')
        parser.add_argument('--manager-database', type=str, default='', help='The database the manager should use if launched from this app.')
        parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
        parser.add_argument('--http-forward', action='store_true', help='Request an http forward, so you can connect to port 80 on the server.')
        parser.add_argument('--server', default='www.openport.be', help=argparse.SUPPRESS)

    def init_app(self, args):
        logger.debug('client pid:%s' % os.getpid())
        if args.verbose:
            from logging import DEBUG
            set_log_level(DEBUG)

        if not args.start_manager:
            args.manager_port = -1

        self.globals.server = args.server

        self.args = args

    def start(self):
        parser = argparse.ArgumentParser()
        self.add_default_arguments(parser)
        self.args = parser.parse_args()

        key_registration_service.register_key(self.args, self.args.server)

        self.init_app(self.args)

        self.first_time = True

        def callback(ignore):
            if not self.first_time:
                return
            self.first_time = False

            session.restart_command = self.get_restart_command(session)
            if self.args.manager_port > 0:
                self.inform_manager_app_new(session, self.args.manager_port, start_manager=self.args.start_manager)

            session.error_observers.append(self.error_callback)
            session.success_observers.append(self.success_callback)

        session = Session()
        session.local_port = int(self.args.local_port)
        session.server_port = self.args.request_port
        session.server_session_token = self.args.request_token
        session.http_forward = self.args.http_forward

        #        app.MainLoop()

        def show_error(error_msg):
            print error_msg

        self.session = session

        open_port(session, callback, show_error, server=self.args.server)

    def error_callback(self, session):
        logger.debug('error_callback')
        if self.args.manager_port > 0 and self.manager_app_started:
            self.inform_manager_app_error(session, self.args.manager_port)

    def success_callback(self, session):
        logger.debug('success_callback')
        if self.args.manager_port > 0 and self.manager_app_started:
            self.inform_manager_app_success(session, self.args.manager_port)


if __name__ == '__main__':
    app = OpenportApp()

    app.start()
