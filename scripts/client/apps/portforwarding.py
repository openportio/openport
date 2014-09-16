import socket
import threading
import paramiko
import time
import select
from services.logger_service import get_logger
from socket import error as SocketError
import errno

logger = get_logger(__name__)


class PortForwardException(Exception):
    pass


class IgnoreUnknownHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """A Paramiko policy that ignores UnknownHostKeyError for missing keys."""
    def missing_host_key(self, client, hostname, key):
        pass


class PortForwardingService:

    def __init__(self,
                 local_port,
                 remote_port,
                 server,
                 server_ssh_port,
                 ssh_user,
                 public_key_file,
                 private_key_file,
                 error_callback=None,
                 success_callback=None,
                 fallback_server_ssh_port=None,
                 http_forward_address=None,
                 start_callback=None):
        self.local_port       = local_port
        self.remote_port      = remote_port
        self.server           = server
        self.server_ssh_port  = server_ssh_port
        self.ssh_user         = ssh_user
        self.public_key_file  = public_key_file
        self.private_key_file = private_key_file
        self.error_callback   = error_callback
        self.success_callback = success_callback
        self.fallback_server_ssh_port = fallback_server_ssh_port
        self.http_forward_address = http_forward_address
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(IgnoreUnknownHostKeyPolicy())
        self.start_callback = start_callback

    def stop(self):
        self.client.close()

    def start(self):
        """This will connect to the server and start port forwarding to the given port of the localhost"""
        self.client.load_system_host_keys()

        logger.debug('Connecting to ssh host %s:%d ...' % (self.server, self.server_ssh_port))
        pk = paramiko.RSAKey(filename=self.private_key_file)

        try:
            self.client.connect(self.server, self.server_ssh_port, username=self.ssh_user, pkey=pk, look_for_keys=False)
        except Exception, e:
            logger.error('*** Failed to connect to %s:%d: %r' % (self.server, self.server_ssh_port, e))
            if self.fallback_server_ssh_port is not None:
                try:
                    self.client.connect(
                        self.server, self.fallback_server_ssh_port, username=self.ssh_user, pkey=pk, look_for_keys=False)
                except Exception, e:
                    logger.error( '*** Failed to fallback connect to %s:%d: %r' % (self.server, self.fallback_server_ssh_port, e) )
                    if self.error_callback:
                        self.error_callback()
                    return
            else:
                if self.error_callback:
                    self.error_callback()
                return

        try:
            self.portForwardingRequestException = None
            thr = threading.Thread(target=self._forward_local_port)
            thr.setDaemon(True)
            thr.start()

            if self.start_callback:
                start_callback_thread = threading.Thread(target=self.start_callback)
                start_callback_thread.setDaemon(True)
                start_callback_thread.start()

            self.keep_alive()
        except KeyboardInterrupt, e:
            self.stop()
            logger.info('Ctrl-c: Port forwarding stopped.')
#            sys.exit(0)

    def keep_alive(self):
        error_count = 0
        while error_count < 2:
            if self.portForwardingRequestException is not None:
                if self.error_callback:
                    self.error_callback()
                raise PortForwardException('port forwarding thread gave an exception...',
                                           self.portForwardingRequestException)
            try:
                self.client.exec_command('echo ""')
                if self.success_callback:
                    self.success_callback()
                time.sleep(10)
                error_count = 0
            except Exception, ex:
                error_count += 1
                if self.error_callback:
                    self.error_callback()
                logger.debug(ex)
        raise PortForwardException('keep_alive stopped')

    def _forward_local_port(self):
        try:
            transport = self.client.get_transport()
            transport.set_keepalive(30)
            logger.debug('requesting forward from remote port %s' % (self.remote_port,))
            transport.request_port_forward('', self.remote_port)
            while True:
                chan = transport.accept(1000)
                if chan is None:
                    continue
                thr = threading.Thread(target=self._port_forward_handler, args=(chan,))
                thr.setDaemon(True)
                thr.start()
        except Exception as e:
            self.portForwardingRequestException = e

    def _port_forward_handler(self, chan):
        """
        A handler to handle the incomming traffic.
        This will connect the channel to the localhost at the given port.
        """
        local_server = 'localhost'
        logger.debug('Opening socket %s:%s'% (local_server, self.local_port))
        sock = socket.socket()
        try:
            sock.connect((local_server, self.local_port))
        except Exception, e:
            logger.error('Forwarding request to %s:%d failed: %r' % (local_server, self.local_port, e))
            return

        logger.debug('Connected!  Tunnel open %r -> %r -> %r' % (chan.origin_addr,
                                                            chan.getpeername(), (local_server, self.local_port)))

        try:
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
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                logger.debug('Got a connection reset by peer.')
            else:
                raise

        chan.close()
        sock.close()
        logger.debug('Tunnel closed from %r' % (chan.origin_addr,))


