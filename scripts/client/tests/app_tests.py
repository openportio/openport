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

from services import osinteraction

from test_utils import SimpleTcpServer, SimpleTcpClient, lineNumber, SimpleHTTPClient, TestHTTPServer
from test_utils import run_command_with_timeout, get_remote_host_and_port, kill_all_processes, wait_for_success_callback
from test_utils import print_all_output
from services.logger_service import get_logger, set_log_level
from apps import openport_app_version
from manager import openportmanager

logger = get_logger(__name__)

TEST_SERVER = 'test.openport.be'

if osinteraction.is_linux():
    PYTHON_EXE = 'env/bin/python'
    KILL_SIGNAL = signal.SIGKILL
else:
    PYTHON_EXE = 'env/Scripts/python'
    KILL_SIGNAL = signal.SIGTERM


class AppTests(unittest.TestCase):
    def setUp(self):
        set_log_level(logging.DEBUG)
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()
        self.manager_port = -1
        #        self.assertFalse(openportmanager.manager_is_running(8001))
        self.db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp_openport.db')
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

        os.chdir(os.path.dirname(os.path.dirname(__file__)))


    def tearDown(self):
        kill_all_processes(self.processes_to_kill)
        if self.manager_port > 0:
            self.kill_manager(self.manager_port)

    def get_nr_of_shares_in_db_file(self, db_file):
        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--list',
                                      '--database', db_file],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p_manager.wait()
        process_output = print_all_output(p_manager, self.osinteraction, 'list')
        return len(process_output[0].split('\n')) if process_output[0] else 0

    def test_openport_app(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--no-manager', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))

#        self.assertFalse(openportmanager.manager_is_running(8001))

        self.check_tcp_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)
        p.kill()

    def test_openport_app__do_not_restart(self):

        port = self.osinteraction.get_open_port()
        s = SimpleTcpServer(port)
        s.runThreaded()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--no-manager', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))
