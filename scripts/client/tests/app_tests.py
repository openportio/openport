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
from test_utils import print_all_output, click_open_for_ip_link, run_method_with_timeout
from services.logger_service import get_logger, set_log_level
from apps import openport_app_version
from apps.app_tcp_server import send_exit
from manager import dbhandler

logger = get_logger(__name__)

TEST_SERVER = 'test.openport.be'

if not osinteraction.is_windows():
    PYTHON_EXE = 'env/bin/python'
    KILL_SIGNAL = signal.SIGKILL
else:
    PYTHON_EXE = 'env/Scripts/python'
    KILL_SIGNAL = signal.SIGTERM


class AppTests(unittest.TestCase):
    def setUp(self):
        print self._testMethodName
        set_log_level(logging.DEBUG)
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()
        self.manager_port = -1
        #        self.assertFalse(openportmanager.manager_is_running(8001))
        self.db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'tmp_openport.db')
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except:
                sleep(3)
                os.remove(self.db_file)
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        dbhandler.db_location = self.db_file
        self.db_handler = dbhandler.getInstance()

    def tearDown(self):
        if self.manager_port > 0:
            self.kill_manager(self.manager_port)
        kill_all_processes(self.processes_to_kill)

    def get_nr_of_shares_in_db_file(self, db_file):
        p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--list',
                                      '--database', db_file],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        run_method_with_timeout(p_manager.wait, 10)
        process_output = print_all_output(p_manager, self.osinteraction, 'list')
        return len(process_output[0].split('\n')) if process_output[0] else 0

    def test_openport_app(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))

#        self.assertFalse(openportmanager.manager_is_running(8001))

        self.check_tcp_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)
        p.kill()

    def test_openport_app__do_not_restart(self):

        port = self.osinteraction.get_open_port()
        s = SimpleTcpServer(port)
        s.runThreaded()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))
#        self.assertFalse(openportmanager.manager_is_running(8001))

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        os.kill(p.pid, KILL_SIGNAL)
        run_method_with_timeout(p.wait, 10)

        manager_port = self.osinteraction.get_open_port()
        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--database', self.db_file,
                                       '--verbose', '--manager-port', str(manager_port), '--restart-shares'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        i = 0
        while i < 10 and self.application_is_alive(p_manager2):
            sleep(1)
            i += 1
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

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        s = SimpleTcpServer(port)
        s.runThreaded()

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()

        share = self.db_handler.get_share_by_local_port(port)[0]
        send_exit(share)
        run_method_with_timeout(p.wait, 10)

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        new_remote_host, new_remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        self.assertEqual(remote_port, new_remote_port)
        click_open_for_ip_link(link)

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
                              '--server', TEST_SERVER, '--verbose',
                              '--http-forward', '--database', self.db_file],
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

        sleep(3)
        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--restart-on-reboot', '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print lineNumber(), "remote port:", remote_port
        click_open_for_ip_link(link)

        self.check_application_is_still_alive(p_app)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()

        share = self.db_handler.get_share_by_local_port(port)[0]
        send_exit(share, force=True)

        run_method_with_timeout(p_app.wait, 10)
        self.assertTrue(p_app.poll() is not None)

        print_all_output(p_app, self.osinteraction, 'p_app')

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))

        p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--database', self.db_file,
                                       '--verbose', '--restart-shares'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p_manager2, 'p_manager2')
        self.processes_to_kill.append(p_manager2)
        run_method_with_timeout(p_manager2.wait, 5)

        self.assertFalse(self.application_is_alive(p_manager2))

        sleep(30)
        # todo: replace by /register

        share = self.db_handler.get_share_by_local_port(port)[0]
        click_open_for_ip_link(share.open_port_for_ip_link)

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

        share = self.db_handler.get_share_by_local_port(port)[0]
        send_exit(share, force=True)
        run_method_with_timeout(p_manager2.wait, 10)
        print_all_output(p_manager2, self.osinteraction, 'p_manager2')

        response = c.send(request)
        self.assertNotEqual(request, response.strip())

        c.close()
        s.close()

    def test_openport_app__start_twice(self):
        port = self.osinteraction.get_open_port()
        print 'localport :', port

        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print 'manager_port :', manager_port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', str(port), '--database', self.db_file,
                                  '--verbose'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        sleep(3)
        p_app2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', str(port), '--database', self.db_file,
                                   '--verbose'],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app2)
        sleep(2)
        command_output = print_all_output(p_app2, self.osinteraction, 'p_app2')

        self.assertNotEqual(False, command_output[0])
        self.assertTrue('Port forward already running for port %s' % port in command_output[0])
        self.assertFalse(self.application_is_alive(p_app2))
        run_method_with_timeout(p_app2.wait, 5)

    def write_to_conf_file(self, section, option, value):
        import ConfigParser

        config = ConfigParser.ConfigParser()
        config_location = os.path.expanduser('~/.openport/openport.cfg')
        config.read(config_location)
        config.set(section, option, value)
        with open(config_location, 'w') as f:
            config.write(f)

  #  def test_manager__other_tcp_app_on_port(self):
  #      manager_port = self.osinteraction.get_open_port()
  #      self.manager_port = manager_port
  #      s = SimpleTcpServer(manager_port)
  #      s.runThreaded()
