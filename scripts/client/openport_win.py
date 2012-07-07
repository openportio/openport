#!/usr/bin/env python

import sys
from sys import argv
import time
import wx
from keyhandling import get_or_create_public_key, PRIVATE_KEYFILE, PUBLIC_KEYFILE
from portforwarding import forward_port

from openport import request_port

SERVER_SSH_PORT = 22
SERVER_SSH_USER = 'open'

class PortForwardResponse():
    def __init__(self, server='', remote_port=-1, message='', account_id=-1, key_id=-1, session_id=-1):
        self.server = server
        self.remote_port = remote_port
        self.message = message
        self.account_id = account_id
        self.key_id = key_id
        self.session_id = session_id

    def __init__(self,dict):
        self.from_dict(dict)

    def from_dict(self, dict):
        self.server = dict['server_ip']
        self.remote_port = dict['server_port']
        self.message = dict['message']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        #self.session_id = dict['session_id']


def open_port(local_port, callback=None):

    public_key = get_or_create_public_key()
    dict = request_port( public_key )

    if 'error' in dict:
        wx.MessageBox('An error has occured:\n%s' %(dict['error']), 'Error', wx.OK | wx.ICON_ERROR)
        sys.exit(8)

    response = PortForwardResponse(dict)

    if callback is not None:
        import threading
        thr = threading.Thread(target=callback, args=(response,))
        thr.setDaemon(True)
        thr.start()
    while True:
        forward_port(local_port, response.remote_port, response.server, SERVER_SSH_PORT, SERVER_SSH_USER, PUBLIC_KEYFILE, PRIVATE_KEYFILE)
        time.sleep(60)

if __name__ == '__main__':
	port = int(argv[1])
	open_port(port)
