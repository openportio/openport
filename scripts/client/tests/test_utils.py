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
from services import osinteraction

logger = get_logger(__name__)


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

    def stop(self):
        self.server.server_close()


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

    def get(self, url, print500=True):
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            return urllib2.urlopen(req, timeout=5).read()
        except urllib2.HTTPError, e:
            if print500 and e.getcode() == 500:
                print e.read()
            raise
        except Exception as detail:
            print "An error has occurred: ", detail
            raise


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
            self.sock.settimeout(5)
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
#            sys.exit(1)

        try:
            self.sock.connect((host, port))

        except socket.timeout as e:
            sys.stderr.write("[timeout] %s\n" % e)
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg)
            if len(msg) > 0:
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
#        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()


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

    port = osinteraction.getInstance().get_open_port()
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
                command = self.cmd
                if not osinteraction.is_linux():
                    command = ' '.join(['"%s"' % arg for arg in self.cmd])


                self.process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                                shell=not osinteraction.is_linux(), close_fds=osinteraction.is_linux())
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
            return osinteraction.getInstance().get_all_output(self.process)

    c = Command(args)
    return c.run(timeout_s)


def run_method_with_timeout(function, timeout_s, args=[], kwargs={}, raise_exception=True):
    return_value = None

    def method1():
        global return_value
        return_value = function(*args, **kwargs)

    thread = threading.Thread(target=method1)
    thread.daemon = True
    thread.start()

    thread.join(timeout_s)
    if thread.is_alive():
        if raise_exception:
            raise Exception('Timeout!')
    return return_value

def run_command_with_timeout_return_process(args, timeout_s):

    class Command(object):
        def __init__(self, cmd):
            self.cmd = cmd
            self.process = None

        def run(self, timeout):
            command = self.cmd
            if not osinteraction.is_linux():
                command = ' '.join(['"%s"' % arg for arg in self.cmd])
            self.process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                            shell=not osinteraction.is_linux(), close_fds=osinteraction.is_linux())

            def kill_target():
                wait_thread.join(timeout)
                if wait_thread.is_alive():
                    print 'Terminating process'
                    self.process.terminate()
                    wait_thread.join()

            def wait_target():
                self.process.wait()

            wait_thread = threading.Thread(target=wait_target)
            wait_thread.setDaemon(True)
            wait_thread.start()

            kill_thread = threading.Thread(target=kill_target)
            kill_thread.setDaemon(True)
            kill_thread.start()

            return self.process

    c = Command(args)
    return c.run(timeout_s)

def get_remote_host_and_port(p, osinteraction, timeout=30, output_prefix=''):
    i = 0
    while i < timeout:
        i += 1
        all_output = osinteraction.get_all_output(p)
        if all_output[0]:
            print '%s - stdout -  %s' % (output_prefix, all_output[0])
        if all_output[1]:
            print '%s - stderr - %s' % (output_prefix, all_output[1])
        if not all_output[0]:
            sleep(1)
            continue
        m = re.search(r'Now forwarding remote port ([^:]*):(\d*) to localhost', all_output[0])
        if m is None:
            sleep(1)
            continue
        else:
            sleep(3)
            host, port = m.group(1), int(m.group(2))
            m = re.search(r'to first go here: ([a-zA-Z0-9\:/\.]+) .', all_output[0])
            link = m.group(1) if m is not None else None
            return host, port, link

    raise Exception('remote host and port not found in output')


def wait_for_response(function, args=[], kwargs={}, timeout=30, throw=True):
    i = 0
    while i < timeout:
        output = function(*args, **kwargs)
        if output:
            return output
        sleep(1)
        i += 1
    if throw:
        raise Exception('function did not response in time')


def print_all_output(app, osinteraction, output_prefix=''):
    all_output = osinteraction.get_all_output(app)
    if all_output[0]:
        print '%s - stdout -  <<<%s>>>' % (output_prefix, all_output[0])
    if all_output[1]:
        print '%s - stderr - <<<%s>>>' % (output_prefix, all_output[1])
    return all_output


def wait_for_success_callback(p_manager, osinteraction, timeout=30, output_prefix=''):
    i = 0
    while i < timeout:
        i += 1
        all_output = print_all_output(p_manager, osinteraction, output_prefix)
        if not all_output[0]:
            sleep(1)
            continue
        if '/successShare' in all_output[0]:
            return
        else:
            sleep(1)
    raise Exception('success_callback not found (timeout expired)')


def kill_all_processes(processes_to_kill):
    for p in processes_to_kill:
        try:
            osinteraction.getInstance().kill_pid(p.pid)
            p.wait()
        except Exception as e:
            logger.exception(e)


def click_open_for_ip_link(link):
    if link:
        logger.info('clicking link %s' % link)
        req = urllib2.Request(link)
        response = urllib2.urlopen(req, timeout=10).read()
        assert 'is now open' in response