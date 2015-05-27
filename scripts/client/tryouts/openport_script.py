#!/usr/bin/python
import warnings

warnings.warn("deprecated", DeprecationWarning)
from common.config import DEFAULT_SERVER


import os
from sys import argv
import subprocess
import signal
import time
import sys

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print 'You need python 2.6 or simplejson to run this application.'
        sys.exit(1)

def request_port(public_key, local_port=None, url='http://%s/post' % DEFAULT_SERVER, restart_session_token='',
                 request_server_port=-1, http_forward=False, automatic_restart=False):
    """
    Requests a port on the server using the openPort protocol
    return a tuple with ( server_ip, server_port, message )
    """
    import urllib, urllib2

    try:
        data = urllib.urlencode({
            'public_key': public_key,
            'request_port': request_server_port,
            'restart_session_token': restart_session_token,
            'http_forward': 'on' if http_forward else '',
            'automatic_restart': 'on' if automatic_restart else '',
            'local_port': local_port,
            })
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req).read()
        dict = json.loads(response)
        return dict
    except Exception, detail:
        print "An error has occurred while communicating the the openport servers. ", detail, detail.read()
        raise detail


def handleSigTERM(signum, frame):
    """
    This kills the ssh process when you terminate the application.
    """
    global s
    print 'killing process %s' % s.pid
    try:
        os.kill(s.pid, signal.SIGKILL)
    except OSError:
        pass
    exit(3)

def getPublicKey():
    """
    Gets content of the public key file.
    """
    key_file = os.path.join(os.path.expanduser('~'), '.ssh', 'id_rsa.pub')
    f = open(key_file, 'r')
    key = f.readline()
    if key == '':
        print 'could not read key: %s' % key_file
        exit(4)
    return key

def startSession(server_ip, server_port, local_port, message):
    """
    This starts a remote ssh session to the given server server.
    """

    command_list = ['ssh', '-R', '*:%s:localhost:%s' % (server_port, local_port), 'open@%s' % server_ip, '-o',
                    'StrictHostKeyChecking=no', '-o', 'ExitOnForwardFailure=yes', 'while true; do sleep 10; done']
    s = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)

    time.sleep(2)

    if s.poll() is not None:
        print '%s - %s' % (s.stdout.read(), s.stderr.read())
        exit(7)

    print u'You are now connected, your port %s can now be accessed on %s:%s\n%s' % (
        local_port, server_ip, server_port, message)
    return s


if __name__ == '__main__':
    local_port=argv[1]
    request_server_port = argv[2] if len(argv) >= 4 else -1
    restart_session_token = argv[3] if len(argv) >= 4 else -1
    signal.signal(signal.SIGTERM, handleSigTERM)
    signal.signal(signal.SIGINT, handleSigTERM)

    key = getPublicKey()
    dict = request_port(key, restart_session_token=restart_session_token, request_server_port=request_server_port)
    if 'error' in dict:
        print dict['error']
        sys.exit(9)
    s = startSession(dict['server_ip'], dict['server_port'], local_port, dict['message'])
    s.wait()
