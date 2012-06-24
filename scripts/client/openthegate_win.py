#!/usr/bin/env python

import getpass
import os
import socket
import select
import sys
import threading
from sys import argv
import time
import wx

from openthegate import request_port

from optparse import OptionParser

import paramiko
g_verbose = True


def handler(chan, host, port):
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception, e:
        verbose('Forwarding request to %s:%d failed: %r' % (host, port, e))
        return
    
    verbose('Connected!  Tunnel open %r -> %r -> %r' % (chan.origin_addr,
                                                        chan.getpeername(), (host, port)))
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()
    verbose('Tunnel closed from %r' % (chan.origin_addr,))


def reverse_forward_tunnel(server_port, remote_host, remote_port, transport):
    transport.set_keepalive(30)
    transport.request_port_forward('', server_port)
    while True:
        chan = transport.accept(1000)
        if chan is None:
            continue
        thr = threading.Thread(target=handler, args=(chan, remote_host, remote_port))
        thr.setDaemon(True)
        thr.start()


def verbose(s):
    if g_verbose:
        print s


HELP = """\
Set up a reverse forwarding tunnel across an SSH server, using paramiko. A
port on the SSH server (given with -p) is forwarded across an SSH session
back to the local machine, and out to a remote site reachable from this
network. This is similar to the openssh -R option.
"""

class IgnoreUnknownHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """A Paramiko policy that ignores UnknownHostKeyError for missing keys."""
    def missing_host_key(self, client, hostname, key):
        pass
 
		
def start(options, server, remote):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy( IgnoreUnknownHostKeyPolicy() )

    verbose('Connecting to ssh host %s:%d ...' % (server[0], server[1]))
	
    pk = paramiko.RSAKey(filename=options.private_keyfile)
	
    try:
        client.connect(server[0], server[1], username=options.user, pkey=pk,
                       look_for_keys=options.look_for_keys)
    except Exception, e:
        print '*** Failed to connect to %s:%d: %r' % (server[0], server[1], e)
        sys.exit(1)


    def keep_alive(client):
        errorCount = 0
        while errorCount < 30:
            try:
                client.exec_command('echo ""')
                time.sleep(30)
            except Exception, ex:
                errorCount+=1
                print ex

    thr = threading.Thread(target=keep_alive, args=(client,))
    thr.setDaemon(True)
    thr.start()

    verbose('Now forwarding remote port %d to %s:%d ...' % (options.port, remote[0], remote[1]))

    try:
        reverse_forward_tunnel(options.port, remote[0], remote[1], client.get_transport())
    except KeyboardInterrupt:
        print 'C-c: Port forwarding stopped.'
        sys.exit(0)

		
class options():
	def __init__(self):
		self.port = None
		self.user = 'open'
		homedir = os.path.expanduser('~')
		self.private_keyfile = os.path.join(homedir, '.ssh', 'id_rsa')
		self.public_keyfile =  os.path.join(homedir, '.ssh', 'id_rsa.pub')
		self.look_for_keys = False
		
		
def write_new_key(private_key_filename, public_key_filename):	
#	print 'writing keys: %s %s' %( private_key_filename, public_key_filename)
	key = paramiko.RSAKey.generate(1024)
	if not os.path.exists( os.path.dirname(private_key_filename) ):
		os.makedirs( os.path.dirname(private_key_filename), 0700)
	key.write_private_key_file(private_key_filename)
	
	pk = paramiko.RSAKey(filename=private_key_filename)
	if not os.path.exists( os.path.dirname(public_key_filename) ):
		os.makedirs( os.path.dirname(public_key_filename), 0700)
	o = open(public_key_filename ,'w').write("ssh-rsa " +pk.get_base64()+ " \n")
		
def open_port(port, callback=None, extra_args={}):
    optionss = options()

    if not os.path.exists(optionss.private_keyfile) or not os.path.exists(optionss.public_keyfile):
        write_new_key(optionss.private_keyfile, optionss.public_keyfile)
    public_key = open( optionss.public_keyfile, 'r').readline()
    dict = request_port( public_key )

    if 'error' in dict:
        wx.MessageBox('An error has occured:\n%s' %(dict['error']), 'Error', wx.OK | wx.ICON_ERROR)
        sys.exit(8)

    server_ip, server_port, message, account_id, key_id = \
        dict['server_ip'], dict['server_port'], dict['message'], dict['account_id'], dict['key_id']
    optionss.port = server_port

    remote = ('localhost', port)
    server = (server_ip, 22)
    if callback is not None:
        import threading
        thr = threading.Thread(target=callback, args=(server_ip, server_port, account_id, key_id, extra_args))
        thr.setDaemon(True)
        thr.start()
    while True:
        start(optionss, server, remote)
        time.sleep(60)

if __name__ == '__main__':
	port = int(argv[1])

	open_port(port)
