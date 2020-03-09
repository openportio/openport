import errno
from urllib.parse import urlparse

import paramiko
import socks
import threading
import time
from socket import error as SocketError

from openport.apps.keyhandling import get_default_key_locations
from openport.services.logger_service import get_logger
from openport.services.utils import run_method_with_timeout, TimeoutException

logger = get_logger(__name__)


class TunnelError(Exception):
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
                 fallback_ssh_server=None,
                 http_forward_address=None,
                 start_callback=None,
                 forward_tunnel=False,
                 session_token=None,
                 keep_alive_interval_seconds=10,
                 proxy=None,
                 ):
        self.local_port = local_port
        self.remote_port = remote_port
        self.server = server
        self.server_ssh_port = server_ssh_port
        self.ssh_user = ssh_user

        default_public_key_file, default_private_key_file = get_default_key_locations()

        self.public_key_file = public_key_file if public_key_file else default_public_key_file
        self.private_key_file = private_key_file if private_key_file else default_private_key_file
        self.error_callback = error_callback
        self.success_callback = success_callback
        self.fallback_server_ssh_port = fallback_server_ssh_port
        self.fallback_ssh_server = fallback_ssh_server
        self.http_forward_address = http_forward_address
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(IgnoreUnknownHostKeyPolicy())
        self.start_callback = start_callback
        self.forward_tunnel = forward_tunnel
        self.session_token = session_token
        self.keep_alive_interval_seconds = keep_alive_interval_seconds

        self.portForwardingRequestException = None
        self.stopped = False
        self.proxy = proxy
        self.sock = None
        if self.proxy:
            parsed = urlparse(self.proxy)
            self.sock = socks.socksocket()
            self.sock.set_proxy(
                proxy_type=socks.SOCKS5,
                addr=parsed.hostname,
                port=parsed.port,
                username=parsed.username,
                password=parsed.password,
            )

    def stop(self):
        self.stopped = True
        self.client.close()

    def start(self):
        """This will connect to the server and start port forwarding to the given port of the localhost"""
        self.client.load_system_host_keys()

        logger.debug('Connecting to ssh host %s:%d ...' % (self.server, self.server_ssh_port))
        pk = paramiko.RSAKey(filename=self.private_key_file)

        try:
            if self.sock:
                self.sock.connect((self.server, self.server_ssh_port))
            self.client.connect(
                self.server,
                self.server_ssh_port,
                username=self.ssh_user,
                pkey=pk,
                look_for_keys=False,
                sock=self.sock,
            )
            self.stopped = False
        except Exception as e:
            logger.error('*** Failed to connect to %s:%d: %r' % (self.server, self.server_ssh_port, e))
            if self.fallback_server_ssh_port is not None:
                try:
                    logger.debug('Connecting to fallback ssh host %s:%d ...' % (
                        self.fallback_ssh_server, self.fallback_server_ssh_port))
                    if self.sock:
                        self.sock.connect((self.server, self.server_ssh_port))

                    self.client.connect(
                        self.fallback_ssh_server,
                        self.fallback_server_ssh_port,
                        username=self.ssh_user,
                        pkey=pk,
                        look_for_keys=False,
                        sock=self.sock,
                    )
                    self.stopped = False
                except Exception as e:
                    logger.error('*** Failed to fallback connect to %s:%d: %r' % (self.fallback_ssh_server,
                                                                                  self.fallback_server_ssh_port, e))
                    if self.error_callback:
                        self.error_callback(e)
                    return
            else:
                if self.error_callback:
                    self.error_callback(e)
                return

        try:
            stdin, stdout, stderr = run_method_with_timeout(lambda: self.client.exec_command(self.session_token),
                                                            timeout_s=10)
        except (TimeoutException, paramiko.SSHException):
            raise TunnelError('Connection to the server seems to be lost.')

        try:
            self.portForwardingRequestException = None

            if self.forward_tunnel:
                thr = threading.Thread(target=self._forward_remote_port)
            else:
                thr = threading.Thread(target=self._forward_local_port)
            thr.setDaemon(True)
            thr.start()

            if self.start_callback:
                start_callback_thread = threading.Thread(target=self.start_callback)
                start_callback_thread.setDaemon(True)
                start_callback_thread.start()

            self.keep_alive()
        except KeyboardInterrupt as e:
            self.stop()
            logger.info('Ctrl-c: Port forwarding stopped.')
        #            sys.exit(0)
        except EOFError as e:
            # Tunnel is stopped.
            self.stop()
            logger.debug(e)
        except:
            self.stop()
            raise

    def keep_alive(self):
        while not self.stopped:
            time.sleep(self.keep_alive_interval_seconds)
            if self.stopped:
                return
            if self.portForwardingRequestException is not None:
                if self.error_callback:
                    self.error_callback(self.portForwardingRequestException)
                logger.exception(self.portForwardingRequestException)

            logger.debug('sending keep_alive')

            try:
                stdin, stdout, stderr = run_method_with_timeout(lambda: self.client.exec_command(self.session_token),
                                                                timeout_s=10)
            except (TimeoutException, paramiko.SSHException):
                raise TunnelError('Connection to the server seems to be lost.')

            # logger.debug('keep_alive sent: stdout %s' % stdout.read())
            # logger.debug('keep_alive sent: stderr %s' % sterr.read())
            if self.success_callback:
                self.success_callback()

    def _forward_local_port(self):
        try:
            transport = self.client.get_transport()
            transport.set_keepalive(self.keep_alive_interval_seconds)
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

    def _forward_remote_port(self):
        create_forward_tunnel(self.local_port, 'localhost', self.remote_port, self.client.get_transport())

    def _port_forward_handler(self, chan):
        """
        A handler to handle the incoming traffic.
        This will connect the channel to the localhost at the given port.
        """
        local_server = 'localhost'
        logger.debug('Opening socket %s:%s' % (local_server, self.local_port))
        sock = socket.socket()
        try:
            sock.connect((local_server, self.local_port))
        except Exception as e:
            logger.error('Forwarding request to %s:%d failed: %r' % (local_server, self.local_port, e))
            sock.close()
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
        finally:
            chan.close()
            sock.close()
            logger.debug('Tunnel closed from %r' % (chan.origin_addr,))


import socket
import select

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

import paramiko

SSH_PORT = 22
DEFAULT_PORT = 4000

g_verbose = True


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(SocketServer.BaseRequestHandler):

    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception as e:
            logger.debug('Incoming request to %s:%d failed: %s' % (self.chain_host,
                                                                   self.chain_port,
                                                                   repr(e)))
            chan = None
        if chan is None:
            logger.error('Incoming request to %s:%d was rejected by the SSH server.' %
                         (self.chain_host, self.chain_port))
            return

        logger.debug('Connected!  Tunnel open %r -> %r -> %r' % (self.request.getpeername(),
                                                                 chan.getpeername(),
                                                                 (self.chain_host, self.chain_port)))
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        peername = self.request.getpeername()

        chan.close()
        self.request.close()
        logger.debug('Tunnel closed from %r' % (peername,))


def create_forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHandler(Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport

    ForwardServer(('', local_port), SubHandler).serve_forever()
