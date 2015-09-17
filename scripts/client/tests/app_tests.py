__author__ = 'Jan'
import urllib2
import subprocess
import unittest
import os
import signal
import sys
from time import sleep
import logging
import shutil
import xmlrunner

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services import osinteraction, dbhandler

from test_utils import SimpleTcpServer, SimpleTcpClient, lineNumber, SimpleHTTPClient, TestHTTPServer
from test_utils import run_command_with_timeout, get_remote_host_and_port, kill_all_processes, wait_for_response
from test_utils import print_all_output, click_open_for_ip_link, check_tcp_port_forward
from services.utils import run_method_with_timeout
from services.logger_service import get_logger, set_log_level
from apps import openport_app_version
from apps.app_tcp_server import send_exit, send_ping, is_running

logger = get_logger(__name__)

TEST_SERVER = 'http://test.openport.be'
#TEST_SERVER = 'https://openport.io'

if not osinteraction.is_windows():
    PYTHON_EXE = 'env/bin/python'
    KILL_SIGNAL = signal.SIGKILL
else:
    PYTHON_EXE = 'env\\Scripts\\python.exe'
    KILL_SIGNAL = signal.SIGTERM


class AppTests(unittest.TestCase):
    def setUp(self):
        print self._testMethodName
        set_log_level(logging.DEBUG)
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()
        self.manager_port = -1
        #        self.assertFalse(openportmanager.manager_is_running(8001))
        self.db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'tmp_openport_%s.db' % self._testMethodName)
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except:
                sleep(3)
                os.remove(self.db_file)
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        self.db_handler = dbhandler.DBHandler(self.db_file)

    def tearDown(self):
        logger.debug('teardown!')
        if self.manager_port > 0:
            logger.debug('killing manager')
            self.kill_manager(self.manager_port)
        for session in self.db_handler.get_all_shares():
            send_exit(session)
        kill_all_processes(self.processes_to_kill)
        logger.debug('end of teardown!')

    def get_nr_of_shares_in_db_file(self, db_file):
        db_handler = dbhandler.DBHandler(db_file, init_db=False)
        try:
            return len(db_handler.get_active_shares())
        except:
            return 0

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

        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)

    def test_openport_app__no_arguments(self):
        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        run_method_with_timeout(p.wait, 10)
        output = self.osinteraction.get_all_output(p)
        print output
        self.assertTrue('usage: ' in output[1], output[1])

    def test_openport_app__live_site(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))