#
  #      print 'manager_port :', manager_port
  #      self.write_to_conf_file('manager', 'port', manager_port)
#
  #      p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
  #                                     '--verbose'],
  #                                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
  #      self.processes_to_kill.append(p_manager2)
  #      sleep(2)
  #      command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')
#
  #      self.assertNotEqual(False, command_output[0])
  #      self.assertTrue('Manager is now running on port' in command_output[0])
  #      self.assertTrue(self.application_is_alive(p_manager2))
#
  #      s.close()
#
  #  def test_manager__other_tcp_app_on_port__pass_by_argument(self):
  #      manager_port = self.osinteraction.get_open_port()
  #      self.manager_port = manager_port
  #      s = SimpleTcpServer(manager_port)
  #      s.runThreaded()
#
  #      print 'manager_port :', manager_port
#
  #      p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
  #                                     '--verbose', '--manager-port', str(manager_port)],
  #                                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
  #      self.processes_to_kill.append(p_manager2)
  #      sleep(2)
  #      command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')
#
  #      self.assertNotEqual(False, command_output[0])
  #      self.assertTrue('Manager is now running on port' in command_output[0])
  #      self.assertTrue(self.application_is_alive(p_manager2))
#
  #      s.close()
#
  #  def test_manager__other_http_app_on_port(self):
  #      manager_port = self.osinteraction.get_open_port()
  #      self.manager_port = manager_port
  #      s = TestHTTPServer(manager_port)
  #      s.reply('hello')
  #      s.runThreaded()
#
  #      print 'manager_port :', manager_port
  #      self.write_to_conf_file('manager', 'port', manager_port)
#
  #      p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
  #                                     '--verbose'],
  #                                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
  #      self.processes_to_kill.append(p_manager2)
  #      sleep(2)
  #      command_output = print_all_output(p_manager2, self.osinteraction, 'p_manager2')
#
  #      self.assertNotEqual(False, command_output[0])
  #      self.assertTrue('Manager is now running on port' in command_output[0])
  #      self.assertTrue(self.application_is_alive(p_manager2))
