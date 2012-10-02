#!/usr/bin/env python

import sys
import time
import wx
from sys import argv
from keyhandling import get_or_create_public_key, PRIVATE_KEY_FILE, PUBLIC_KEY_FILE
from portforwarding import forward_port
from loggers import get_logger

from openport import request_port

logger = get_logger('openport_win')

class PortForwardResponse():
    def __init__(self, server='', remote_port=-1, message='', account_id=-1, key_id=-1, session_id=-1, local_port=-1):
        self.server = server
        self.remote_port = remote_port
        self.message = message
        self.account_id = account_id
        self.key_id = key_id
        self.session_id = session_id
        self.local_port = local_port

    def __init__(self,dict):
        self.from_dict(dict)

    def from_dict(self, dict):
        self.server = dict['server_ip']
        self.remote_port = dict['server_port']
        self.message = dict['message']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        self.session_id = dict['session_id']


def open_port(local_port, restart_session_id = -1, request_server_port=-1):

    public_key = get_or_create_public_key()

    logger.debug("requesting port forward - remote port: %s, restart session id: %s" % (request_server_port, restart_session_id))
    dict = request_port( public_key, restart_session_id=restart_session_id, request_server_port=request_server_port )

    if 'error' in dict:
        wx.MessageBox('An error has occured:\n%s' %(dict['error']), 'Error', wx.OK | wx.ICON_ERROR)
        sys.exit(8)
    logger.debug(dict)

    response = PortForwardResponse(dict)

    if request_server_port != '' and request_server_port != response.remote_port:
        logger.error( 'Did not get requested server port (%s), but got %s' % (request_server_port, response.remote_port))
    response.local_port = local_port

    return response

if __name__ == '__main__':
	port = int(argv[1])
	open_port(port)