#        self.assertFalse(openportmanager.manager_is_running(8001))

        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)
        p.kill()

    def test_save_share(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        share = self.db_handler.get_share_by_local_port(port, filter_active=False)

        self.assertEqual(1, share.id)
        self.assertEqual(remote_host, share.server)
        self.assertEqual(remote_port, share.server_port)
        self.assertEqual(p.pid, share.pid)
        self.assertTrue(share.active)
        self.assertNotEqual(None, share.account_id)
        self.assertNotEqual(None, share.key_id)
        self.assertEqual(port, share.local_port)
        self.assertNotEqual(None, share.server_session_token)
        self.assertEqual('', share.restart_command)
        self.assertFalse(share.http_forward)
        self.assertEqual(None, share.http_forward_address)
        self.assertTrue(share.app_management_port > 1024)
        self.assertEqual(link, share.open_port_for_ip_link)
        self.assertFalse(share.forward_tunnel)
        p.kill()

    def test_save_share__restart_on_reboot(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file, '--restart-on-reboot'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)

        share = self.db_handler.get_share_by_local_port(port, filter_active=False)

        self.assertTrue(share.active)
        self.assertEqual(['%s' % port, '--restart-on-reboot', '--database', self.db_file, '--verbose', '--server',
                          TEST_SERVER], share.restart_command)
        p.kill()

    def test_openport_app__forward_tunnel(self):
        port_out = self.osinteraction.get_open_port()
        p_out = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port_out,  # --verbose,
                                  '--server', TEST_SERVER, '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        self.processes_to_kill.append(p_out)
        remote_host, remote_port, link = get_remote_host_and_port(p_out, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p_out, 'p_out')
        #click_open_for_ip_link(link)
        #check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)

        port_in = self.osinteraction.get_open_port()
        logger.info('port_in: %s' % port_in)
        p_in = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port_in,
                              '--server', TEST_SERVER, '--database', self.db_file, '--forward-tunnel', '--verbose',
                              '--remote-port', str(remote_port)],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_in)
        self.check_application_is_still_alive(p_in)
        self.check_application_is_still_alive(p_out)
        get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)
        self.assertEqual(2, self.get_nr_of_shares_in_db_file(self.db_file))

    def test_openport_app__forward_tunnel__no_local_port_passed(self):
        port_out = self.osinteraction.get_open_port()
        p_out = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port_out,  # --verbose,
                                  '--server', TEST_SERVER, '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        self.processes_to_kill.append(p_out)
        remote_host, remote_port, link = get_remote_host_and_port(p_out, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p_out, 'p_out')

        p_in = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py',
                              '--server', TEST_SERVER, '--database', self.db_file, '--forward-tunnel', '--verbose',
                              '--remote-port', str(remote_port)],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_in)
        self.check_application_is_still_alive(p_in)
        self.check_application_is_still_alive(p_out)
        #self.osinteraction.print_output_continuously_threaded(p_in, 'p_in')
        host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)
        self.assertEqual(2, self.get_nr_of_shares_in_db_file(self.db_file))

    def test_openport_app__forward_tunnel__restart_on_reboot(self):
        port_out = self.osinteraction.get_open_port()
        p_out = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port_out,  # --verbose,
                                  '--server', TEST_SERVER, '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        logger.debug('p_out.pid: %s' % p_out.pid)

        self.processes_to_kill.append(p_out)
        remote_host, remote_port, link = get_remote_host_and_port(p_out, self.osinteraction)
        click_open_for_ip_link(link)
        self.osinteraction.print_output_continuously_threaded(p_out, 'p_out')


        p_in = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py',
                                 '--server', TEST_SERVER, '--database', self.db_file, '--forward-tunnel', '--verbose',
                                 '--remote-port', str(remote_port), '--restart-on-reboot'],
                                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        logger.debug('p_in.pid: %s' % p_in.pid)

        self.processes_to_kill.append(p_in)
        self.check_application_is_still_alive(p_in)
        self.check_application_is_still_alive(p_out)
        #self.osinteraction.print_output_continuously_threaded(p_in, 'p_in')
        host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)
        sleep(2)
        in_session = self.db_handler.get_share_by_local_port(port_in, filter_active=False)
        in_app_management_port = in_session.app_management_port
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)
        self.assertEqual(2, self.get_nr_of_shares_in_db_file(self.db_file))
#
        p_in.terminate()
        logger.debug('p_in wait')