#
  #      s.stop()

    def getRemoteAddress(self, output):
        print 'getRemoteAddress - output:%s' % output
        import re

        m = re.search(r'Now forwarding remote address ([a-z\\.]*) to localhost', output)
        if m is None:
            raise Exception('address not found in output: %s' % output)
        return m.group(1)

    # def test_openport_app_start_manager(self):
    #     manager_port = self.osinteraction.get_open_port()
    #     self.manager_port = manager_port
    #     print 'manager port: ', manager_port
    #     self.assertFalse(openportmanager.manager_is_running(manager_port))
    #
    #     port = self.osinteraction.get_open_port()
    #     print 'local port: ', port
    #
    #     p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
    #                               '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
    #                               '--database', self.db_file, '--restart-on-reboot'],
    #                              stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #     self.processes_to_kill.append(p_app)
    #
    #     remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
    #     print lineNumber(), "remote port:", remote_port
    #     click_open_for_ip_link(link)
    #
    #     self.check_application_is_still_alive(p_app)
    #
    #     self.assertTrue(openportmanager.manager_is_running(manager_port))
    #
    #     os.kill(p_app.pid, KILL_SIGNAL)
    #     run_method_with_timeout(p_app.wait, 10)
    #     sleep(1)
    #     self.assertTrue(openportmanager.manager_is_running(manager_port))
    #     self.kill_manager(manager_port)
    #     sleep(5)
    #     self.assertFalse(openportmanager.manager_is_running(manager_port))

    def test_openport_app__cannot_reach_manager(self):
        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--listener-port', str(700000),  # port out of reach
                                  '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        click_open_for_ip_link(link)
        self.check_application_is_still_alive(p_app)
        print lineNumber(), "remote port:", remote_port

    def test_kill(self):
        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p_app, 'p_app')
        self.processes_to_kill.append(p_app)
        sleep(3)

        p_kill = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--kill', str(port),
                                  '--database', self.db_file, '--restart-on-reboot'],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_kill)
        self.osinteraction.print_output_continuously_threaded(p_kill, 'p_kill')
        run_method_with_timeout(p_kill.wait, 10)
        sleep(1)
        self.assertFalse(p_app.poll() is None)

    def test_kill_all(self):
        port = self.osinteraction.get_open_port()
        print 'local port: ', port

        p_app1 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app1)
        self.osinteraction.print_output_continuously_threaded(p_app1, 'p_app1')

        port2 = self.osinteraction.get_open_port()
        print 'local port2: ', port2
        self.assertNotEqual(port, port2)

        p_app2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port2,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app2)
        get_remote_host_and_port(p_app2, self.osinteraction)
        sleep(1)
        self.assertEqual(2, self.get_nr_of_shares_in_db_file(self.db_file))
        p_kill = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--kill-all',
                                  '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p_kill, 'p_kill')
        sleep(3)
        self.processes_to_kill.append(p_kill)
        run_method_with_timeout(p_kill.wait, 10)
        self.assertFalse(p_app1.poll() is None)
        self.assertFalse(p_app2.poll() is None)

    # def test_restart_manager_on_different_port(self):
    #     manager_port = self.osinteraction.get_open_port()
    #     print 'manager port: ', manager_port
    #     self.manager_port = manager_port
    #     self.assertFalse(openportmanager.manager_is_running(manager_port))
    #
    #     port = self.osinteraction.get_open_port()
    #     print 'local port: ', port
    #
    #     p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
    #                               '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
    #                               '--database', self.db_file, '--restart-on-reboot'],
    #                              stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #     self.processes_to_kill.append(p_app)
    #
    #     remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
    #     print lineNumber(), "remote port:", remote_port
    #     click_open_for_ip_link(link)
    #
    #     self.check_application_is_still_alive(p_app)
    #     sleep(3)
    #     self.assertTrue(openportmanager.manager_is_running(manager_port))
    #     self.assertEqual(1, self.get_share_count_of_manager(manager_port))
    #
    #     self.kill_manager(manager_port)
    #     kill_all_processes(self.processes_to_kill)
    #     i = 0
    #     while self.osinteraction.pid_is_running(p_app.pid) and i < 30:
    #         sleep(1)
    #     self.assertFalse(self.osinteraction.pid_is_running(p_app.pid), 'could not kill the app.')
    #
    #     new_manager_port = self.osinteraction.get_open_port()
    #     print 'new manager port:', new_manager_port
    #     self.assertNotEqual(manager_port, new_manager_port)
    #
    #     p_manager2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
    #                                    '--verbose', '--manager-port', str(new_manager_port),
    #                                    '--server', TEST_SERVER, '--restart-shares'],
    #                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #     self.processes_to_kill.append(p_manager2)
    #     self.manager_port = new_manager_port
    #
    #     sleep(15)
    #     print_all_output(p_manager2, self.osinteraction, 'p_manager2')
    #
    #     self.assertEqual(1, self.get_share_count_of_manager(new_manager_port))
    #
    #     print "http://%s:%s" % (remote_host, remote_port)
    #     failed = False
    #     e = None
    #     try:
    #         self.check_http_port_forward(remote_host=remote_host, local_port=port, remote_port=remote_port)
    #     except Exception as e:
    #         failed = True
    #     sleep(5)
    #
    #     print_all_output(p_manager2, self.osinteraction, 'p_manager2 - final')
    #     if failed:
    #         raise e
    #
    #     self.kill_manager(new_manager_port)
    #     sleep(5)
    #     print_all_output(p_manager2, self.osinteraction, 'p_manager2 - killed')

    # def test_manager_kills_restarted_openport_processes(self):
    #     """ Test to see that the manager kills the jobs it has restarted.
    #     """
    #
    #     # Starting the manager
    #     manager_port = self.osinteraction.get_open_port()
    #     print 'manager port: ', manager_port
    #     self.manager_port = manager_port
    #     self.assertFalse(openportmanager.manager_is_running(manager_port))
    #
    #     p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
    #                                   '--verbose', '--manager-port', str(manager_port), '--server', TEST_SERVER],
    #                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #     self.processes_to_kill.append(p_manager)
    #
    #     sleep(1)
    #     print_all_output(p_manager, self.osinteraction, 'p_manager')
    #
    #     self.assertTrue(openportmanager.manager_is_running(manager_port))
    #
    #     # Starting http server
    #
    #     port = self.osinteraction.get_open_port()
    #     print 'local port: ', port
    #
    #     s = TestHTTPServer(port)
    #     s.reply('echo')
    #     s.runThreaded()
    #
    #     # Starting openport session
    #
    #     p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
    #                               '--verbose', '--server', TEST_SERVER, '--manager-port', str(manager_port),
    #                               '--http-forward', '--database', self.db_file, '--restart-on-reboot'],
    #                              stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #     self.processes_to_kill.append(p_app)
    #     print "p_app pid:", p_app.pid
    #     sleep(10)
    #
    #     # Checking that everything is still running.
    #
    #     print_all_output(p_manager, self.osinteraction, 'p_manager')
    #
    #     self.assertEqual(1, self.get_share_count_of_manager(manager_port))
    #     process_output = print_all_output(p_app, self.osinteraction, 'p_app')
    #
    #     remote_host = self.getRemoteAddress(process_output[0])
    #     sleep(10)
    #
    #     # Checking the connection.
    #
    #     cr = SimpleHTTPClient()
    #     try:
    #         url = 'http://' + remote_host
    #         print 'url=' + url
    #         self.assertEqual('echo', cr.get(url))
    #     except Exception, e:
    #         tr = traceback.format_exc()
    #         logger.error(e)
    #         logger.error(tr)
    #         self.fail('first port forwarding failed')
    #
    #     # Killing the manager
    #
    #     if not osinteraction.is_windows():
    #         self.osinteraction.kill_pid(p_manager.pid, signal.SIGINT)
    #     else:
    #         self.kill_manager(manager_port)
    #     sleep(3)
    #     print_all_output(p_manager, self.osinteraction, 'p_manager')
    #
    #     self.assertFalse(openportmanager.manager_is_running(manager_port))
    #
    #     # Checking that the connection is down.
    #
    #     try:
    #         self.assertEqual('echo', cr.get(url, print500=False))
    #         self.fail('expecting an exception')
    #     except AssertionError:
    #         raise
    #     except:
    #         pass
    #
    #     if not osinteraction.is_windows():
    #         run_method_with_timeout(p_app.communicate, 2, raise_exception=False)
    #
    #     self.assertFalse(self.osinteraction.pid_is_running(p_app.pid))
    #
    #     # Restarting manager, should restart port-forwarding app
    #
    #     p_manager = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', 'manager', '--database', self.db_file,
    #                                   '--verbose', '--manager-port', str(manager_port), '--server', TEST_SERVER,
    #                                   '--restart-shares'],
    #                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #     self.processes_to_kill.append(p_manager)
    #
    #     sleep(25)
    #     process_output = print_all_output(p_manager, self.osinteraction, 'p_manager')
    #
    #     self.assertTrue(openportmanager.manager_is_running(manager_port))
    #     self.assertEqual(1, self.get_share_count_of_manager(manager_port))
    #
    #     # Checking that http server is still running
    #
    #     local_url = 'http://127.0.0.1:%s' % port
    #     try:
    #         self.assertEqual('echo', cr.get(local_url))
    #     except Exception, e:
    #         logger.exception(e)
    #         self.fail('calling local port failed')
    #
    #     print "url2: %s" % url
    #     wait_for_success_callback(p_manager, self.osinteraction, output_prefix='p_manager')
    #
    #     # Checking that the openport session has restarted.
    #
    #     try:
    #         self.assertEqual('echo', cr.get(url, print500=False))
    #     except Exception, e:
    #         logger.exception(e)
    #         self.fail('second port forwarding failed')
    #
    #     # Killing the manager should also kill the app
    #
    #     if not osinteraction.is_windows():
    #         self.osinteraction.kill_pid(p_manager.pid, signal.SIGINT)
    #     else:
    #         self.kill_manager(manager_port)
    #
    #     sleep(3)
    #
    #     print_all_output(p_manager, self.osinteraction, 'p_manager')
    #
    #     self.assertFalse(openportmanager.manager_is_running(manager_port))
    #
    #     # Checking that the openport session has ended.
    #
    #     try:
    #         self.assertEqual('echo', cr.get(url, print500=False))
    #         self.fail('expecting an exception')
    #     except:
    #         pass

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
            else:
                print 'manager killed'
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

    def test_kill_openport_app(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                      '--http-forward', '--server', TEST_SERVER,
                      '--database', self.db_file],
                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(2)
        self.osinteraction.kill_pid(p.pid, signal.SIGTERM)
        sleep(5)
        output = self.osinteraction.get_all_output(p)
        print output[0]
        print output[1]
        # Sadly, this does not work on windows...
        if not osinteraction.is_windows():
            self.assertTrue('got signal ' in output[0])
        self.assertNotEqual(None, p.poll())


    def test_openport_app_with_http_forward(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                              '--http-forward', '--server', TEST_SERVER,
                              '--database', self.db_file],
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
        run_method_with_timeout(p.wait, 10)

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