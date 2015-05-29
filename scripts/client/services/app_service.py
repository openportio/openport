import urllib2
import os
from urllib2 import URLError, HTTPError

from common.session import Session
from services.logger_service import get_logger
from services import osinteraction

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
        else:
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
        if server:
            command.extend(['--server', server])
        if session.ip_link_protection is not None:
            command = osinteraction.set_variable('--ip-link-protection', session.ip_link_protection)

        command = self.set_manager_port(command)

        return command

    def start_openport_process_from_session(self, session, database=''):
        command = self.get_restart_command(session, database=database)
        logger.debug(command)
        session.restart_command = command
        p = osinteraction.getInstance().start_openport_process(session)
        osinteraction.getInstance().print_output_continuously_threaded(p, 'openport_app')
        return p

    def manager_is_running(self, manager_port):
        url = 'http://localhost:%s/ping' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=5).read()
            if response.strip() != 'pong':
                logger.debug('got response: %s' % response)
                raise Exception('Another application is running on port %s' % manager_port)
            else:
                return True
        except HTTPError:
            raise Exception('Another application is running on port %s' % manager_port)
        except URLError, detail:
            return False
        except Exception, detail:
            raise Exception('Another application is running on port %s' % manager_port)

    def check_username_in_config_file(self):
        if not osinteraction.is_windows():
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

