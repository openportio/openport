from manager.globals import Globals
from services import osinteraction
from common.share import Share
from common.session import Session
from services.logger_service import get_logger
import urllib2
from urllib2 import URLError, HTTPError
logger = get_logger(__name__)


def set_manager_port(command):
    os_interaction = osinteraction.getInstance()
    if Globals.Instance().manager_port_from_config_file:
        command = os_interaction.unset_variable(command, '--manager-port')
    else:
        command = os_interaction.set_variable(command, '--manager-port', Globals.Instance().manager_port)
    return command


def start_openport_process(port):
    session = Session()
    session.local_port = port
    start_openport_process_from_session(session)


def get_restart_command(session, database='', verbose=False, server=''):
    command = ['%s' % session.local_port]
    if session.http_forward:
        command.append('--http-forward')
    if session.active:
        command.append('--restart-on-reboot')
    if database:
        command.extend(['--database', database])
    if verbose:
        command.append('--verbose')
    if server:
        command.extend(['--server', server])

    command = set_manager_port(command)

    return command


def start_openport_process_from_session(session):
    command = get_restart_command(session)
    logger.debug(command)
    session.restart_command = command
    p = osinteraction.getInstance().start_openport_process(session)
    osinteraction.getInstance().print_output_continuously_threaded(p, 'openport_app')
    return p


def manager_is_running(manager_port):
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


