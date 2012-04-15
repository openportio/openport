#!/usr/bin/env python

# Copyright (C) 2008  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distrubuted in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

"""
Sample script showing how to do remote port forwarding over paramiko.

This script connects to the requested SSH server and sets up remote port
forwarding (the openssh -R option) from a remote port through a tunneled
connection to a destination reachable from the local machine.
"""

import getpass
import os
import socket
import select
import sys
import threading

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
		
def start(options, server, remote):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    verbose('Connecting to ssh host %s:%d ...' % (server[0], server[1]))
	
    pk = paramiko.RSAKey(filename=options.private_keyfile)
	
    try:
        client.connect(server[0], server[1], username=options.user, pkey=pk,
                       look_for_keys=options.look_for_keys)
    except Exception, e:
        print '*** Failed to connect to %s:%d: %r' % (server[0], server[1], e)
        sys.exit(1)

    verbose('Now forwarding remote port %d to %s:%d ...' % (options.port, remote[0], remote[1]))

    try:
        reverse_forward_tunnel(options.port, remote[0], remote[1], client.get_transport())
    except KeyboardInterrupt:
        print 'C-c: Port forwarding stopped.'
        sys.exit(0)

		
class options():
	def __init__(self):
		self.port = 8000
		self.user = 'open'
		self.private_keyfile = 'id_rsa'
		self.public_keyfile = 'id_rsa.pub'
		self.look_for_keys = False
		
		
def write_new_key(private_key_filename, public_key_filename):		
	key = paramiko.RSAKey.generate(1024)
	key.write_private_key_file(private_key_filename)
	
	pk = paramiko.RSAKey(filename=private_key_filename)
	
	o = open(public_key_filename ,'w').write("ssh-rsa " +pk.get_base64()+ " \n")
		
def main():
	optionss = options()
	
	if not os.path.exists(optionss.private_keyfile) or not not os.path.exists(optionss.public_keyfile):
		write_new_key(optionss.private_keyfile, optionss.public_keyfile)
	public_key = open( optionss.public_keyfile, 'r').readline()
	
	(server_ip, server_port, message) = request_port( public_key )
	
	optionss.port = server_port

	remote = ('localhost', 8000)
	server = (server_ip, 22)
	start(optionss, server, remote)

if __name__ == '__main__':
    main()
