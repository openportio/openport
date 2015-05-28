import os
from time import sleep

from common.config import DEFAULT_SERVER
from apps import openport_api
from apps.portforwarding import PortForwardingService, PortForwardException
from services.logger_service import get_logger


logger = get_logger('openport')

SERVER_SSH_PORT = 22
FALLBACK_SERVER_SSH_PORT = 443
FALLBACK_SSH_SERVER = 's.openport.io'
SERVER_SSH_USER = 'open'


class Openport(object):

    def __init__(self):
        self.port_forwarding_service = None
        self.restart_on_failure = True
        self.session = None
        self.automatic_restart = False
        self.repeat_message = True
        self.first_time_showing_message = True
        self.last_response = None

    def start_port_forward(self, session, server=DEFAULT_SERVER):

        self.restart_on_failure = True
        self.automatic_restart = False
        self.session = session
        if session.public_key_file:
            with open(session.public_key_file, 'r') as f:
                public_key = f.readline().strip()
        else:
            public_key = None

        while self.restart_on_failure:
            try:
                response = openport_api.request_open_port(
                    session.local_port,
                    request_server_port=session.server_port,
                    restart_session_token=session.server_session_token,
                    error_callback=session.notify_error,
                    stop_callback=session.notify_stop,
                    http_forward=session.http_forward,
                    server=server,
                    automatic_restart=self.automatic_restart,
                    public_key=public_key,
                    forward_tunnel=session.forward_tunnel,
                )
                self.last_response = response

                if session.server_port != response.remote_port:
                    self.repeat_message = True

                session.server = response.server
                if not session.forward_tunnel:
                    session.server_port = response.remote_port
                session.pid = os.getpid()
                session.account_id = response.account_id
                session.key_id = response.key_id
                session.server_session_token = response.session_token
                session.http_forward_address = response.http_forward_address
                session.open_port_for_ip_link = response.open_port_for_ip_link

                self.port_forwarding_service = PortForwardingService(
                    session.local_port,
                    session.server_port,
                    session.server,
                    SERVER_SSH_PORT,
                    SERVER_SSH_USER,
                    session.public_key_file,
                    session.private_key_file,
                    success_callback=self.session_success,
                    error_callback=session.notify_error,
                    fallback_server_ssh_port=FALLBACK_SERVER_SSH_PORT,
                    fallback_ssh_server=FALLBACK_SSH_SERVER,
                    http_forward_address=session.http_forward_address,
                    start_callback=session.notify_start,
                    forward_tunnel=session.forward_tunnel,
                )
                self.port_forwarding_service.start()  # hangs
            except PortForwardException as e:
                logger.info('The port forwarding has stopped: %s' % e)
            except SystemExit as e:
                raise
            except Exception as e:
                logger.exception(e)
                sleep(10)
            finally:
                self.automatic_restart = True

    def session_success(self):
        self.session.notify_success()
        self.show_message()

    def show_message(self):
        if not self.session:
            logger.error('session is None???')
        elif self.first_time_showing_message and (not self.automatic_restart or self.repeat_message):
            if self.session.http_forward_address is None or self.session.http_forward_address == '':
                logger.info('Now forwarding remote port %s:%d to localhost:%d .\n'
                            'You can keep track of your shares at https://openport.io/user .\n%s'
                            % (self.session.server, self.session.server_port, self.session.local_port,
                               self.last_response.message))
            else:
                logger.info('Now forwarding remote address %s to localhost:%d .\n'
                            'You can keep track of your shares at https://openport.io/user .\n%s'
                            % (self.session.http_forward_address, self.session.local_port,
                               self.last_response.message))
        self.repeat_message = False
        self.first_time_showing_message = False

    def stop_port_forward(self):
        self.restart_on_failure = False
        if self.port_forwarding_service:
            self.port_forwarding_service.stop()
        if self.session:
            self.session.notify_stop()

    def stop(self):
        self.stop_port_forward()

    def running(self):
        return not self.port_forwarding_service.stopped
