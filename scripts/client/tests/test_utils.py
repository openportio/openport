import os
import socket
import sys
import signal
import re
from time import sleep
import inspect
import subprocess
import threading
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib2
from services.logger_service import get_logger
from services.utils import get_all_output

logger = get_logger(__file__)


class TestHTTPServer(object):
    def __init__(self, port):
        self.server = HTTPServer(('', port), TestHTTPRequestHandler)

    def reply(self, response):
        self.server.response_string = response #what a hack

    def runThreaded(self):
        import threading
        thr = threading.Thread(target=self.server.serve_forever, args=())
        thr.setDaemon(True)
        thr.start()


class TestHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, httpServer):
        self._response_string = httpServer.response_string
        BaseHTTPRequestHandler.__init__(self, request, client_address, httpServer)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(self._response_string)))
        self.end_headers()
        self.wfile.write(self._response_string)
        self.wfile.close()


class SimpleHTTPClient(object):

    def get(self, url):
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            return urllib2.urlopen(req).read()
        except Exception as detail:
            print "An error has occurred: ", detail
            sleep(1)
            #print "detail: ", detail.read()
            raise detail


class SimpleTcpServer(object):

    def __init__(self, port):
        self.HOST = '127.0.0.1' # Symbolic name meaning the local host
        self.PORT = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((self.HOST, self.PORT))
        self.s.listen(5)
        self.connections_accepted = 0

    def run(self):
        while 1:
            print "connections accepted: ", self.connections_accepted
            self.connections_accepted += 1
            conn, self.address = self.s.accept()
            print 'Connected by', self.address
            data = conn.recv(1024)
            if data:
                conn.send(data)
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

    def close(self):
        try:
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
        except:
            pass

    def runThreaded(self):
        import threading
        thr = threading.Thread(target=self.run, args=())
        thr.setDaemon(True)
        thr.start()


class SimpleTcpClient(object):
    def __init__(self, host, port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
#            sys.exit(1)

        try:
            self.sock.connect((host, port))
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
#            sys.exit(2)


    def send(self, request):
        self.sock.send('%s\n' % request)

        data = self.sock.recv(1024)
        response = ""
        while len(data):
            response += data
            data = self.sock.recv(1024)
        return response

    def close(self):
        self.sock.close()


def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def lineNumber():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

if __name__ == '__main__':

#    port = get_open_port()
#    s = SimpleTcpServer(port)
#    s.runThreaded()
#    sleep(1)
#
#    c = SimpleTcpClient('localhost', port)
#
#    var = raw_input('Enter something: ')
#    print 'you entered ', var
#    print 'server replied', c.send(var)

    port = get_open_port()
    s = TestHTTPServer(port)
    s.reply('hooray')
    s.runThreaded()
    sleep(1)

    c = SimpleHTTPClient()

    print 'server replied', c.get('http://localhost:%s' % port)


def run_command_with_timeout(args, timeout_s):

    class Command(object):
        def __init__(self, cmd):
            self.cmd = cmd
            self.process = None

        def run(self, timeout):
            def target():
                #print 'Thread started'
                self.process = subprocess.Popen(self.cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                self.process.wait()
                #self.process.communicate()
                #print 'Thread finished'

            thread = threading.Thread(target=target)
            thread.start()

            thread.join(timeout)
            if thread.is_alive():
                print 'Terminating process'
                self.process.terminate()
                thread.join()
            print self.process.returncode
            return get_all_output(self.process)

    c = Command(args)
    return c.run(timeout_s)


def get_remote_host_and_port(output):
    m = re.search(r'Now forwarding remote port ([^:]*):(\d*) to localhost', output)
    return m.group(1), int(m.group(2))


def kill_all_processes(processes_to_kill):
    for p in processes_to_kill:
        try:
            os.kill(p.pid, signal.SIGKILL)
            p.wait()
        except Exception as e:
            pass
