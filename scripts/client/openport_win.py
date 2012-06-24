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

def open_port(local_port, callback=None, extra_args={}):

    public_key = get_or_create_public_key()
    dict = request_port( public_key )

    if 'error' in dict:
        wx.MessageBox('An error has occured:\n%s' %(dict['error']), 'Error', wx.OK | wx.ICON_ERROR)
        sys.exit(8)

    server, remote_port, message, account_id, key_id = \
        dict['server_ip'], dict['server_port'], dict['message'], dict['account_id'], dict['key_id']

    if callback is not None:
        import threading
        thr = threading.Thread(target=callback, args=(server, remote_port, account_id, key_id, extra_args))
        thr.setDaemon(True)
        thr.start()
    while True:
        forward_port(local_port, remote_port, server, SERVER_SSH_PORT, SERVER_SSH_USER, PUBLIC_KEYFILE, PRIVATE_KEYFILE)
        time.sleep(60)

if __name__ == '__main__':
	port = int(argv[1])
	open_port(port)
