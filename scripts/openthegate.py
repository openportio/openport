#!/usr/bin/python

import os
from sys import argv
import subprocess
import signal
import time

def request_port(key):
    """
    Requests a port on the server using the openPort protocol
    return a tuple with ( server_ip, server_port, message )
    """
    import urllib, urllib2

    url = 'http://www.openport.be/post'
    try:
        data = urllib.urlencode({'public_key' : key,})
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req).read()
        parts = response.splitlines()
        if len(parts) < 4 or parts[0] != 'ok':
            for line in parts:
                print line
            exit(8)
        else:
            return parts[1], int(parts[2]), parts[3]
    except Exception, detail:
        print "Err ", detail
        exit(9)

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

def startSession(server_ip, server_port, local_port):
    """
    This starts a remote ssh session to the given server server.
    """

    command_list = ['ssh', '-R', '*:%s:localhost:%s' %(server_port, local_port), 'open@%s' % server_ip, '-o',
                    'StrictHostKeyChecking=no', '-o', 'ExitOnForwardFailure=yes', 'while true; do sleep 10; done']
    s = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)

    time.sleep(2)

    if s.poll() is not None:
        print '%s - %s' % (s.stdout.read(), s.stderr.read())
        exit(7)

    print u'You are now connected, your port %s can now be accessed on %s:%s\n%s' % (local_port, server_ip, server_port, message)
    return s

	
if __name__ == '__main__':
	local_port=argv[1]
	signal.signal(signal.SIGTERM, handleSigTERM)
	signal.signal(signal.SIGINT, handleSigTERM)

	key = getPublicKey()
	(server_ip, server_port, message) = request_port(key)
	s = startSession(server_ip, server_port, local_port)
	s.wait()
