#!/usr/bin/env python

import sys
import os
import requests
import platform
from openport.services.logger_service import get_logger
from openport.common.config import DEFAULT_SERVER
from openport.apps.openport_app_version import VERSION
from openport.services import osinteraction

logger = get_logger('openport_api')


class SessionError(Exception):
    pass


class FatalSessionError(Exception):
    pass


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
        self.fallback_ssh_server_ip = dict.get('fallback_ssh_server_ip')
        self.fallback_ssh_server_port = dict.get('fallback_ssh_server_port')


def request_port(public_key, local_port=None, url='%s/api/v1/request-port' % DEFAULT_SERVER,
                 restart_session_token='',
                 request_server_port=-1, http_forward=False, automatic_restart=False,
                 forward_tunnel=False, ip_link_protection=None, client_version=VERSION,
                 proxies={}):
    """
    Requests a port on the server using the openPort protocol
    return a tuple with ( server_ip, server_port, message )
    """

    os_interaction = osinteraction.getInstance()
    r = None
    try:
        request_data = {
            'public_key': public_key,
            'request_port': request_server_port,
            'restart_session_token': restart_session_token,
            'http_forward': 'on' if http_forward else '',
            'automatic_restart': 'on' if automatic_restart else '',
            'local_port': local_port if local_port else '',
            'client_version': client_version,
            'forward_tunnel': 'on' if forward_tunnel else '',
            'platform': platform.platform(),
        }
        if ip_link_protection is not None:
            request_data['ip_link_protection'] = 'on' if ip_link_protection else ''

        logger.debug('sending request %s %s' % (url, request_data))

        verify = 'local' not in url and '192.168' not in url and not os.environ.get('NO_SSL_VERIFY')
        r = requests.post(url, data=request_data, verify=verify, proxies=proxies)
        if r.status_code == 200:
            # logger.debug(r.text)
            return r.json()
        if r.status_code == 500:
            return {'error': r.reason}
        return {'error': 'status code: {} text: {}'.format(r.status_code, r.text)}
    except requests.HTTPError as e:
        logger.error("An error has occurred while communicating with the openport servers. %s" % e)
        if r is not None:
            logger.debug('error: got response: %s' % r.text)
            try:
                error_page_file_path = os_interaction.get_app_data_path('error.html')
                with open(error_page_file_path, 'w') as f:
                    f.write(r.text)
                    logger.debug('error is available here: %s' % error_page_file_path)
            except Exception as e2:
                logger.debug(e2)

        if e.response:
            logger.debug('error: got response: %s' % e.response.text)
            if e.response.status_code == 500:
                try:
                    error_page_file_path = os_interaction.get_app_data_path('error.html')
                    with open(error_page_file_path, 'w') as f:
                        logger.debug('error is available here: %s' % error_page_file_path)
                        f.write(e.response.text)
                except Exception as e:
                    logger.debug(e)
        raise
    except Exception as e:
        if r is not None:
            try:
                error_page_file_path = os_interaction.get_app_data_path('error.html')
                with open(error_page_file_path, 'w') as f:
                    f.write(r.text)
                    logger.debug('error is available here: %s' % error_page_file_path)
            except Exception as e:
                logger.debug(e)
        logger.error("An error has occurred while communicating with the openport servers. %s" % e)
        # logger.exception(e)
        raise e


def request_open_port(local_port, restart_session_token='', request_server_port=-1, error_callback=None,
                      http_forward=False, stop_callback=None, server=DEFAULT_SERVER, automatic_restart=False,
                      public_key=None, forward_tunnel=False, ip_link_protection=None, client_version=VERSION,
                      proxies={}):
    assert public_key is not None

    logger.debug("requesting port forward - remote port: %s, restart session token: %s" % (
    request_server_port, restart_session_token))
    url = '%s/api/v1/request-port' % server
    dict = request_port(local_port=local_port, public_key=public_key, url=url,
                        restart_session_token=restart_session_token,
                        request_server_port=request_server_port, http_forward=http_forward,
                        automatic_restart=automatic_restart,
                        forward_tunnel=forward_tunnel,
                        ip_link_protection=ip_link_protection,
                        client_version=client_version,
                        proxies=proxies,
                        )

    if 'error' in dict:
        if error_callback:
            error_callback(Exception('An error has occurred:\n%s' % (dict['error'])))
        if dict['error'] == 'Session killed':
            if stop_callback:
                stop_callback()
        if 'No session found' in dict['error']:
            if stop_callback:
                stop_callback()
            logger.info(dict['error'])
        if dict.get('fatal_error', False):
            raise FatalSessionError(dict.get('error'))
        raise SessionError(dict['error'])

    logger.debug(dict)

    response = PortForwardResponse(dict)

    if request_server_port != -1 and request_server_port != response.remote_port:
        logger.error('Did not get requested server port (%s), but got %s' % (request_server_port, response.remote_port))

    return response
