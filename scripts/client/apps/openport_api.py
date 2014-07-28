#!/usr/bin/env python
import os

import sys
from apps.keyhandling import get_or_create_public_key, PUBLIC_KEY_FILE, PRIVATE_KEY_FILE
from apps.portforwarding import PortForwardingService
from services.logger_service import get_logger
import urllib
import urllib2
import json

logger = get_logger('openport_api')

SERVER_SSH_PORT = 22
FALLBACK_SERVER_SSH_PORT = 443
SERVER_SSH_USER = 'open'
from manager.globals import DEFAULT_SERVER


class PortForwardResponse():
    def __init__(self, server='', remote_port=-1, message='', account_id=-1, key_id=-1, local_port=-1, session_token='', http_forward_address=None):
        self.server = server
        self.remote_port = remote_port
        self.message = message
        self.account_id = account_id
        self.key_id = key_id
        self.session_token = session_token
        self.http_forward_address = http_forward_address

    def __init__(self,dict):
        self.from_dict(dict)

    def from_dict(self, dict):
        self.server = dict['server_ip']
        self.remote_port = dict['server_port']
        self.message = dict['message']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        self.session_token = dict['session_token']
        self.http_forward_address = dict['http_forward_address']


def request_port(public_key, local_port=None, url='http://%s/post' % DEFAULT_SERVER, restart_session_token='',
                 request_server_port=-1, http_forward=False, automatic_restart=False):
    """
    Requests a port on the server using the openPort protocol
    return a tuple with ( server_ip, server_port, message )
    """

    response = None
    try:
        data = urllib.urlencode({
            'public_key': public_key,
            'request_port': request_server_port,
            'restart_session_token': restart_session_token,
            'http_forward': 'on' if http_forward else '',
            'automatic_restart': 'on' if automatic_restart else '',
            'local_port': local_port if local_port else '',
            })
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req).read()
        dict = json.loads(response)
        return dict
    except urllib2.HTTPError, detail:
        logger.debug('error: got response: %s' % response)
        logger.error("An error has occurred while communicating the the openport servers. %s" % detail)
        if detail.getcode() == 500:
            logger.error(detail.read())
        raise
    except Exception, detail:
        logger.debug('error: got response: %s' % response)
        logger.error("An error has occurred while communicating the the openport servers. %s" % detail)
        raise


def request_open_port(local_port, restart_session_token='', request_server_port=-1, error_callback=None,
                      http_forward=False, stop_callback=None, server=DEFAULT_SERVER, automatic_restart=False):

    public_key = get_or_create_public_key()

    logger.debug("requesting port forward - remote port: %s, restart session token: %s" % (request_server_port, restart_session_token))
    url = 'http://%s/post' % server
    dict = request_port(local_port=local_port, public_key=public_key, url=url,
                        restart_session_token=restart_session_token,
                        request_server_port=request_server_port, http_forward=http_forward,
                        automatic_restart=automatic_restart)

    if 'error' in dict:
        if error_callback:
            error_callback('An error has occurred:\n%s' %(dict['error']))
        if dict['error'] == 'Session killed':
            if stop_callback:
                stop_callback()
            logger.debug("session killed, killing app!!!")
            sys.exit(9)
        sys.exit(8)
    logger.debug(dict)

    response = PortForwardResponse(dict)

    if request_server_port != -1 and request_server_port != response.remote_port:
        logger.error('Did not get requested server port (%s), but got %s' % (request_server_port, response.remote_port))

    return response


def open_port(session, callback=None, error_callback=None, server=DEFAULT_SERVER):

    from time import sleep
    automatic_restart = False

    while True:
        try:
            response = request_open_port(
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

            portForwardingService = PortForwardingService(
                session.local_port,
                response.remote_port,
                response.server,
                SERVER_SSH_PORT,
                SERVER_SSH_USER,
                PUBLIC_KEY_FILE,
                PRIVATE_KEY_FILE,
                success_callback=session.notify_success,
                error_callback=session.notify_error,
                fallback_server_ssh_port = FALLBACK_SERVER_SSH_PORT,
                http_forward_address = session.http_forward_address
            )
            portForwardingService.start() #hangs
        except SystemExit as e:
            raise
        except Exception as e:
            logger.error(e)
            sleep(10)
        finally:
            automatic_restart = True




