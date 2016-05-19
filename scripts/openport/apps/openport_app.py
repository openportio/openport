import sys
import signal
import os
from UserDict import UserDict
import argparse
import ast
import threading

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..', '..'))

from openport.services import osinteraction, dbhandler
from openport.services.logger_service import get_logger, set_log_level
from openport.common.config import OpenportAppConfig
from openport.common.session import Session
from openport.services import key_registration_service
from openport.services.config_service import ConfigService
from openport.services.app_service import AppService, USER_CONFIG_FILE
from openport.apps.openport_service import Openport
from openport.apps import openport_app_version
from app_tcp_server import AppTcpServer, send_exit, send_ping, is_running
from keyhandling import ensure_keys_exist, get_default_key_locations

from openport.common.config import DEFAULT_SERVER

logger = get_logger('openport_app')
from time import sleep


class OpenportApp(object):
    def __init__(self):
        self.config = OpenportAppConfig()
        self.config.app = self
        self.manager_app_started = False
        self.os_interaction = osinteraction.getInstance()
        self.args = UserDict()
        self.session = None
        self.openport = Openport()
        self.db_handler = None

        self.server = AppTcpServer('127.0.0.1', self.os_interaction.get_open_port(), self.config, self.db_handler)
        self.config_service = ConfigService(self.config)
        self.app_service = AppService(self.config)

        self.argument_parser = argparse.ArgumentParser()

        if self.os_interaction.is_compiled():
            from openport.common.tee import TeeStdErr, TeeStdOut
            TeeStdOut(self.os_interaction.get_app_data_path('openport_app.out.log'), 'a')
            TeeStdErr(self.os_interaction.get_app_data_path('openport_app.error.log'), 'a')
        try:
            if not osinteraction.is_windows():
                signal.signal(signal.SIGINT, self.handleSigTERM)
                signal.signal(signal.SIGTERM, self.handleSigTERM)
            else:
                # To be honest, I don't think this does anything...

                signal.signal(signal.SIGINT, self.handleSigTERM)
                signal.signal(signal.SIGTERM, self.handleSigTERM)

                # self.os_interaction.handle_signals(self.handleSigTERM)
        except ValueError:
            pass
            # Do not handle the sigterm signal, otherwise the share will not be restored after reboot.
            # signal.signal(signal.SIGTERM, self.handleSigTERM)

    def handleSigTERM(self, signum, frame=-1):
        logger.info('got signal %s, exiting...' % signum)
        try:
            if self.session:
                self.session.notify_stop()
            if self.openport:
                self.openport.stop()

            def kill_if_needed():
                sleep(5)
                logger.debug('App did not end cleanly.')
                os._exit(-1)

            t = threading.Thread(target=kill_if_needed())
            t.daemon = True
            t.start()

        except Exception as e:
            logger.exception(e)
            os._exit(3)

    def save_share(self, share):
        self.db_handler.add_share(share)

    def add_default_arguments(self, parser, group_required=True):

        group = parser.add_mutually_exclusive_group(required=group_required)
        group.add_argument('port', nargs='?', type=int, help='The local port you want to openport.', default=-1)
        group.add_argument('--version', '-V', action='version', help='Print the version and exit.',
                           version=openport_app_version.VERSION)
        parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
        group.add_argument('--local-port', type=int, help='The local port you want to openport.', default=-1)
        group.add_argument('--register-key', default='', metavar='SECRET_KEY', help='Use this to link your client to your account. Find the key at https://openport.io/user/keys')
        parser.add_argument('--name', default='',
                            help='The name for this client. (Use in combination with --register-key)')
        group.add_argument('--list', '-l', action='store_true', help="List shares and exit")
        group.add_argument('--kill', '-k', action='store', type=int, help="Stop a share.", metavar='LOCAL_PORT', default=0)
        group.add_argument('--kill-all', '-K', action='store_true', help="Stop all shares")
        group.add_argument('--restart-shares', action='store_true', help='Start all shares that were started with -R and are not running.')
        group.add_argument('--create-migrations', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument('--listener-port', type=int, default=-1, help=argparse.SUPPRESS)
        parser.add_argument('--database', type=str, default='', help=argparse.SUPPRESS)
        parser.add_argument('--request-port', type=int, default=-1, metavar='REMOTE_PORT',
                            help='Request the server port for the share. Do not forget to pass the token with --request-token.')
        parser.add_argument('--request-token', default='', help='The token needed to restart the share.')
        parser.add_argument('--http-forward', action='store_true',
                            help='Request an http forward, so you can connect to port 80 on the server.')
        parser.add_argument('--server', default=DEFAULT_SERVER, help=argparse.SUPPRESS)
        parser.add_argument('--restart-on-reboot', '-R', action='store_true',
                            help='Restart this share when --restart-shares is called (on boot for example).')
        parser.add_argument('--config-file', action='store', type=str, default='', help=argparse.SUPPRESS)
        parser.add_argument('--forward-tunnel', action='store_true',
                            help='Forward connections from your local port to the server port. Use this to connect two tunnels.')
        parser.add_argument('--remote-port', type=int, help='The server port you want to forward to'
                                                            ' (use in combination with --forward-tunnel).',
                            default=-1)
        parser.add_argument('--ip-link-protection', type=ast.literal_eval,
                            help='Set to True or False to set if you want users to click a secret link before they can '
                                 'access this port. This overwrites the standard setting in your profile for this '
                                 'session.', default=None, choices=[True, False])

        parser.add_argument('--daemonize', '-d', action='store_true', help='Start the app in the background.')

    def init_app(self, args):
        if args.verbose:
            import logging
            set_log_level(logging.DEBUG)
            logging.getLogger('sqlalchemy').setLevel(logging.WARN)
            self.config.verbose = True
        logger.debug('client pid:%s' % os.getpid())

        self.config.server = args.server
        if args.port > 0:
            args.local_port = args.port

        self.args = args

        manager_port = self.config_service.get_and_save_manager_port(exit_on_fail=False)
        self.config.tcp_listeners.add(manager_port)

    def parse_args(self):
        group_required = not '--forward-tunnel' in sys.argv

        self.add_default_arguments(self.argument_parser, group_required)
        self.args = self.argument_parser.parse_args()

    def print_shares(self):
        shares = self.db_handler.get_active_shares()
        shares.extend(self.db_handler.get_shares_to_restart())
        shares = {x.id: x for x in shares}.values()

        logger.debug('listing shares - amount: %s' % len(list(shares)))
        for share in shares:
            print self.get_share_line(share)

    def get_share_line(self, share):
        # "pid: %s - " % share.pid + \
        share_line = "localport: %s - " % share.local_port + \
                     "remote server: %s - " % share.server + \
                     "remote port: %s - " % share.server_port
        if share.open_port_for_ip_link:
            share_line += "open-for-ip-link: %s - " % share.open_port_for_ip_link
        share_line += "running: %s - " % is_running(share) + \
                      "restart on reboot: %s" % bool(share.restart_command)
        if self.config.verbose:
            share_line += ' - pid: %s' % share.pid + \
                          ' - id: %s' % share.id + \
                          ' - token: %s' % share.server_session_token
        return share_line

    def kill(self, local_port):
        share = self.db_handler.get_share_by_local_port(local_port)
        if share:
            self.kill_share(share)
        else:
            logger.info('No active session found for local port %s' % local_port)
        self.print_shares()

    def kill_share(self, share):
        if send_ping(share, print_error=False):
            logger.debug('Share %s is running, will kill it.' % share.local_port)
            send_exit(share)
        else:
            share.active = False
            share.restart_command = ''
            self.db_handler.add_share(share)
            self.server.inform_stop(share)

        logger.debug('killed share %s for port %s' % (share.id, share.local_port))

    def kill_all(self):
        shares = self.db_handler.get_active_shares()
        shares.extend(self.db_handler.get_shares_to_restart())

        shares = {x.id: x for x in shares}.values()
        for share in shares:
            self.kill_share(share)

    def restart_sharing(self):
        shares = self.db_handler.get_shares_to_restart()
        logger.debug('restarting shares - amount: %s' % len(list(shares)))
        for share in shares:
            if not is_running(share):
                try:
                    logger.info('restarting share: %s' % ' '.join(share.restart_command))
                    share.restart_command = self.app_service.set_manager_port(share.restart_command)

                    p = self.os_interaction.start_openport_process(share)
                    logger.debug('process started with pid %s' % p.pid)
                    # self.os_interaction.print_output_continuously_threaded(p, 'share port: %s - ' % share.local_port)
                    sleep(1)
                    if p.poll() is not None:
                        all_output = self.os_interaction.get_all_output(p)
                        logger.debug('could not start openport process for port %s: StdOut:%s\nStdErr:%s' %
                                     (share.local_port, all_output[0], all_output[1]))
                    else:
                        logger.debug('started app with pid %s : %s' % (p.pid, share.restart_command))
                        sleep(1)

                except Exception, e:
                    logger.exception(e)
            else:
                logger.debug('not starting %s: still running' % share.local_port)

        if not osinteraction.is_windows() and self.os_interaction.user_is_root() and os.path.exists(USER_CONFIG_FILE):
            with open(USER_CONFIG_FILE, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if not line.strip() or line.strip()[0] == '#':
                        continue
                    username = line.strip().split()[0]
                    if username == 'root':
                        continue
                    openport_command = self.os_interaction.get_openport_exec()
                    command = ['sudo', '-u', username, '-H'] + openport_command + ['--restart-shares']
                    logger.debug('restart command: %s' % command)
                    self.os_interaction.spawn_daemon(command)

    def start(self):
        # print 'sys.argv: %s' % sys.argv
        self.init_app(self.args)

        if self.args.daemonize:
            args = self.os_interaction.get_openport_exec()
            args.extend(sys.argv[1:])
            args = self.os_interaction.unset_variable(args, '--daemonize')
            args = self.os_interaction.unset_variable(args, '-d')
            self.os_interaction.spawn_daemon(args)
            logger.info('App started in background.')
            logger.debug(args)
            sys.exit(0)

        key_registration_service.register_key(self.args, self.args.server)

        self.db_handler = dbhandler.DBHandler(self.args.database)
        self.server.db_handler = self.db_handler

        self.config.manager_port = self.args.listener_port
        self.config.openport_address = self.args.server

        if self.args.config_file:
            self.config.config = self.args.config_file

        logger.debug('db location: ' + self.db_handler.db_location)

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
            logger.debug('exiting')
            sys.exit()

        if self.args.create_migrations:
            from openport.services import migration_service
            migration_service.create_migrations(self.db_handler.db_location)
            sys.exit()

        session = Session()
        session.local_port = int(self.args.local_port)
        session.server_port = self.args.request_port
        session.server_session_token = self.args.request_token
        session.forward_tunnel = self.args.forward_tunnel
        session.active = False  # Will be set active in start_callback.

        if session.forward_tunnel:
            session.server_port = self.args.remote_port
            if self.args.local_port < 0:
                session.local_port = self.os_interaction.get_open_port()

        else:
            db_share = self.db_handler.get_share_by_local_port(session.local_port, filter_active=False)
            if db_share:
                logger.debug('previous share found in database')
                if is_running(db_share):
                    logger.info('Port forward already running for port %s' % self.args.local_port)
                    sys.exit(6)

                if db_share.restart_command and not self.args.restart_on_reboot:
                    logger.warn(
                        'Port forward for port %s that would be restarted on reboot will not be restarted anymore.'
                        % self.args.local_port)

                if not session.server_session_token:
                    logger.debug("retrieved db share session token: %s" % db_share.server_session_token)
                    session.server_session_token = db_share.server_session_token
                    session.server_port = db_share.server_port
            else:
                logger.debug('No db share session could be found.')
            session.http_forward = self.args.http_forward

        if self.args.restart_on_reboot:
            session.restart_command = self.app_service.get_restart_command(session,
                                                                           database=self.args.database,
                                                                           verbose=self.args.verbose,
                                                                           server=self.args.server,
                                                                           )
            self.app_service.check_username_in_config_file()

        session.ip_link_protection = self.args.ip_link_protection

        session.stop_observers.append(self.stop_callback)
        session.start_observers.append(self.save_share)
        session.error_observers.append(self.error_callback)
        session.success_observers.append(self.success_callback)

        session.app_management_port = self.server.get_port()
        session.start_observers.append(self.server.inform_start)
        session.success_observers.append(self.server.inform_success)
        session.error_observers.append(self.server.inform_failure)
        session.stop_observers.append(self.server.inform_stop)

        ensure_keys_exist(*get_default_key_locations())

        self.session = session

        self.server.run_threaded()
        session.active = True
        self.save_share(session)
        self.openport.start_port_forward(session, server=self.args.server)

    def error_callback(self, session, exception):
        logger.debug('error_callback')
        logger.debug('exception in session %s' % session.id)
        # logger.exception(exception)

    def success_callback(self, session):
        logger.debug('success_callback')

    def stop_callback(self, session):
        logger.debug('stop_callback')
        session.active = False
        self.save_share(session)

    def stop(self):
        if self.openport:
            self.openport.stop_port_forward()
        if self.server:
            self.server.stop()


if __name__ == '__main__':
    app = OpenportApp()
    app.parse_args()
    app.start()
