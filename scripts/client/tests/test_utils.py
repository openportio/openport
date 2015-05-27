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
import traceback
from apps.openportit import OpenportItApp
from apps.openport import Openport

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
            if hasattr(msg, 'len') and len(msg) > 0:
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
                if osinteraction.is_windows():
                    command = ' '.join(['"%s"' % arg for arg in self.cmd])


                self.process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                                shell=osinteraction.is_windows(), close_fds=not osinteraction.is_windows())
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
            if osinteraction.is_windows():
                command = ' '.join(['"%s"' % arg for arg in self.cmd])
            self.process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                            shell=osinteraction.is_windows(), close_fds=not osinteraction.is_windows())

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
            if p.poll() is None:
                osinteraction.getInstance().kill_pid(p.pid)
            p.wait()
        except Exception as e:
            logger.exception(e)


def click_open_for_ip_link(link):
    if link:
        logger.info('clicking link %s' % link)
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib2.Request(link)
        response = urllib2.urlopen(req, timeout=10, context=ctx).read()
        assert 'is now open' in response

servers = {}


def check_tcp_port_forward(test, remote_host, local_port, remote_port, fail_on_error=True):

    text = 'ping'

    s = servers[local_port] if local_port in servers else SimpleTcpServer(local_port)
    servers[local_port] = s
    try:
        s.runThreaded()

        cl = SimpleTcpClient('127.0.0.1', local_port)
        response = cl.send(text).strip()
        if not fail_on_error and text != response:
            return False
        else:
            test.assertEqual(text, response)
        cl.close()

        cr = SimpleTcpClient(remote_host, remote_port)
        response = cr.send(text).strip()
        if not fail_on_error and text != response:
            return False
        else:
            test.assertEqual(text, response)

        cr.close()
        print 'tcp portforward ok'
    except Exception, e:
        tr = traceback.format_exc()
        logger.error(e)
        logger.error(tr)
        if not fail_on_error:
            return False
        else:
            raise e
    finally:
        s.close()
    return True


def start_openportit_session(test, share):
    test.called_back_success = False
    test.called_back_error = False

    def callback(session1):
        print session1.as_dict()
        test.assertEquals(test.test_server, session1.server)
        test.assertTrue(session1.server_port >= 2000, 'expected server_port >= 2000 but was %s' % session1.server_port)
       # test.assertTrue(share.server_port<= 51000)

        test.assertTrue(session1.account_id > 0, 'share.account_id was %s' % session1.account_id)
        test.assertTrue(session1.key_id > 0, 'share.key_id was %s' % session1.key_id)
        print 'called back, thanks :)'

    def session_success_callback(session1):
        test.called_back_success = True

    def session_error_callback(session1, exception):
        test.called_back_error = True
        raise exception

    share.success_observers.append(session_success_callback)
    share.error_observers.append(session_error_callback)

    app = OpenportItApp()
    app.args.server = test.test_server

    def start_openport_it():
        app.open_port_file(share, callback=callback)
    thr = threading.Thread(target=start_openport_it)
    thr.setDaemon(True)
    thr.start()

    i = 0
    while i < 30 and not test.called_back_success:
        if test.called_back_error:
            test.fail('error call back!')
        sleep(1)
        i += 1
    test.assertTrue(test.called_back_success, 'not called back in time')
    print 'called back after %s seconds' % i
    return app


def start_openport_session(test, session):
    openport = Openport()
    test.called_back_success = False
    test.called_back_error = False

    def callback(session1):
        print session1.as_dict()
        test.assertEquals(test.test_server, session1.server)
        test.assertTrue(session1.server_port >= 2000, 'expected server_port >= 2000 but was %s' % session1.server_port)
       # test.assertTrue(share.server_port<= 51000)

        test.assertTrue(session1.account_id > 0, 'share.account_id was %s' % session1.account_id)
        test.assertTrue(session1.key_id > 0, 'share.key_id was %s' % session1.key_id)
        print 'called back, thanks :)'

    def session_success_callback(session1):
        test.called_back_success = True

    def session_error_callback(session1, exception):
        test.called_back_error = True
        raise exception

    session.success_observers.append(session_success_callback)
    session.error_observers.append(session_error_callback)

    def show_error(error_msg):
        print "error:" + error_msg

    def start_openport():
        openport.start_port_forward(session, server=test.test_server)

    thr = threading.Thread(target=start_openport)
    thr.setDaemon(True)
    thr.start()
    i = 0
    while i < 30 and (not test.called_back_success or session.server_port < 0):
        if test.called_back_error:
            test.fail('error call back!')
        sleep(1)
        i += 1
    test.assertTrue(test.called_back_success, 'not called back in time')
    print 'called back after %s seconds' % i
    return openport

def set_default_args(app, db_location=None):
    app.args.local_port = -1
    app.args.register_key = ''
    app.args.port = -1

    app.args.manager_port = 8001
    app.args.start_manager = True
    app.args.database = db_location
    app.args.request_port = -1
    app.args.request_token = ''
    app.args.verbose = True
    app.args.http_forward = False
    app.args.server = 'testserver.jdb'
    app.args.restart_on_reboot = False
    app.args.no_manager = False
    app.args.config_file = ''
    app.args.list = False
    app.args.kill = 0
    app.args.kill_all = False
    app.args.restart_shares = False
    app.args.listener_port = -1
    app.args.forward_tunnel = False
    app.args.remote_port = -1