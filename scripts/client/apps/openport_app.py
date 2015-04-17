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
from services.app_service import get_restart_command, set_manager_port
from manager import dbhandler
from apps.openport import Openport
from apps import openport_app_version
from app_tcp_server import start_server_thread, send_exit, send_ping
from keyhandling import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, ensure_keys_exist

from manager.globals import DEFAULT_SERVER

logger = get_logger('openport_app')
from time import sleep


class OpenportApp(object):

    def __init__(self):
        Globals.Instance().app = self
        self.manager_app_started = False
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals.Instance()
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

    def handleSigTERM(self, signum, frame=-1):
        logger.debug('got signal %s' % signum)
        if self.session:
            self.session.notify_stop()
            sleep(1)
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
        group.add_argument('--list', '-l', action='store_true', help="List shares and exit")
        group.add_argument('--kill', '-k', action='store', type=int, help="Stop a share", default=0)
        group.add_argument('--kill-all', '-K', action='store_true', help="Stop all shares")
        group.add_argument('--restart-shares', action='store_true', help='Restart all active shares.')

        parser.add_argument('--listener-port', type=int, default=-1, help=argparse.SUPPRESS)
        parser.add_argument('--database', type=str, default='', help=argparse.SUPPRESS)
        parser.add_argument('--request-port', type=int, default=-1, help='Request the server port for the share. Do not forget to pass the token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
        parser.add_argument('--http-forward', action='store_true', help='Request an http forward, so you can connect to port 80 on the server.')
        parser.add_argument('--server', default=DEFAULT_SERVER, help=argparse.SUPPRESS)
        parser.add_argument('--restart-on-reboot', '-R', action='store_true', help='Restart this share when the manager app is started.')
        parser.add_argument('--config-file', action='store', type=str, default='', help=argparse.SUPPRESS)
        parser.add_argument('--forward-tunnel', action='store_true', help='Forward connections from your local port to the server port.')
        parser.add_argument('--remote-port', type=int, help='The server port you want to forward to'
                                                           ' (only use in combination with --forward-tunnel).', default=-1)

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
        Globals.Instance().tcp_listeners.add(manager_port)

    def parse_args(self):
        parser = argparse.ArgumentParser()
        self.add_default_arguments(parser)
        self.args = parser.parse_args()


    def print_shares(self):
        shares = self.db_handler.get_shares()
        logger.debug('listing shares - amount: %s' % len(list(shares)))
        for share in shares:
            print self.get_share_line(share)

    def get_share_line(self, share):
               #"pid: %s - " % share.pid + \
        share_line = "localport: %s - " % share.local_port + \
                     "remote port: %s - " % share.server_port + \
                     "running: %s - " % self.os_interaction.pid_is_openport_process(share.pid) + \
                     "restart on reboot: %s" % bool(share.restart_command)
        if Globals.Instance().verbose:
            share_line += ' - pid: %s' % share.pid + \
                          ' - id: %s' % share.id
        return share_line

    def kill(self, local_port):
        shares = self.db_handler.get_share_by_local_port(local_port)
        if len(shares) > 0:
            share = shares[0]
            self.kill_share(share)
        self.print_shares()

    def kill_share(self, share):
        if send_ping(share):
            logger.debug('Share %s is running, will kill it.' % share.local_port)
            send_exit(share)

    def kill_all(self):
        shares = self.db_handler.get_shares()
        for share in shares:
            self.kill_share(share)

    def restart_sharing(self):
        shares = self.db_handler.get_shares_to_restart()
        logger.debug('restarting shares - amount: %s' % len(list(shares)))
        for share in shares:
            if not self.os_interaction.pid_is_openport_process(share.pid):
                try:
                    logger.debug('restarting share: %s' % share.restart_command)
                    share.restart_command = set_manager_port(share.restart_command)

                    p = self.os_interaction.start_openport_process(share)
                    self.os_interaction.print_output_continuously_threaded(p, 'share port: %s - ' % share.local_port)
                    sleep(1)
                    if p.poll() is not None:
                        logger.debug('could not start openport process: StdOut:%s\nStdErr:%s' %
                                     self.os_interaction.non_block_read(p))
                    else:
                        logger.debug('started app with pid %s : %s' % (p.pid, share.restart_command))
                        sleep(1)

                except Exception, e:
                    logger.exception(e)
            else:
                logger.debug('not starting %s: still running' % share.local_port)
        users_file = '/etc/openport/users.conf'
        if not osinteraction.is_windows() and self.os_interaction.user_is_root() and os.path.exists(users_file):
            with open(users_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if not line.strip() or line.strip()[0] == '#':
                        continue
                    username = line.strip().split()[0]
                    openport_command = self.os_interaction.get_openport_exec()
                    command = ['sudo', '-u', username, '-H'] + openport_command + ['--restart-shares']
                    logger.debug('restart command: %s' % command)
                    self.os_interaction.spawn_daemon(command)

    def start(self):
        # print 'sys.argv: %s' % sys.argv
        self.init_app(self.args)

        key_registration_service.register_key(self.args, self.args.server)

        if self.args.database != '':
            dbhandler.db_location = self.args.database
        self.db_handler = dbhandler.getInstance()


        Globals.Instance().manager_port = self.args.listener_port
        Globals.Instance().openport_address = self.args.server

        if self.args.config_file:
            Globals.Instance().config = self.args.config_file

        logger.debug('db location: ' + dbhandler.db_location)

        if self.args.list:
            self.print_shares()
            sys.exit()

        if self.args.kill:
            self.kill(self.args.kill)
            sys.exit()

        if self.args.kill_all:
            self.kill_all()
            sys.exit()

        if self.args.restart_shares:
            self.restart_sharing()
            sys.exit()

        session = Session()
        session.local_port = int(self.args.local_port)
        session.server_port = self.args.request_port
        session.server_session_token = self.args.request_token
        session.forward_tunnel = self.args.forward_tunnel
        if session.forward_tunnel:
            session.server_port = self.args.remote_port

        db_share = self.db_handler.get_share_by_local_port(session.local_port)
        if db_share:
            if self.os_interaction.pid_is_openport_process(db_share[0].pid):
                logger.info('Port forward already running for port %s' % self.args.local_port)
                sys.exit(6)

            if not session.server_session_token:
                logger.debug("retrieved db share session token: %s" % db_share[0].server_session_token)
                session.server_session_token = db_share[0].server_session_token
                session.server_port = db_share[0].server_port
        else:
            logger.debug('No db share session could be found.')
        session.http_forward = self.args.http_forward

        session.restart_command = get_restart_command(session,
                                                      database=self.args.database,
                                                      verbose=self.args.verbose,
                                                      server=self.args.server,
                                                      )

        session.stop_observers.append(self.stop_callback)
        session.start_observers.append(self.save_share)
        session.error_observers.append(self.error_callback)
        session.success_observers.append(self.success_callback)

        ensure_keys_exist()
        session.private_key_file = PRIVATE_KEY_FILE
        session.public_key_file = PUBLIC_KEY_FILE

        self.session = session

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
