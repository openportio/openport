import os
import requests

from openport.common.session import Session, DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS
from openport.services.logger_service import get_logger
from openport.services import osinteraction
from openport.common.config import DEFAULT_SERVER

logger = get_logger(__name__)

USER_CONFIG_FILE = '/etc/openport/users.conf'


class AppService(object):
    def __init__(self, openport_app_config):
        self.config = openport_app_config
        self.os_interaction = osinteraction.getInstance()

    def set_manager_port(self, command):
        os_interaction = osinteraction.getInstance()
        if self.config.manager_port_from_config_file:
            command = os_interaction.unset_variable(command, '--listener-port')
        elif self.config.manager_port > 0:
            command = os_interaction.set_variable(command, '--listener-port', self.config.manager_port)
        return command

    def start_openport_process(self, port):
        session = Session()
        session.local_port = port
        self.start_openport_process_from_session(session)

    def get_restart_command(self, session, database='', verbose=False, server=''):
        command = ['%s' % session.local_port]
        if session.http_forward:
            command.append('--http-forward')
        command.append('--restart-on-reboot')
        if database:
            command.extend(['--database', database])
        if verbose:
            command.append('--verbose')
        if server and server != DEFAULT_SERVER:
            command.extend(['--server', server])
        if session.ip_link_protection is not None:
            command = self.os_interaction.set_variable(command, '--ip-link-protection', session.ip_link_protection)
        if session.forward_tunnel:
            command = self.os_interaction.set_variable(command, '--forward-tunnel')
            command = self.os_interaction.set_variable(command, '--remote-port', str(session.server_port))
        if session.keep_alive_interval_seconds != DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS:
            command = self.os_interaction.set_variable(command, '--keep-alive', str(session.keep_alive_interval_seconds))

        command = self.set_manager_port(command)

        return command

    def start_openport_process_from_session(self, session, database=''):
        command = self.get_restart_command(session, database=database)
        logger.debug(command)
        session.restart_command = command

        os_interaction = osinteraction.getInstance()
        full_command = os_interaction.get_full_restart_command(session)
        p = os_interaction.start_process(full_command)
        return p

    def manager_is_running(self, manager_port):
        url = 'http://localhost:%s/ping' % manager_port
        logger.debug('sending get request ' + url)
        try:
            r = requests.get(url, timeout=5)
            if r.text.strip() != 'pong':
                logger.debug('got response: %s' % r.text)
                raise Exception('Another application is running on port %s' % manager_port)
            else:
                return True
        except requests.HTTPError:
            raise Exception('Another application is running on port %s' % manager_port)
        except requests.ConnectionError as detail:
            return False
        except Exception as detail:
            raise Exception('Another application is running on port %s' % manager_port)

    def check_username_in_config_file(self):
        if not osinteraction.is_windows():
            if osinteraction.getInstance().user_is_root():
                return
            if not os.path.exists(USER_CONFIG_FILE):
                logger.warning('The file %s does not exist. Your sessions will not be automatically restarted '
                               'on reboot. You can restart your session with "openport --restart-shares"'
                               % USER_CONFIG_FILE)
                return
            username = self.os_interaction.get_username()
            with open(USER_CONFIG_FILE, 'r') as f:
                lines = [l.strip() for l in f.readlines()]
                if username not in lines:
                    logger.warning('Your username (%s) is not in %s. Your sessions will not be automatically restarted '
                                   'on reboot. You can restart your session with "openport --restart-shares"' %
                                   (username, USER_CONFIG_FILE))
                    return