#        self.assertFalse(openportmanager.manager_is_running(8001))

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        os.kill(p.pid, KILL_SIGNAL)
        p.wait()

        manager_port = self.osinteraction.get_open_port()
        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose', '--manager-port', str(manager_port), '--restart-shares'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(3)
        print_all_output(p_manager2, self.osinteraction, 'p_manager2')
        self.assertFalse(self.application_is_alive(p_manager2))
        try:
            response = c.send(request)
        except:
            response = ''
        self.assertNotEqual(request, response.strip())
        c.close()
        s.close()

    def test_openport_app_same_port(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--no-manager', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        s = SimpleTcpServer(port)
        s.runThreaded()

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()

        p.kill()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--no-manager', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        new_remote_host, new_remote_port = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        self.assertEqual(remote_port, new_remote_port)

        c = SimpleTcpClient(new_remote_host, new_remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()
        s.close()

        p.kill()

    def test_openport_app_http_forward(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--server', TEST_SERVER, '--verbose',
                              '--no-manager', '--http-forward', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(10)
        process_output = print_all_output(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        remote_host = self.getRemoteAddress(process_output[0])

        self.check_http_port_forward(remote_host=remote_host, local_port=port)
        p.kill()

    def application_is_alive(self, p):
        return p.poll() is None

    def check_application_is_still_alive(self, p):
        if not self.application_is_alive(p):  # process terminated
            print 'application terminated: ', self.osinteraction.get_all_output(p)
            self.fail('p_app.poll() should be None but was %s' % p.poll())

    def test_manager(self):
        port = self.osinteraction.get_open_port()
        print 'localport :', port
        s = SimpleTcpServer(port)
        s.runThreaded()

        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print 'manager_port :', manager_port

        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                      '--verbose', '--manager-port', str(manager_port)],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        sleep(3)
        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
                                  '--restart-on-reboot', '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print lineNumber(), "remote port:", remote_port

        print_all_output(p_manager, self.osinteraction, 'manager')

        self.check_application_is_still_alive(p_manager)
        self.check_application_is_still_alive(p_app)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()
        #     s.close()
        os.kill(p_app.pid, KILL_SIGNAL)
        self.assertNotEqual(p_app.wait(), None)
        while self.osinteraction.pid_is_running(p_app.pid):
            print "waiting for pid to be killed: %s" % p_app.pid
            sleep(1)
        os.kill(p_manager.pid, signal.SIGINT)
        print 'waiting for manager to be killed'
        p_manager.wait()

        print_all_output(p_manager, self.osinteraction, 'p_manager')
        print_all_output(p_app, self.osinteraction, 'p_app')

        sleep(5)

        #      s = SimpleTcpServer(port)
        #      s.runThreaded()

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))

        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose', '--manager-port', str(manager_port), '--restart-shares'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(3)
        i = 0
        while i < 15 and self.get_share_count_of_manager(manager_port) < 1:
            sleep(1)
            i += 1
        self.check_application_is_still_alive(p_manager2)
        print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        self.assertEqual(1, self.get_share_count_of_manager(manager_port))

        wait_for_success_callback(p_manager2, self.osinteraction)

        c = SimpleTcpClient(remote_host, remote_port)
        cl = SimpleTcpClient('127.0.0.1', port)
        request = 'hello'
        try:
            response = cl.send(request)
        except:
            self.fail('local share has not been restarted')
        self.assertEqual(request, response.strip(), 'getting response locally failed')

        try:
            response = c.send(request)
        except:
            self.fail('remote share has not been restarted')
        self.assertEqual(request, response.strip(), 'getting response through proxy failed')

        os.kill(p_manager2.pid, signal.SIGINT)
        p_manager2.wait()
        print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        response = c.send(request)
        self.assertNotEqual(request, response.strip())

        c.close()
        s.close()

    def test_manager__stop_if_no_shares(self):
        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print 'manager_port :', manager_port

        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                      '--verbose', '--manager-port', str(manager_port), '--restart-shares'],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        sleep(3)
        print_all_output(p_manager, self.osinteraction)
        self.assertFalse(self.application_is_alive(p_manager))

    def test_manager__start_twice(self):
        port = self.osinteraction.get_open_port()
        print 'localport :', port


        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print 'manager_port :', manager_port

        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                      '--verbose', '--manager-port', str(manager_port)],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        sleep(3)
        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose', '--manager-port', str(manager_port)],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(2)
        command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        self.assertNotEqual(False, command_output[0])
        self.assertTrue('Manager is already running on port' in command_output[0])
        self.assertFalse(self.application_is_alive(p_manager2))

    def write_to_conf_file(self, section, option, value):
        import ConfigParser

        config = ConfigParser.ConfigParser()
        config_location = os.path.expanduser('~/.openport/openport.cfg')
        config.read(config_location)
        config.set(section, option, value)
        with open(config_location, 'w') as f:
            config.write(f)

    def test_manager__other_tcp_app_on_port(self):
        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        s = SimpleTcpServer(manager_port)
        s.runThreaded()

        print 'manager_port :', manager_port
        self.write_to_conf_file('manager', 'port', manager_port)

        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(2)
        command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        self.assertNotEqual(False, command_output[0])
        self.assertTrue('Manager is now running on port' in command_output[0])
        self.assertTrue(self.application_is_alive(p_manager2))

        s.close()

    def test_manager__other_tcp_app_on_port__pass_by_argument(self):
        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        s = SimpleTcpServer(manager_port)
        s.runThreaded()

        print 'manager_port :', manager_port

        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose', '--manager-port', str(manager_port)],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(2)
        command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        self.assertNotEqual(False, command_output[0])
        self.assertTrue('Manager is now running on port' in command_output[0])
        self.assertTrue(self.application_is_alive(p_manager2))

        s.close()

    def test_manager__other_http_app_on_port(self):
        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        s = TestHTTPServer(manager_port)
        s.reply('hello')
        s.runThreaded()

        print 'manager_port :', manager_port
        self.write_to_conf_file('manager', 'port', manager_port)

        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        sleep(2)
        command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        self.assertNotEqual(False, command_output[0])
        self.assertTrue('Manager is now running on port' in command_output[0])
        self.assertTrue(self.application_is_alive(p_manager2))

        s.stop()

    def getRemoteAddress(self, output):
        print 'getRemoteAddress - output:%s' % output
        import re

        m = re.search(r'Now forwarding remote address ([a-z\\.]*) to localhost', output)
        if m is None:
            raise Exception('address not found in output: %s' % output)
        return m.group(1)

    def test_openport_app_start_manager(self):
        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print 'manager port: ', manager_port
        self.assertFalse(openportmanager.manager_is_running(manager_port))

        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
                                  '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print lineNumber(), "remote port:", remote_port

        self.check_application_is_still_alive(p_app)

        self.assertTrue(openportmanager.manager_is_running(manager_port))

        os.kill(p_app.pid, KILL_SIGNAL)
        p_app.wait()
        sleep(1)
        self.assertTrue(openportmanager.manager_is_running(manager_port))
        self.kill_manager(manager_port)
        sleep(5)
        self.assertFalse(openportmanager.manager_is_running(manager_port))

    def test_openport_app__cannot_reach_manager(self):
        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--manager-port', str(700000),  # port out of reach
                                  '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        self.check_application_is_still_alive(p_app)
        print lineNumber(), "remote port:", remote_port

    def test_restart_manager_on_different_port(self):
        manager_port = self.osinteraction.get_open_port()
        print 'manager port: ', manager_port
        self.manager_port = manager_port
        self.assertFalse(openportmanager.manager_is_running(manager_port))

        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
                                  '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print lineNumber(), "remote port:", remote_port

        self.check_application_is_still_alive(p_app)
        self.assertTrue(openportmanager.manager_is_running(manager_port))
        self.assertEqual(1, self.get_share_count_of_manager(manager_port))

        self.kill_manager(manager_port)
        kill_all_processes(self.processes_to_kill)
        i = 0
        while self.osinteraction.pid_is_running(p_app.pid) and i < 30:
            sleep(1)
        self.assertFalse(self.osinteraction.pid_is_running(p_app.pid), 'could not kill the app.')

        new_manager_port = self.osinteraction.get_open_port()
        print 'new manager port:', new_manager_port
        self.assertNotEqual(manager_port, new_manager_port)

        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                       '--verbose', '--manager-port', str(new_manager_port),
                                       '--server', TEST_SERVER, '--restart-shares'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        self.manager_port = new_manager_port

        sleep(15)
        print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        self.assertEqual(1, self.get_share_count_of_manager(new_manager_port))

        print "http://%s:%s" % (remote_host, remote_port)
        failed = False
        e = None
        try:
            self.check_http_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)
        except Exception as e:
            failed = True
        sleep(5)

        print_all_output(p_manager2, self.osinteraction, 'p_manager2 - final')
        if failed:
            raise e

        os.kill(p_manager2.pid, signal.SIGINT)
        sleep(5)
        print_all_output(p_manager2, self.osinteraction, 'p_manager2 - killed')

    def test_manager_kills_restarted_openport_processes(self):
        """ Test to see that the manager kills the jobs it has restarted.
        """

        # Starting the manager
        manager_port = self.osinteraction.get_open_port()
        print 'manager port: ', manager_port
        self.manager_port = manager_port
        self.assertFalse(openportmanager.manager_is_running(manager_port))

        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                      '--verbose', '--manager-port', str(manager_port), '--server', TEST_SERVER],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)

        sleep(1)
        print_all_output(p_manager, self.osinteraction, 'p_manager')

        self.assertTrue(openportmanager.manager_is_running(manager_port))

        # Starting http server

        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        s = TestHTTPServer(port)
        s.reply('echo')
        s.runThreaded()

        # Starting openport session

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
                                  '--http-forward', '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        print "p_app pid:", p_app.pid
        sleep(10)

        # Checking that everything is still running.

        print_all_output(p_manager, self.osinteraction, 'p_manager')

        self.assertEqual(1, self.get_share_count_of_manager(manager_port))
        process_output = print_all_output(p_app, self.osinteraction, 'p_app')

        remote_host = self.getRemoteAddress(process_output[0])
        sleep(10)

        # Checking the connection.

        cr = SimpleHTTPClient()
        try:
            url = 'http://' + remote_host
            print 'url=' + url
            self.assertEqual('echo', cr.get(url))
        except Exception, e:
            tr = traceback.format_exc()
            logger.error(e)
            logger.error(tr)
            self.fail('first port forwarding failed')

        # Killing the manager

        self.osinteraction.kill_pid(p_manager.pid, signal.SIGINT)
        sleep(3)
        print_all_output(p_manager, self.osinteraction, 'p_manager')

        self.assertFalse(openportmanager.manager_is_running(manager_port))

        # Checking that the connection is down.

        try:
            self.assertEqual('echo', cr.get(url, print500=False))
            self.fail('expecting an exception')
        except:
            pass
        print p_app.communicate()
        self.assertFalse(self.osinteraction.pid_is_running(p_app.pid))

        # Restarting manager, should restart port-forwarding app

        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
                                      '--verbose', '--manager-port', str(manager_port), '--server', TEST_SERVER,
                                      '--restart-shares'],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager)

        sleep(25)
        process_output = print_all_output(p_manager, self.osinteraction, 'p_manager')

        self.assertTrue(openportmanager.manager_is_running(manager_port))
        self.assertEqual(1, self.get_share_count_of_manager(manager_port))

        # Checking that http server is still running

        local_url = 'http://127.0.0.1:%s' % port
        try:
            self.assertEqual('echo', cr.get(local_url))
        except Exception, e:
            tr = traceback.format_exc()
            logger.error(e)
            logger.error(tr)
            self.fail('calling local port failed')

        print "url2: %s" % url
        sleep(15)

        print_all_output(p_manager, self.osinteraction, 'p_manager')

        # Checking that the openport session has restarted.

        try:
            self.assertEqual('echo', cr.get(url, print500=False))
        except Exception, e:
            tr = traceback.format_exc()
            logger.error(e)
            logger.error(tr)
            self.fail('second port forwarding failed')

        # Killing the manager should also kill the app

        self.osinteraction.kill_pid(p_manager.pid, signal.SIGINT)
        sleep(1)

        print_all_output(p_manager, self.osinteraction, 'p_manager')

        self.assertFalse(openportmanager.manager_is_running(manager_port))

        # Checking that the openport session has ended.

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

    def test_openport_app_with_http_forward(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                              '--start-manager', 'False', '--http-forward', '--server', TEST_SERVER,
                              '--no-manager', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(15)
        process_output = print_all_output(p, self.osinteraction)

        self.check_application_is_still_alive(p)

        remote_host = self.getRemoteAddress(process_output[0])

        self.check_http_port_forward(remote_host, port)

    def test_version(self):
        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--version'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        p.wait()

        process_output = p.communicate()
        for out in process_output:
            print 'output: ', out

        self.assertFalse(self.application_is_alive(p))
        self.assertEqual(openport_app_version.VERSION, process_output[1].strip())


    def test_run_run_command_with_timeout(self):
        self.assertEqual((False, False),
                         run_command_with_timeout(['python', '-c', 'from time import sleep;sleep(1)'], 2))
        self.assertEqual((False, False),
                         run_command_with_timeout(['python', '-c', 'from time import sleep;sleep(2)'], 1))
        self.assertEqual(('hello', False), run_command_with_timeout(['python', '-c', "print 'hello'"], 1))
        self.assertEqual(('hello', False), run_command_with_timeout(['python', '-c', 'from time import sleep;import sys'
                                                                                     ";print 'hello';sys.stdout.flush()"
                                                                                     ';sleep(2)'], 1))

    def test_shell_behaviour(self):
        p = subprocess.Popen('''python -c "print 'hello'"''', shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.assertEqual(('hello', False), self.osinteraction.get_all_output(p))

        p = subprocess.Popen(['python', '-c', 'print "hello"'], shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.assertEqual(('hello', False), self.osinteraction.get_all_output(p))


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))