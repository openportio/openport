from time import sleep
import urllib2

__author__ = 'Jan'
import subprocess
import unittest
import os
import signal
from services import osinteraction

from test_utils import SimpleTcpServer, SimpleTcpClient, get_open_port, lineNumber, SimpleHTTPClient, TestHTTPServer
from services.utils import nonBlockRead
from services.logger_service import get_logger

logger = get_logger(__name__)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()
        self.manager_port = -1

    def tearDown(self):
        self.kill_all_processes(self.processes_to_kill)

        self.kill_manager(self.manager_port)

    def kill_all_processes(self, processes_to_kill):
        for p in processes_to_kill:
            try:
                os.kill(p.pid, signal.SIGKILL)
                p.wait()
            except Exception as e:
                pass

    def testOpenportApp(self):
        port = get_open_port()
        s = SimpleTcpServer(port)
        s.runThreaded()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--server', 'www.openport.be', '--verbose'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(5)
        process_output = AppTests.get_all_output(p)
        print 'output: ', process_output

        if p.poll() is not None: # process terminated
            print AppTests.get_all_output(p)
            self.fail('p.poll() should be None but was %s' % p.poll())

        remote_host, remote_port = self.getRemoteHostAndPort(process_output)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        c.close()
        s.close()
        p.kill()

    def check_application_is_still_alive(self, p):
        if p.poll() is not None: # process terminated
            print 'application terminated: ', AppTests.get_all_output(p)
            self.fail('p_app.poll() should be None but was %s' % p.poll())

    def test_manager(self):
        db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp_openport.db')
        try:
            os.remove(db_file)
        except OSError:
            pass

        port = get_open_port()
        print 'localport :', port
        s = SimpleTcpServer(port)
        s.runThreaded()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        manager_port = get_open_port()
        self.manager_port = manager_port
        print 'manager_port :', manager_port

        p_manager = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                                   '--verbose', '--manager-port', str(manager_port)],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p_app = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', 'test.openport.be', '--manager-port', str(manager_port)],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)
        self.processes_to_kill.append(p_app)
        sleep(15)

        process_output = AppTests.get_all_output(p_app)
        print lineNumber(), 'output: ', process_output

        self.check_application_is_still_alive(p_manager)
        self.check_application_is_still_alive(p_app)

        remote_host, remote_port = self.getRemoteHostAndPort(process_output)
        print lineNumber(), "remote port:", remote_port

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()
   #     s.close()

        os.kill(p_app.pid, signal.SIGKILL)
        self.assertNotEqual(p_app.wait(), None)
        while self.osinteraction.pid_is_running(p_app.pid):
            print "waiting for pid to be killed: %s" % p_app.pid
            sleep(1)
        os.kill(p_manager.pid, signal.SIGINT)
        print 'waiting for manager to be killed'
        p_manager.wait()
        print lineNumber(),  "manager:", AppTests.get_all_output(p_manager)

        print lineNumber(),  "p_app:", AppTests.get_all_output(p_app)

        sleep(5)

  #      s = SimpleTcpServer(port)
  #      s.runThreaded()

        p_manager2 = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                                    '--verbose', '--manager-port', str(manager_port)],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(10)

        print lineNumber(),  "manager:", AppTests.get_all_output(p_manager2)
        self.check_application_is_still_alive(p_manager2)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        os.kill(p_manager2.pid, signal.SIGINT)
        p_manager2.wait()
        print lineNumber(),  "manager:", AppTests.get_all_output(p_manager2)

        response = c.send(request)
        self.assertNotEqual(request, response.strip())

        c.close()
        s.close()


    def getRemoteHostAndPort(self, output):
        import re
        m = re.search(r'Now forwarding remote port ([^:]*):(\d*) to localhost', output)
        return m.group(1), int(m.group(2))

    def getRemoteAddress(self, output):
        print 'getRemoteAddress - output:%s' % output
        import re
        m = re.search(r'Now forwarding remote address ([a-z\\.]*) to localhost', output)
        return m.group(1)

    def test_manager_spawning(self):
        manager_port = get_open_port()
        self.manager_port = manager_port
        print 'manager port: ', manager_port
        self.assertFalse(self.managerIsRunning(manager_port))

        db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp_openport.db')
        try:
            os.remove(db_file)
        except OSError:
            pass

        port = get_open_port()
        print 'local port: ', port

        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        p_app = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', 'test.openport.be', '--manager-port', str(manager_port)],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        sleep(15)
        process_output = AppTests.get_all_output(p_app)
        print lineNumber(), 'output: ', process_output

        self.check_application_is_still_alive(p_app)
        self.assertTrue(self.managerIsRunning(manager_port))

        remote_host, remote_port = self.getRemoteHostAndPort(process_output)
        print lineNumber(), "remote port:", remote_port

        os.kill(p_app.pid, signal.SIGKILL)
        p_app.wait()
        sleep(1)
        self.assertTrue(self.managerIsRunning(manager_port))
        self.kill_manager(manager_port)
        self.assertFalse(self.managerIsRunning(manager_port))

    def test_restart_manager_on_different_port(self):
        manager_port = get_open_port()
        print 'manager port: ', manager_port
        self.manager_port = manager_port
        self.assertFalse(self.managerIsRunning(manager_port))
        db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp_openport.db')
        try:
            os.remove(db_file)
        except OSError:
            pass

        port = get_open_port()
        print 'local port: ', port

        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        p_app = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', 'test.openport.be', '--manager-port', str(manager_port),
                                  '--manager-database', db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        sleep(15)
        process_output = AppTests.get_all_output(p_app)
        print lineNumber(), 'output app: ', process_output
        remote_host, remote_port = self.getRemoteHostAndPort(process_output)
        print lineNumber(), "remote port:", remote_port

        self.check_application_is_still_alive(p_app)
        self.assertTrue(self.managerIsRunning(manager_port))

        self.kill_manager(manager_port)
        self.kill_all_processes(self.processes_to_kill)

        new_manager_port = get_open_port()
        print 'new manager port:', new_manager_port
        self.assertNotEqual(manager_port, new_manager_port)

        p_manager2 = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                                    '--verbose', '--manager-port', str(new_manager_port), '--server', 'test.openport.be'],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)

        sleep(15)
        process_output = AppTests.get_all_output(p_manager2)
        print lineNumber(), 'output manager: ', process_output
        self.assertEqual(1, self.get_share_count_of_manager(new_manager_port))

        self.check_http_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)

    @staticmethod
    def get_all_output(p):
        return 'stdout: %s stderr: %s' % (nonBlockRead(p.stdout), nonBlockRead(p.stderr))


    def check_http_port_forward(self, remote_host, local_port, remote_port=80):
        s = TestHTTPServer(local_port)
        response = 'echo'
        s.reply(response)
        s.runThreaded()

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % local_port)
        self.assertEqual(actual_response, response.strip())
        url = 'http://%s:%s' % (remote_host, remote_port) if remote_port != 80 else 'http://%s' % remote_host
        print 'checking url:', url
        actual_response = c.get(url)
        self.assertEqual(actual_response, response.strip())
        print 'http portforward ok'
        s.server.shutdown()

    def check_tcp_port_forward(self, remote_host, local_port, remote_port):

        text = 'ping'

        s = SimpleTcpServer(local_port)
        s.runThreaded()

        cl = SimpleTcpClient('127.0.0.1', local_port)
        self.assertEqual(text, cl.send(text))
        cl.close()

        cr = SimpleTcpClient(remote_host, remote_port)
        self.assertEqual(text, cr.send(text))
        cr.close()
        print 'tcp portforward ok'
        s.close()

    def kill_manager(self, manager_port):
        url = 'http://localhost:%s/exit' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=1).read()
            if response.strip() != 'ok':
                print lineNumber(), response
        except Exception, detail:
            print detail

    def get_share_count_of_manager(self, manager_port):
        url = 'http://localhost:%s/active_count' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=1).read()
            return int(response)

        except Exception as detail:
            print 'error contacting the manager: %s %s' % (url, detail)
            raise

    def managerIsRunning(self, manager_port):
        url = 'http://localhost:%s/ping' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=5).read()
            if response.strip() != 'pong':
                print lineNumber(), response
                return False
            else:
                return True
        except Exception, detail:
            return False

    def testOpenportAppWithHttpForward(self):
        port = get_open_port()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--http-forward', '--server', 'test.openport.be'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(15)
        process_output = AppTests.get_all_output(p)
        print 'output app: ', process_output

        self.check_application_is_still_alive(p)
        if p.poll() is not None: # process terminated
            self.fail('p.poll() should be None but was %s' % p.poll())

        remote_host = self.getRemoteAddress(process_output)

        self.check_http_port_forward(remote_host, port)
