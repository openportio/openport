import os
from time import sleep
from manager.globals import DEFAULT_SERVER

from apps import openport_api
from apps.portforwarding import PortForwardingService
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

    def start_port_forward(self, session, callback=None, error_callback=None, server=DEFAULT_SERVER):

        self.restart_on_failure = True
        automatic_restart = False

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
                    automatic_restart=automatic_restart
                )

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
                    http_forward_address=session.http_forward_address
                )
                self.port_forwarding_service.start() #hangs
            except SystemExit as e:
                raise
            except Exception as e:
                logger.error(e)
                sleep(10)
            finally:
                automatic_restart = True

    def stop_port_forward(self):
        self.restart_on_failure = False
        if self.port_forwarding_service:
            self.port_forwarding_service.stop()
