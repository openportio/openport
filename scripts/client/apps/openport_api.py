#!/usr/bin/env python

import sys
from apps.keyhandling import get_or_create_public_key
from services.logger_service import get_logger
import urllib
import urllib2
import json
from manager.globals import DEFAULT_SERVER
from apps.openport_app_version import VERSION

logger = get_logger('openport_api')

SERVER_SSH_PORT = 22
FALLBACK_SERVER_SSH_PORT = 443
SERVER_SSH_USER = 'open'


class PortForwardResponse():

    def __init__(self, dict):
        self.from_dict(dict)

    def from_dict(self, dict):
        self.server = dict['server_ip']
        self.remote_port = dict['server_port']
        self.message = dict['message']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        self.session_token = dict['session_token']
        self.http_forward_address = dict['http_forward_address']

        self.session_max_bytes = dict.get('session_max_bytes')
        self.open_port_for_ip_link = dict.get('open_port_for_ip_link')
        self.session_id = dict.get('session_id')
        self.session_end_time = dict.get('session_end_time')


def request_port(public_key, local_port=None, url='https://%s/api/v1/request-port' % DEFAULT_SERVER,
                 restart_session_token='',
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
            'client_version': VERSION,
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
        try:
            logger.debug('error: got response: %s' % response)
        except:
            pass
        print "An error has occurred while communicating the the openport servers. ", detail, detail.read()
        raise detail


def request_open_port(local_port, restart_session_token='', request_server_port=-1, error_callback=None,
                      http_forward=False, stop_callback=None, server=DEFAULT_SERVER, automatic_restart=False):

    public_key = get_or_create_public_key()

    logger.debug("requesting port forward - remote port: %s, restart session token: %s" % (request_server_port, restart_session_token))
    url = 'https://%s/api/v1/request-port' % server
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
            logger.info("Session is killed, stopping app!!!")
            sys.exit(9)
    logger.debug(dict)

    response = PortForwardResponse(dict)

    if request_server_port != -1 and request_server_port != response.remote_port:
        logger.error('Did not get requested server port (%s), but got %s' % (request_server_port, response.remote_port))

    return response




