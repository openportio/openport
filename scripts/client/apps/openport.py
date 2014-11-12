import os
from time import sleep
from manager.globals import DEFAULT_SERVER

from apps import openport_api
from apps.portforwarding import PortForwardingService, PortForwardException
from apps.keyhandling import PUBLIC_KEY_FILE, PRIVATE_KEY_FILE
from services.logger_service import get_logger

logger = get_logger('openport')

SERVER_SSH_PORT = 22
FALLBACK_SERVER_SSH_PORT = 443
SERVER_SSH_USER = 'open'


class Openport(object):

    def __init__(self):
        self.port_forwarding_service = None
        self.restart_on_failure = True
        self.session = None
        self.automatic_restart = False
        self.repeat_message = True
        self.last_response = None

    def start_port_forward(self, session, callback=None, error_callback=None, server=DEFAULT_SERVER):

        self.restart_on_failure = True
        self.automatic_restart = False
        self.session = session

        while self.restart_on_failure:
            try:
                response = openport_api.request_open_port(
                    session.local_port,
                    request_server_port=session.server_port,
                    restart_session_token=session.server_session_token,
                    error_callback=error_callback,
                    stop_callback=session.notify_stop,
                    http_forward=session.http_forward,
                    server=server,
                    automatic_restart=self.automatic_restart
                )
                self.last_response = response

                if session.server_port != response.remote_port:
                    self.repeat_message = True

                session.server = response.server
                session.server_port = response.remote_port
                session.pid = os.getpid()
                session.account_id = response.account_id
                session.key_id = response.key_id
                session.server_session_token = response.session_token
                session.http_forward_address = response.http_forward_address

                if callback is not None:
                    import threading
                    thr = threading.Thread(target=callback, args=(session,))
                    thr.setDaemon(True)
                    thr.start()

                self.port_forwarding_service = PortForwardingService(
                    session.local_port,
                    response.remote_port,
                    response.server,
                    SERVER_SSH_PORT,
                    SERVER_SSH_USER,
                    PUBLIC_KEY_FILE,
                    PRIVATE_KEY_FILE,
                    success_callback=session.notify_success,
                    error_callback=session.notify_error,
                    fallback_server_ssh_port=FALLBACK_SERVER_SSH_PORT,
                    http_forward_address=session.http_forward_address,
                    start_callback=self.show_message
                )
                self.port_forwarding_service.start() #hangs
            except PortForwardException as e:
                logger.info('The port forwarding has stopped: %s' % e)
            except SystemExit as e:
                raise
            except Exception as e:
                logger.error(e)
                sleep(10)
            finally:
                self.automatic_restart = True

    def show_message(self):
        if not self.session:
            logger.error('session is None???')
        elif not self.automatic_restart or self.repeat_message:
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

    def stop_port_forward(self):
        self.restart_on_failure = False
        if self.port_forwarding_service:
            self.port_forwarding_service.stop()

    def stop(self):
        self.stop_port_forward()