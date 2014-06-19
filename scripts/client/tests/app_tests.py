__author__ = 'Jan'
import urllib2
import subprocess
import unittest
import os
import signal
import sys
import xmlrunner
from time import sleep
import logging
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.utils import get_all_output

from services import osinteraction

from test_utils import SimpleTcpServer, SimpleTcpClient, get_open_port, lineNumber, SimpleHTTPClient, TestHTTPServer
from test_utils import run_command_with_timeout, get_remote_host_and_port, kill_all_processes
from services.logger_service import get_logger, set_log_level

logger = get_logger(__name__)


class AppTests(unittest.TestCase):
    def setUp(self):
        set_log_level(logging.DEBUG)
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()
        self.manager_port = -1

    def tearDown(self):
        kill_all_processes(self.processes_to_kill)
        if self.manager_port > 0:
            self.kill_manager(self.manager_port)

    def test_openport_app(self):
        port = get_open_port()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--server', 'test.openport.be', '--verbose',
                              '--manager-port', '-1'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(5)
        process_output = get_all_output(p)
        print 'std_out: ', process_output[0]
        print 'std_err: ', process_output[1]
        self.check_application_is_still_alive(p)

        remote_host, remote_port = get_remote_host_and_port(process_output[0])

        self.check_tcp_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)
        p.kill()

    def test_openport_app_http_forward(self):
        port = get_open_port()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--server', 'test.openport.be', '--verbose',
                              '--manager-port', '-1', '--http-forward'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(5)
        process_output = get_all_output(p)
        print 'std_out: ', process_output[0]
        print 'std_err: ', process_output[1]
        self.check_application_is_still_alive(p)

        remote_host = self.getRemoteAddress(process_output[0])

        self.check_http_port_forward(remote_host=remote_host, local_port=port)
        p.kill()

    def check_application_is_still_alive(self, p):
        if p.poll() is not None: # process terminated
            print 'application terminated: ', get_all_output(p)
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
        sleep(3)
        p_app = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', 'test.openport.be', '--manager-port', str(manager_port)],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)
        self.processes_to_kill.append(p_app)
        sleep(15)

        process_output = get_all_output(p_app)
        print 'std_out: ', process_output[0]
        print 'std_err: ', process_output[1]

        self.check_application_is_still_alive(p_manager)
        self.check_application_is_still_alive(p_app)

        remote_host, remote_port = get_remote_host_and_port(process_output[0])
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

        for out in get_all_output(p_manager):
            print lineNumber(),  'manager:', out
        for out in get_all_output(p_app):
            print lineNumber(), 'p_app: ', out

        sleep(5)

  #      s = SimpleTcpServer(port)
  #      s.runThreaded()

        p_manager2 = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                                    '--verbose', '--manager-port', str(manager_port)],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(10)
        for out in get_all_output(p_manager2):
            print lineNumber(), 'p_manager2: ', out
        self.check_application_is_still_alive(p_manager2)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        os.kill(p_manager2.pid, signal.SIGINT)
        p_manager2.wait()
        for out in get_all_output(p_manager2):
            print lineNumber(), 'p_manager2: ', out

        response = c.send(request)
        self.assertNotEqual(request, response.strip())

        c.close()
        s.close()

    def getRemoteAddress(self, output):
        print 'getRemoteAddress - output:%s' % output
        import re
        m = re.search(r'Now forwarding remote address ([a-z\\.]*) to localhost', output)
        if m is None:
            raise Exception('address not found in output: %s' % output)
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
                                  '--verbose', '--server', 'test.openport.be', '--manager-port', str(manager_port),
                                  '--manager-database', db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        sleep(15)
        process_output = get_all_output(p_app)
        for out in process_output:
            print lineNumber(), 'p_app: ', out

        self.check_application_is_still_alive(p_app)
        self.assertTrue(self.managerIsRunning(manager_port))

        remote_host, remote_port = get_remote_host_and_port(process_output[0])
        print lineNumber(), "remote port:", remote_port

        os.kill(p_app.pid, signal.SIGKILL)
        p_app.wait()
        sleep(1)
        self.assertTrue(self.managerIsRunning(manager_port))
        self.kill_manager(manager_port)
        sleep(5)
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
        process_output = get_all_output(p_app)
        for out in process_output:
            print lineNumber(), 'p_app: ', out
        remote_host, remote_port = get_remote_host_and_port(process_output[0])
        print lineNumber(), "remote port:", remote_port

        self.check_application_is_still_alive(p_app)
        self.assertTrue(self.managerIsRunning(manager_port))

        self.kill_manager(manager_port)
        kill_all_processes(self.processes_to_kill)

        new_manager_port = get_open_port()
        print 'new manager port:', new_manager_port
        self.assertNotEqual(manager_port, new_manager_port)

        p_manager2 = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                                    '--verbose', '--manager-port', str(new_manager_port), '--server', 'test.openport.be'],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)

        sleep(15)
        process_output = get_all_output(p_manager2)
        for out in process_output:
            print lineNumber(), 'p_manager2: ', out
        self.assertEqual(1, self.get_share_count_of_manager(new_manager_port))

        self.check_http_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)

    def test_manager_kills_restarted_openport_processes(self):

        manager_port = get_open_port()
        print 'manager port: ', manager_port
        self.manager_port = manager_port
        self.assertFalse(self.managerIsRunning(manager_port))

        db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp_openport.db')
        try:
            os.remove(db_file)
        except OSError:
            pass
        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p_manager = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                                    '--verbose', '--manager-port', str(manager_port), '--server', 'test.openport.be'],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)

        sleep(1)
        self.assertTrue(self.managerIsRunning(manager_port))

        port = get_open_port()
        print 'local port: ', port

        s = TestHTTPServer(port)
        s.reply('echo')
        s.runThreaded()

        p_app = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', 'test.openport.be', '--manager-port', str(manager_port),
                                  '--http-forward', '--manager-database', db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        print "p_app pid:", p_app.pid
        sleep(5)
        process_output = get_all_output(p_manager)
        print lineNumber(), 'p_manager std_out: ', process_output[0]
        print lineNumber(), 'p_manager std_err: ', process_output[1]
        self.assertEqual(1, self.get_share_count_of_manager(manager_port))
        process_output = get_all_output(p_app)
        print lineNumber(), 'p_app std_out: ', process_output[0]
        print lineNumber(), 'p_app std_err: ', process_output[1]
        remote_host = self.getRemoteAddress(process_output[0])
        sleep(5)

        cr = SimpleHTTPClient()
        try:
            url = 'http://'+remote_host
            print 'url=' + url
            self.assertEqual('echo', cr.get(url))
        except Exception, e:
            tr = traceback.format_exc()
            logger.error(e)
            logger.error(tr)
            self.fail('port forwarding failed')

        self.osinteraction.kill_pid(p_manager.pid, signal.SIGINT)
        sleep(3)
        process_output = get_all_output(p_manager)
        print lineNumber(), 'p_manager std_out: ', process_output[0]
        print lineNumber(), 'p_manager std_err: ', process_output[1]
        self.assertFalse(self.managerIsRunning(manager_port))
        try:
            self.assertEqual('echo', cr.get(url, print500=False))
            self.fail('expecting an exception')
        except:
            pass
        print p_app.communicate()
        self.assertFalse(self.osinteraction.pid_is_running(p_app.pid))
        # Restarting manager, should restart port-forwarding app
        p_manager = subprocess.Popen(['env/bin/python', 'manager/openportmanager.py', '--database', db_file,
                            '--verbose', '--manager-port', str(manager_port), '--server', 'test.openport.be'],
                           stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)

        sleep(10)
        process_output = get_all_output(p_manager)
        print lineNumber(), 'p_manager std_out: ', process_output[0]
        print lineNumber(), 'p_manager std_err: ', process_output[1]
        self.assertTrue(self.managerIsRunning(manager_port))
        self.assertEqual(1, self.get_share_count_of_manager(manager_port))

        try:
            self.assertEqual('echo', cr.get(url))
        except Exception, e:
            tr = traceback.format_exc()
            logger.error(e)
            logger.error(tr)
            self.fail('port forwarding failed')

        # Killing the manager should also kill the app
        self.osinteraction.kill_pid(p_manager.pid, signal.SIGINT)
        sleep(1)

        process_output = get_all_output(p_manager)
        print lineNumber(), 'p_manager std_out: ', process_output[0]
        print lineNumber(), 'p_manager std_err: ', process_output[1]

        self.assertFalse(self.managerIsRunning(manager_port))
        try:
            self.assertEqual('echo', cr.get(url, print500=False))
            self.fail('expecting an exception')
        except:
            pass

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
        try:
            actual_response = c.get(url)
        except urllib2.URLError, e:
            self.fail('Http forward failed')
        self.assertEqual(actual_response, response.strip())
        print 'http portforward ok'
        s.server.shutdown()

    def check_tcp_port_forward(self, remote_host, local_port, remote_port, fail_on_error=True):

        text = 'ping'

        s = SimpleTcpServer(local_port)
        try:
            s.runThreaded()

            cl = SimpleTcpClient('127.0.0.1', local_port)
            response = cl.send(text).strip()
            if not fail_on_error and text != response:
                return False
            else:
                self.assertEqual(text, response)
            cl.close()

            cr = SimpleTcpClient(remote_host, remote_port)
            response = cr.send(text).strip()
            if not fail_on_error and text != response:
                return False
            else:
                self.assertEqual(text, response)

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

    def test_openport_app_with_http_forward(self):
        port = get_open_port()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--http-forward', '--server', 'test.openport.be',
                              '--manager-port', '-1'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(15)
        process_output = get_all_output(p)
        for out in process_output:
            print 'output: ', out

        self.check_application_is_still_alive(p)

        remote_host = self.getRemoteAddress(process_output[0])

        self.check_http_port_forward(remote_host, port)

    def test_run_run_command_with_timeout(self):
        self.assertEqual(('', ''), run_command_with_timeout(['sleep', '1'], 2))
        self.assertEqual(('', ''), run_command_with_timeout(['sleep', '2'], 1))
        self.assertEqual(('hello\n', ''), run_command_with_timeout(['echo', 'hello'], 1))
        self.assertEqual(('hello\n', ''), run_command_with_timeout(['bash', '-c',  'echo hello; sleep 2'], 1))


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))