import logging
import socket
import threading
import paramiko
import sys
import time
import select
from loggers import get_logger

logger = get_logger(__name__)

class IgnoreUnknownHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """A Paramiko policy that ignores UnknownHostKeyError for missing keys."""
    def missing_host_key(self, client, hostname, key):
        pass

def forward_port(local_port, remote_port, server, server_ssh_port, ssh_user, public_key_file, private_key_file):
    """This will connect to the server and start port forwarding to the given port of the localhost"""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy( IgnoreUnknownHostKeyPolicy() )

    logger.debug('Connecting to ssh host %s:%d ...' % (server, server_ssh_port))

    pk = paramiko.RSAKey(filename=private_key_file)

    try:
        client.connect(server, server_ssh_port, username=ssh_user, pkey=pk,
            look_for_keys=False)
    except Exception, e:
        print '*** Failed to connect to %s:%d: %r' % (server, server_ssh_port, e)
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

    try:
        reverse_forward_tunnel(local_port, remote_port, client.get_transport())
        logger.info('Now forwarding remote port %s:%d to localhost:%d...' % (server, remote_port, local_port))
    except KeyboardInterrupt:
        print 'C-c: Port forwarding stopped.'
        sys.exit(0)


def port_forward_handler(chan, localhost, local_port):
    """
    A handler to handle the incomming traffic.
    This will connect the channel to the localhost at the given port.
    """

    logger.info('Opening socket %s:%d'% (localhost, local_port))
    sock = socket.socket()
    try:
        sock.connect((localhost, local_port))
    except Exception, e:
        logger.error('Forwarding request to %s:%d failed: %r' % (localhost, local_port, e))
        return

    logger.info('Connected!  Tunnel open %r -> %r -> %r' % (chan.origin_addr,
                                                        chan.getpeername(), (localhost, local_port)))
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if not len(data):
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if not len(data):
                break
            sock.send(data)
    chan.close()
    sock.close()
    logger.info('Tunnel closed from %r' % (chan.origin_addr,))


def reverse_forward_tunnel(local_port, remote_port, transport):
    transport.set_keepalive(30)
    transport.request_port_forward('', remote_port)
    while True:
        chan = transport.accept(1000)
        if chan is None:
            continue
        thr = threading.Thread(target=port_forward_handler, args=(chan, 'localhost', local_port))
        thr.setDaemon(True)
        thr.start()