#        p_in.wait()
#        logger.debug('done')
#        #run_method_with_timeout(p_in.wait, 10)
#        self.assertNotEqual(None, p_in.poll())
#        self.assertFalse(check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out,
#                                                remote_port=port_in, fail_on_error=False))
#
#        self.assertEqual(1, len(self.db_handler.get_shares_to_restart()))

        p_restart = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--restart-shares', '--verbose',
                                      '--database', self.db_file],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_restart)
        self.osinteraction.print_output_continuously_threaded(p_restart, 'p_restart')
       # p_restart.communicate()
        logger.debug('p_restart.pid: %s' % p_restart.pid)
        logger.debug('p_restart.wait')
        run_method_with_timeout(p_restart.wait, 10)
       # p_restart.wait()
        logger.debug('p_restart.wait done')

        self.check_application_is_still_alive(p_out)
        logger.debug('alive!')
        check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)

        def foo():
            in_session2 = self.db_handler.get_share_by_local_port(port_in, filter_active=False)
            in_app_management_port2 = in_session2.app_management_port
            # wait for the session to be renewed
            if in_app_management_port == in_app_management_port2:
                return False

            return run_method_with_timeout(is_running, args=[in_session2], timeout_s=5)

        wait_for_response(foo, timeout=10)
        logger.debug('sleeping now')
        #sleep(20)
        logger.debug('wait_for_response done')

        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)

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

    def test_openport_app_get_same_port(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)
        check_tcp_port_forward(self, remote_host, port, remote_port)

        share = self.db_handler.get_share_by_local_port(port)
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

        check_tcp_port_forward(self, new_remote_host, port, new_remote_port)

    def test_openport_app__http_forward(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose',
                              '--http-forward', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction, output_prefix='app', http_forward=True)

        self.check_http_port_forward(remote_host=remote_host, local_port=port)

    def application_is_alive(self, p):
        return run_method_with_timeout(p.poll, 1, raise_exception=False) is None

    def check_application_is_still_alive(self, p):
        if not self.application_is_alive(p):  # process terminated
            print 'application terminated: ', self.osinteraction.get_output(p)
            self.fail('p_app.poll() should be None but was %s' % p.poll())

    def test_exit(self):
        port = self.osinteraction.get_open_port()
        print 'localport :', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER, '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')

        share = self.db_handler.get_share_by_local_port(port)
        send_exit(share, force=True)

        run_method_with_timeout(p_app.wait, 10)
        self.assertTrue(p_app.poll() is not None)

    def test_restart_shares(self):
        port = self.osinteraction.get_open_port()
        print 'localport :', port

        p_app = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--restart-on-reboot', '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print lineNumber(), "remote port:", remote_port
        sleep(1)
        click_open_for_ip_link(link)
        logger.debug('ping')

        self.check_application_is_still_alive(p_app)
        check_tcp_port_forward(self, remote_host, port, remote_port)

        share = self.db_handler.get_share_by_local_port(port)
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
        run_method_with_timeout(p_manager2.wait, 10)

        #self.assertFalse(self.application_is_alive(p_manager2))

        sleep(10)
        # todo: replace by /register

        share = self.db_handler.get_share_by_local_port(port)
        logger.debug(share)
        if 'test.' in share.open_port_for_ip_link:
            share.open_port_for_ip_link = share.open_port_for_ip_link.replace('https', 'http')
        click_open_for_ip_link(share.open_port_for_ip_link)
        logger.debug('pong')

        check_tcp_port_forward(self, remote_host, port, remote_port)

        share = self.db_handler.get_share_by_local_port(port)
        send_exit(share, force=True)
        sleep(5)

        self.assertFalse(check_tcp_port_forward(self, remote_host, port, remote_port, fail_on_error=False))

    def test_openport_app__start_twice(self):
        port = self.osinteraction.get_open_port()
        print 'local port :', port

        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print 'manager_port :', manager_port

        command = [PYTHON_EXE, 'apps/openport_app.py', str(port), '--database', self.db_file, '--verbose', '--server',
                   TEST_SERVER]
        p_app = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        remote_host1, remote_port1, link1 = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')

        p_app2 = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app2)
        def foo():
            command_output = print_all_output(p_app2, self.osinteraction, 'p_app2')
            if command_output[0]:
                return 'Port forward already running for port %s' % port in command_output[0], command_output[0]
            else:
                return False

        wait_for_response(foo)

        run_method_with_timeout(p_app2.wait, 5)
        self.assertFalse(self.application_is_alive(p_app2))

        p_app.kill()
        run_method_with_timeout(p_app.wait, 5)

        p_app3 = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app3)
        sleep(2)
        remote_host3, remote_port3, link3 = get_remote_host_and_port(p_app3, self.osinteraction, output_prefix='app3')
        self.assertEqual(remote_host1, remote_host3)
        self.assertEqual(remote_port1, remote_port3)


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

        # Todo: there still is a problem if the app gets the signal before the tunnel is set up.
        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='p_app')
        self.osinteraction.print_output_continuously_threaded(p_app, 'p_app')
        self.processes_to_kill.append(p_app)

        p_kill = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--kill', str(port),
                                  '--database', self.db_file, '--verbose'],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_kill)
        self.osinteraction.print_output_continuously_threaded(p_kill, 'p_kill')
        run_method_with_timeout(p_kill.wait, 10)
        run_method_with_timeout(p_app.wait, 10)
        self.assertFalse(self.application_is_alive(p_app))

    def test_kill_all(self):
        port = self.osinteraction.get_open_port()
        print 'local port: ', port
        self.assertEqual(0, self.get_nr_of_shares_in_db_file(self.db_file))

        p_app1 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app1)
        get_remote_host_and_port(p_app1, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p_app1, 'p_app1')
        self.assertEqual(1, self.get_nr_of_shares_in_db_file(self.db_file))

        port2 = self.osinteraction.get_open_port()
        print 'local port2: ', port2
        self.assertNotEqual(port, port2)

        p_app2 = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '%s' % port2,
                                  '--verbose', '--server', TEST_SERVER,
                                  '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app2)
        get_remote_host_and_port(p_app2, self.osinteraction)

        for share in self.db_handler.get_active_shares():
            logger.debug(share.local_port)

        self.assertEqual(2, self.get_nr_of_shares_in_db_file(self.db_file))
        p_kill = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--kill-all',
                                  '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p_kill, 'p_kill')
        sleep(3)
        self.processes_to_kill.append(p_kill)
        run_method_with_timeout(p_kill.wait, 10)
        sleep(3)
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
                      '--server', TEST_SERVER,
                      '--database', self.db_file],
                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(2)
        get_remote_host_and_port(p, self.osinteraction)

        print 'pid: %s' % p.pid
        self.osinteraction.kill_pid(p.pid, signal.SIGTERM)
        run_method_with_timeout(p.wait, 10)

        output = self.osinteraction.get_output(p)
        print output[0]
        print output[1]
        # Sadly, this does not work on windows...
        if not osinteraction.is_windows():
            self.assertTrue('got signal ' in output[0])

        self.assertFalse(self.osinteraction.pid_is_running(p.pid))

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
                         run_command_with_timeout([PYTHON_EXE, '-c', 'from time import sleep;sleep(1)'], 2))
        self.assertEqual((False, False),
                         run_command_with_timeout([PYTHON_EXE, '-c', 'from time import sleep;sleep(2)'], 1))
        self.assertEqual(('hello', False), run_command_with_timeout([PYTHON_EXE, '-c', "print 'hello'"], 1))
        self.assertEqual(('hello', False), run_command_with_timeout([PYTHON_EXE, '-c', 'from time import sleep;import sys'
                                                                                     ";print 'hello';sys.stdout.flush()"
                                                                                     ';sleep(2)'], 1))

    def test_shell_behaviour(self):
        p = subprocess.Popen('''%s -c "print 'hello'"''' % PYTHON_EXE, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.assertEqual(('hello', False), self.osinteraction.get_output(p))

        p = subprocess.Popen([PYTHON_EXE, '-c', 'print "hello"'], shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.assertEqual(('hello', False), self.osinteraction.get_output(p))

    def test_open_for_ip_option__False(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                              '--server', TEST_SERVER,
                              '--database', self.db_file, '--ip-link-protection', 'False'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        self.check_application_is_still_alive(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)

        check_tcp_port_forward(self, remote_host, port, remote_port)

    def test_open_for_ip_option__True(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--verbose', '--local-port', '%s' % port,
                              '--server', TEST_SERVER,
                              '--database', self.db_file, '--ip-link-protection', 'True'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        self.check_application_is_still_alive(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)

        self.assertFalse(check_tcp_port_forward(self, remote_host, port, remote_port, fail_on_error=False))
        click_open_for_ip_link(link)
        check_tcp_port_forward(self, remote_host, port, remote_port)

    def test_alembic__0_9_1__new_share(self):
        old_db = os.path.join(os.path.dirname(__file__), 'testfiles/openport-0.9.1.db')
        old_db_tmp = os.path.join(os.path.dirname(__file__), 'testfiles/tmp/openport-0.9.1.db')

        shutil.copy(old_db, old_db_tmp)

        port = self.osinteraction.get_open_port()

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', old_db_tmp],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        db_handler = dbhandler.DBHandler(old_db_tmp)
        session_from_db = db_handler.get_share_by_local_port(port)
        self.assertNotEqual(session_from_db, None)

        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)

    def test_alembic__0_9_1__restart_shares(self):
        pass

    def test_alembic__create_migrations(self):
        return
        old_db = os.path.join(os.path.dirname(__file__), 'testfiles/openport-0.9.1.db')
        old_db_tmp = os.path.join(os.path.dirname(__file__), 'testfiles/tmp/openport-0.9.1.db')

        shutil.copy(old_db, old_db_tmp)

        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--create-migrations', '--verbose', '--database', old_db_tmp],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        run_method_with_timeout(p.wait, 10)
        process_output = print_all_output(p, self.osinteraction, 'list')
        print process_output[0]
        self.assertFalse(process_output[1])

    def test_openport_app__no_errors(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        get_remote_host_and_port(p, self.osinteraction)

        output = print_all_output(p, self.osinteraction)
        self.assertFalse(output[1])
       # self.assertFalse('UserWarning' in output[1])

        p.kill()

    def test_openport_app__restart_on_reboot_app_not_running(self):
        port = self.osinteraction.get_open_port()
        # This app should be restarted
        p = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--restart-on-reboot', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        get_remote_host_and_port(p, self.osinteraction)
        p.kill()

        # This app shouldn't be restarted
        q = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port,
                              '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(q)
        remote_host, remote_port, link = get_remote_host_and_port(q, self.osinteraction)
        output = self.osinteraction.get_all_output(q)

        self.assertTrue('Port forward for port %s that would be restarted on reboot will not be restarted anymore.' % port in output[0])

    def test_hang(self):
        sleep_and_print = '''from time import sleep
for i in range(%s):
    print i
    sleep(1)
print 'Now forwarding remote port test.openport.be:12345 to localhost:555'
print 'to first go here: http://1235.be .'
print 'INFO - You are now connected. You can access the remote pc\\\'s port 7777 on localhost:8888'

for i in range(%s):
    print i
    sleep(1)
    '''
        port_out = self.osinteraction.get_open_port()
        if 1 == 1:
            p_out = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port_out,  # --verbose,
                                    '--server', TEST_SERVER, '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        else:
            p_out = subprocess.Popen([PYTHON_EXE, '-c', sleep_and_print % (3, 60)],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            logger.debug('p_out.pid: %s' % p_out.pid)

        self.processes_to_kill.append(p_out)
        remote_host, remote_port, link = get_remote_host_and_port(p_out, self.osinteraction)
     #   click_open_for_ip_link(link)
        self.osinteraction.print_output_continuously_threaded(p_out, 'p_out')

        sleep(1)
        logger.debug(self.osinteraction.get_output(p_out))

        if 1 == 1:
            if 1 == 1:
                p_in = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py',
                                     '--server', TEST_SERVER, '--database', self.db_file, '--forward-tunnel', '--verbose',
                                     '--remote-port', str(remote_port), '--restart-on-reboot'],
                                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)

            else:
                port_out = self.osinteraction.get_open_port()
                p_in = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--local-port', '%s' % port_out,  # --verbose,
                                    '--server', TEST_SERVER, '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction)



        else:
            p_in = subprocess.Popen([PYTHON_EXE, '-c', sleep_and_print % (3, 60)],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)
        logger.debug('p_in.pid: %s' % p_in.pid)

        self.processes_to_kill.append(p_in)
        self.check_application_is_still_alive(p_in)
        self.check_application_is_still_alive(p_out)


        sleep(1)
        logger.debug(self.osinteraction.get_output(p_in))

      #  sleep(2)
      #  in_session = self.db_handler.get_share_by_local_port(port_in, filter_active=False)
      #  check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)

        p_in.terminate()
        logger.debug('p_in wait')
        run_method_with_timeout(p_in.wait, 10)
        logger.debug('p_in wait done')

        if 1 == 1:
            p_restart = subprocess.Popen([PYTHON_EXE, 'apps/openport_app.py', '--restart-shares', '--verbose',
                                      '--database', self.db_file],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        else:

            p_restart = subprocess.Popen([PYTHON_EXE, '-c', sleep_and_print % (1, 3)],
                                         stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        logger.debug('p_restart started')
        self.processes_to_kill.append(p_restart)
        logger.debug('p_restart continuous print')
        self.osinteraction.print_output_continuously_threaded(p_restart, 'p_restart')
        logger.debug('p_restart.wait')
        #run_method_with_timeout(p_restart.wait, 10)
       # p_restart.communicate()
        logger.debug('p_restart.pid: %s' % p_restart.pid)
        run_method_with_timeout(p_restart.wait, 10)
      #  p_restart.wait()
        logger.debug('p_restart.wait done')

        self.check_application_is_still_alive(p_out)
        logger.debug('alive!')
#        check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)

        def foo():
            return False

        logger.debug('wait for response')
#        wait_for_response(foo, timeout=5)
        logger.debug('sleeping now')
        sleep(1)
        #sleep(20)
        logger.debug('wait_for_response done')

     #   check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)



if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))