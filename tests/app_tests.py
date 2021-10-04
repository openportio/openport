import json
import logging
import os
import shutil
import signal
import subprocess
import unittest
from pathlib import Path
from unittest import skip
from urllib.error import URLError

import requests
import xmlrunner as xmlrunner
from threading import Thread
from time import sleep

from openport.apps import openport_app_version
from openport.apps.app_tcp_server import send_exit, is_running
from openport.services import osinteraction, dbhandler
from openport.services.logger_service import get_logger, set_log_level
from openport.services.utils import run_method_with_timeout
from tests.test_utils import SimpleTcpServer, SimpleTcpClient, lineNumber, SimpleHTTPClient, TestHTTPServer, get_ip, \
    TEST_FILES_PATH
from tests.test_utils import get_nr_of_shares_in_db_file
from tests.test_utils import print_all_output, click_open_for_ip_link, check_tcp_port_forward
from tests.test_utils import run_command_with_timeout, get_remote_host_and_port, kill_all_processes, wait_for_response

logger = get_logger(__name__)

# TEST_SERVER = 'https://eu.openport.io'
# TEST_SERVER = 'https://openport.io'
TEST_SERVER = 'https://test2.openport.io'
# TEST_SERVER = 'http://127.0.0.1:8000'
# TEST_SERVER = 'https://us.openport.io'
# TEST_SERVER = 'http://192.168.64.2.xip.io'


if not osinteraction.is_windows():
    PYTHON_EXE = subprocess.getoutput('which python')
    KILL_SIGNAL = signal.SIGKILL
else:
    PYTHON_EXE = 'env\\Scripts\\python.exe'
    KILL_SIGNAL = signal.SIGTERM

OPENPORT_APP_FILE = Path(__file__).parents[1] / 'openport' / 'apps' / 'openport_app.py'


class AppTests(unittest.TestCase):
    openport_exe = [PYTHON_EXE, OPENPORT_APP_FILE]
    restart_shares = '--restart-shares'
    kill = '--kill'
    kill_all = '--kill-all'
    version = '--version'
    app_version = openport_app_version.VERSION
    forward = '--forward-tunnel'
    list = '--list'

    def setUp(self):
        logging.getLogger('sqlalchemy').setLevel(logging.WARN)
        print(self._testMethodName)
        set_log_level(logging.DEBUG)
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()
        self.manager_port = -1
        #        self.assertFalse(openportmanager.manager_is_running(8001))
        self.db_file = TEST_FILES_PATH / 'tmp' / f'tmp_openport_{self._testMethodName}.db'
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except:
                sleep(3)
                os.remove(self.db_file)
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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

    def test_aaa_openport_app(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--local-port', str(port),
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        #        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))

        #        self.assertFalse(openportmanager.manager_is_running(8001))

        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)

    @skip("")
    def test_heavy_load(self):
        local_ports = []
        threads = []

        def click_link(p):
            remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction, timeout=60)
            self.check_application_is_still_alive(p)
            click_open_for_ip_link(link)

        for i in range(200):
            port = self.osinteraction.get_open_port()
            local_ports.append(port)
            p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                      '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.processes_to_kill.append(p)
            t = Thread(target=click_link, args=(p,))
            t.daemon = True
            t.start()
            threads.append(t)
        for t in threads:
            t.join(30)

        for local_port in local_ports:
            share = self.db_handler.get_share_by_local_port(local_port)
            check_tcp_port_forward(self, remote_host=share.server, local_port=local_port, remote_port=share.server_port)

    def test_openport_app__daemonize(self):
        if osinteraction.is_mac():
            # does not work on mac-os
            return
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file,
                                                  '--daemonize'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        # self.osinteraction.print_output_continuously(p, '****')
        run_method_with_timeout(p.wait, 3)
        output = self.osinteraction.non_block_read(p)
        for i in output:
            print(i)
        self.assertTrue(output[1] == False or 'Traceback' not in output[1])
        wait_for_response(lambda: get_nr_of_shares_in_db_file(self.db_file) == 1, timeout=10)
        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))
        share = self.db_handler.get_share_by_local_port(port, filter_active=False)
        click_open_for_ip_link(share.open_port_for_ip_link)
        check_tcp_port_forward(self, remote_host=share.server.split('://')[-1], local_port=port,
                               remote_port=share.server_port)

    def test_openport_app__no_arguments(self):
        p = subprocess.Popen(self.openport_exe, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        run_method_with_timeout(p.wait, 10)
        output = self.osinteraction.get_all_output(p)
        print(output)
        all_output = ''.join([str(x) for x in output])
        self.assertTrue('usage: ' in all_output.lower(), all_output)

    def test_openport_app__live_site(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))

        #        self.assertFalse(openportmanager.manager_is_running(8001))

        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)
        p.kill()

    def test_save_share(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        share = self.db_handler.get_share_by_local_port(port, filter_active=False)

        self.assertEqual(1, share.id)
        self.assertEqual(TEST_SERVER, share.server)
        self.assertEqual(remote_port, share.server_port)
        self.assertEqual(p.pid, share.pid)
        self.assertTrue(share.active)
        self.assertNotEqual(None, share.account_id)
        self.assertNotEqual(None, share.key_id)
        self.assertEqual(port, share.local_port)
        self.assertNotEqual(None, share.server_session_token)
        self.assertEqual([], share.restart_command)
        self.assertFalse(share.http_forward)
        self.assertEqual('', share.http_forward_address)
        self.assertTrue(share.app_management_port > 1024)
        self.assertEqual(link, share.open_port_for_ip_link)
        self.assertFalse(share.forward_tunnel)
        p.kill()

    def test_save_share__restart_on_reboot(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + [str(port), '--restart-on-reboot', '--database', str(self.db_file),
                                                  '--verbose', '--server', TEST_SERVER,
                                                  '--ip-link-protection', 'False', '--keep-alive', '5'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)

        share = self.db_handler.get_share_by_local_port(port, filter_active=False)

        self.assertTrue(share.active)
        self.assertEqual(
            [x.encode('utf-8') for x in
             ['%s' % port, '--restart-on-reboot', '--database', str(self.db_file), '--verbose', '--server',
              TEST_SERVER, '--ip-link-protection', 'False', '--keep-alive', '5']],
            share.restart_command)

    def test_save_share__restart_on_reboot__proxy(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + ['%s' % port, '--restart-on-reboot', '--database', str(self.db_file),
                                                  '--verbose', '--server', TEST_SERVER,
                                                  '--proxy', 'socks5://jan:db@1.2.3.4:5555'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(2)

        output = self.osinteraction.non_block_read(p)
        for i in output:
            print(i)
        share = self.db_handler.get_share_by_local_port(port, filter_active=False)
        self.assertEqual(
            [x.encode('utf-8') for x in
             ['%s' % port, '--restart-on-reboot', '--database', str(self.db_file), '--verbose', '--server',
              TEST_SERVER, '--proxy', 'socks5://jan:db@1.2.3.4:5555']],
            share.restart_command)

    def test_save_share__restart_on_reboot__simple(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + [str(port), '--restart-on-reboot',
                                                  '--database', self.db_file,
                                                  '--server', TEST_SERVER,
                                                  ],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        share = self.db_handler.get_share_by_local_port(port, filter_active=False)
        self.assertTrue(share.active)
        self.assertEqual(
            [str(x).encode('utf-8') for x in
             ['%s' % port, '--restart-on-reboot', '--database', self.db_file, '--server',
              TEST_SERVER]], share.restart_command)
        p.kill()

    def test_openport_app__forward_tunnel(self):
        port_out = self.osinteraction.get_open_port()
        p_out = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port_out,  # --verbose,
                                                      '--server', TEST_SERVER, '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        self.processes_to_kill.append(p_out)
        remote_host, remote_port, link = get_remote_host_and_port(p_out, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p_out, 'p_out')
        # click_open_for_ip_link(link)
        # check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)

        port_in = self.osinteraction.get_open_port()
        logger.info('port_in: %s' % port_in)
        p_in = subprocess.Popen(self.openport_exe + [self.forward, '--local-port', '%s' % port_in,
                                                     '--server', TEST_SERVER, '--database', self.db_file,
                                                     '--verbose',
                                                     '--remote-port', str(remote_port)],
                                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_in)
        self.check_application_is_still_alive(p_in)
        self.check_application_is_still_alive(p_out)
        get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)
        self.assertEqual(2, get_nr_of_shares_in_db_file(self.db_file))

    def test_openport_app__forward_tunnel__no_local_port_passed(self):
        port_out = self.osinteraction.get_open_port()
        p_out = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port_out,  # --verbose,
                                                      '--server', TEST_SERVER, '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        self.processes_to_kill.append(p_out)
        remote_host, remote_port, link = get_remote_host_and_port(p_out, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p_out, 'p_out')

        p_in = subprocess.Popen(self.openport_exe + [self.forward,
                                                     '--server', TEST_SERVER, '--database', self.db_file, '--verbose',
                                                     '--remote-port', str(remote_port)],
                                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_in)
        self.check_application_is_still_alive(p_in)
        self.check_application_is_still_alive(p_out)
        # self.osinteraction.print_output_continuously_threaded(p_in, 'p_in')
        host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)
        self.assertEqual(2, get_nr_of_shares_in_db_file(self.db_file))

    def test_openport_app__forward_tunnel__restart_on_reboot(self):
        serving_port = self.osinteraction.get_open_port()
        p_reverse_tunnel = subprocess.Popen(
            self.openport_exe + ['--local-port', '%s' % serving_port,  # --verbose,
                                 '--server', TEST_SERVER, '--database', str(self.db_file)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        logger.debug('p_reverse_tunnel.pid: %s' % p_reverse_tunnel.pid)

        self.processes_to_kill.append(p_reverse_tunnel)
        remote_host, remote_port, link = get_remote_host_and_port(p_reverse_tunnel, self.osinteraction)
        # click_open_for_ip_link(link)
        self.osinteraction.print_output_continuously_threaded(p_reverse_tunnel, 'p_reverse_tunnel')

        forward_port = self.osinteraction.get_open_port()
        p_forward_tunnel = self.start_openport_process([self.forward,
                                                        '--server', TEST_SERVER, '--database', str(self.db_file),
                                                        '--local-port', str(forward_port),
                                                        '--verbose',
                                                        '--remote-port', str(remote_port),
                                                        '--restart-on-reboot'])
        logger.debug('p_forward_tunnel.pid: %s' % p_forward_tunnel.pid)

        self.check_application_is_still_alive(p_forward_tunnel)
        self.check_application_is_still_alive(p_reverse_tunnel)
        # self.osinteraction.print_output_continuously_threaded(p_forward_tunnel, 'p_forward_tunnel')
        host, forwarding_port, link = get_remote_host_and_port(p_forward_tunnel, self.osinteraction,
                                                               forward_tunnel=True)
        self.assertEqual(forward_port, forwarding_port)
        sleep(2)
        forward_session = self.db_handler.get_share_by_local_port(forwarding_port, filter_active=False)
        forward_app_management_port = forward_session.app_management_port
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=serving_port, remote_port=forwarding_port)
        self.assertEqual(2, get_nr_of_shares_in_db_file(self.db_file))
        #
        p_forward_tunnel.terminate()  # on shutdown, ubuntu sends a sigterm
        logger.debug('p_forward_tunnel wait')
        run_method_with_timeout(p_forward_tunnel.wait, 4)
        self.assertFalse(check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=serving_port,
                                                remote_port=forwarding_port, fail_on_error=False))

        self.assertEqual(1, len(self.db_handler.get_shares_to_restart()))

        p_restart = subprocess.Popen(self.openport_exe + [self.restart_shares, '--verbose',
                                                          '--database', self.db_file],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_restart)
        self.osinteraction.print_output_continuously_threaded(p_restart, 'p_restart')

        logger.debug('p_restart.pid: %s' % p_restart.pid)
        logger.debug('p_restart.wait')
        run_method_with_timeout(p_restart.wait, 2)
        # p_restart.wait()
        logger.debug('p_restart.wait done')

        self.check_application_is_still_alive(p_reverse_tunnel)
        logger.debug('alive!')

        # check_tcp_port_forward(self, remote_host=remote_host, local_port=serving_port, remote_port=remote_port)

        def foo():
            in_session2 = self.db_handler.get_share_by_local_port(forwarding_port, filter_active=False)
            if in_session2 is None:
                print('forwarding session not found')
                return False

            print('forwarding session found')
            in_app_management_port2 = in_session2.app_management_port
            # wait for the session to be renewed
            if forward_app_management_port == in_app_management_port2:
                print('still same session')
                return False
            if not in_session2.active:
                print('session not active')
                return False

            return run_method_with_timeout(is_running, args=[in_session2], timeout_s=5)

        wait_for_response(foo, timeout=10)
        logger.debug('sleeping now')
        logger.debug('wait_for_response done')
        check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=serving_port, remote_port=forwarding_port)

    def start_openport_process(self, args):
        print(f'Running {" ".join(self.openport_exe + args)}')
        p_forward_tunnel = subprocess.Popen(
            self.openport_exe + args,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_forward_tunnel)
        return p_forward_tunnel

    def test_openport_app__do_not_restart(self):

        port = self.osinteraction.get_open_port()
        s = SimpleTcpServer(port)
        s.runThreaded()

        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))
        #        self.assertFalse(openportmanager.manager_is_running(8001))

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        os.kill(p.pid, KILL_SIGNAL)
        run_method_with_timeout(p.wait, 10)

        manager_port = self.osinteraction.get_open_port()
        p_manager2 = subprocess.Popen(self.openport_exe + [self.restart_shares, '--database', self.db_file,
                                                           '--verbose', '--manager-port', str(manager_port),
                                                           ],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_manager2)
        run_method_with_timeout(self.application_is_alive, args=[p_manager2], timeout_s=10, raise_exception=False)
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

        p = subprocess.Popen(self.openport_exe + ['%s' % port,
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

        p = subprocess.Popen(self.openport_exe + ['%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        new_remote_host, new_remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        self.assertEqual(remote_port, new_remote_port)
        click_open_for_ip_link(link)

        check_tcp_port_forward(self, new_remote_host, port, new_remote_port)

    def test_openport_app_get_same_port__after_sigint(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + ['%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)
        check_tcp_port_forward(self, remote_host, port, remote_port)

        p.send_signal(signal.SIGINT)
        run_method_with_timeout(p.wait, 10)

        p = subprocess.Popen(self.openport_exe + ['%s' % port,
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

        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose',
                                                  '--http-forward', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction, output_prefix='app',
                                                                  http_forward=True)

        self.check_http_port_forward(remote_host=remote_host, local_port=port)

    def test_openport_app__regular_then_http_forward(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)
        click_open_for_ip_link(link)

        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))

        #        self.assertFalse(openportmanager.manager_is_running(8001))

        return_server = []
        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port,
                               return_server=return_server)
        p.kill()
        for s in return_server:
            s.close()
            print('closed server')
        p.wait()

        c = SimpleTcpClient('localhost', port)

        def server_is_not_active():
            print('checking server_is_not_active')
            try:
                response = c.send('pong').strip()
            except Exception as e:
                logger.exception('this is expected')
                return True
            print(response)
            return response != 'pong'

        wait_for_response(server_is_not_active, timeout=30)
        #        sleep(3)

        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose',
                                                  '--http-forward', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)

        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction, output_prefix='app',
                                                                  http_forward=True)

        self.check_http_port_forward(remote_host=remote_host, local_port=port)

    def application_is_alive(self, p):
        return run_method_with_timeout(p.poll, 1, raise_exception=False) is None

    def check_application_is_still_alive(self, p):
        if not self.application_is_alive(p):  # process terminated
            print('application terminated: ', self.osinteraction.get_output(p))
            self.fail('p_app.poll() should be None but was %s' % p.poll())

    def test_exit(self):
        port = self.osinteraction.get_open_port()
        print('localport :', port)

        p_app = subprocess.Popen(self.openport_exe + ['%s' % port,
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
        print('localport :', port)

        p_app = subprocess.Popen(self.openport_exe + ['%s' % port,
                                                      '--verbose', '--server', TEST_SERVER,
                                                      '--restart-on-reboot', '--database', self.db_file,
                                                      '--ip-link-protection', 'True'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print(lineNumber(), "remote port:", remote_port)
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

        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))

        p_manager2 = subprocess.Popen(self.openport_exe + [self.restart_shares, '--database', self.db_file,
                                                           '--verbose'],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p_manager2, 'p_manager2')
        self.processes_to_kill.append(p_manager2)
        run_method_with_timeout(p_manager2.wait, 10)

        # self.assertFalse(self.application_is_alive(p_manager2))

        sleep(1)
        # todo: replace by /register

        share = self.db_handler.get_share_by_local_port(port)
        logger.debug(share)
        click_open_for_ip_link(share.open_port_for_ip_link)
        logger.debug('pong')

        check_tcp_port_forward(self, remote_host, port, remote_port)

        share = self.db_handler.get_share_by_local_port(port)
        send_exit(share, force=True)
        sleep(1)

        self.assertFalse(check_tcp_port_forward(self, remote_host, port, remote_port, fail_on_error=False))

    def test_openport_app__start_twice(self):
        port = self.osinteraction.get_open_port()
        print('local port :', port)

        manager_port = self.osinteraction.get_open_port()
        self.manager_port = manager_port
        print('manager_port :', manager_port)

        command = self.openport_exe + [str(port), '--database', self.db_file, '--verbose', '--server',
                                       TEST_SERVER]
        print('######app1')
        p_app = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)
        remote_host1, remote_port1, link1 = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        print('######app2')
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

        print('######app3')
        p_app3 = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app3)
        sleep(2)
        remote_host3, remote_port3, link3 = get_remote_host_and_port(p_app3, self.osinteraction, output_prefix='app3')
        self.assertEqual(remote_host1, remote_host3)
        self.assertEqual(remote_port1, remote_port3)

    def test_openport_app__start_trice(self):
        port = self.osinteraction.get_open_port()
        print('local port :', port)
        command = self.openport_exe + [str(port), '--database', self.db_file, '--verbose', '--server',
                                       TEST_SERVER]
        p_app1 = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        self.processes_to_kill.append(p_app1)
        remote_host1, remote_port1, link1 = get_remote_host_and_port(p_app1, self.osinteraction, output_prefix='app')

        p_app2 = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app2)

        def foo(p_app):
            command_output = print_all_output(p_app, self.osinteraction, 'p_app2')
            if command_output[0]:
                return 'Port forward already running for port %s' % port in command_output[0], command_output[0]
            else:
                return False

        wait_for_response(foo, args=[p_app2])
        run_method_with_timeout(p_app2.wait, 5)
        self.assertFalse(self.application_is_alive(p_app2))

        print('######app3')
        p_app3 = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app3)
        wait_for_response(foo, args=[p_app3])
        run_method_with_timeout(p_app3.wait, 5)
        self.assertFalse(self.application_is_alive(p_app3))

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
    #      p_manager2 = subprocess.Popen(self.openport_exe + ['manager', '--database', self.db_file,
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
    #      p_manager2 = subprocess.Popen(self.openport_exe + ['manager', '--database', self.db_file,
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
    #      p_manager2 = subprocess.Popen(self.openport_exe + ['manager', '--database', self.db_file,
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
        print('getRemoteAddress - output:%s' % output)
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
    #     p_app = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
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
        print('local port: ', port)

        p_app = subprocess.Popen(self.openport_exe + ['%s' % port,
                                                      '--verbose', '--server', TEST_SERVER,
                                                      '--listener-port', str(700000),  # port out of reach
                                                      '--database', self.db_file, '--restart-on-reboot'],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app)

        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='app')
        click_open_for_ip_link(link)
        self.check_application_is_still_alive(p_app)
        print(lineNumber(), "remote port:", remote_port)

    def test_kill(self):
        port = self.osinteraction.get_open_port()
        print('local port: ', port)

        p_app = subprocess.Popen(self.openport_exe + ['%s' % port,
                                                      '--verbose', '--server', TEST_SERVER,
                                                      '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        # Todo: there still is a problem if the app gets the signal before the tunnel is set up.
        remote_host, remote_port, link = get_remote_host_and_port(p_app, self.osinteraction, output_prefix='p_app')
        self.osinteraction.print_output_continuously_threaded(p_app, 'p_app')
        self.processes_to_kill.append(p_app)

        p_kill = subprocess.Popen(self.openport_exe + [
            self.kill, str(port),
            '--database', self.db_file, '--verbose'],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_kill)
        self.osinteraction.print_output_continuously_threaded(p_kill, 'p_kill')
        run_method_with_timeout(p_kill.wait, 10)
        run_method_with_timeout(p_app.wait, 10)
        self.assertFalse(self.application_is_alive(p_app))

    def test_kill_all(self):
        port = self.osinteraction.get_open_port()
        print('local port: ', port)
        self.assertEqual(0, get_nr_of_shares_in_db_file(self.db_file))

        p_app1 = subprocess.Popen(self.openport_exe + ['%s' % port,
                                                       '--verbose', '--server', TEST_SERVER,
                                                       '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app1)
        get_remote_host_and_port(p_app1, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p_app1, 'p_app1')
        self.assertEqual(1, get_nr_of_shares_in_db_file(self.db_file))

        port2 = self.osinteraction.get_open_port()
        print('local port2: ', port2)
        self.assertNotEqual(port, port2)

        p_app2 = subprocess.Popen(self.openport_exe + ['%s' % port2,
                                                       '--verbose', '--server', TEST_SERVER,
                                                       '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_app2)
        get_remote_host_and_port(p_app2, self.osinteraction)

        for share in self.db_handler.get_active_shares():
            logger.debug(share.local_port)

        self.assertEqual(2, get_nr_of_shares_in_db_file(self.db_file))
        p_kill = subprocess.Popen(self.openport_exe + [self.kill_all,
                                                       '--database', self.db_file],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p_kill, 'p_kill')
        sleep(1)
        self.processes_to_kill.append(p_kill)
        run_method_with_timeout(p_kill.wait, 10)
        sleep(1)
        self.assertFalse(p_app1.poll() is None)
        self.assertFalse(p_app2.poll() is None)

    def check_http_port_forward(self, remote_host, local_port, remote_port=80):
        s = TestHTTPServer(local_port)
        response = 'echo'
        s.set_response(response)
        s.run_threaded()

        try:
            c = SimpleHTTPClient()
            actual_response = c.get('http://localhost:%s' % local_port)
            self.assertEqual(actual_response, response.strip())
            url = 'http://%s:%s' % (remote_host, remote_port) if remote_port != 80 else 'http://%s' % remote_host
            print('checking url:{}'.format(url))
            try:
                actual_response = c.get(url)
            except Exception as e:
                logger.exception(e)
                self.fail('Http forward failed')
            self.assertEqual(actual_response, response.strip())
            print('http portforward ok')

            url = 'https://%s' % remote_host
            print('checking url:{}'.format(url))
            try:
                actual_response = c.get(url)
            except Exception as e:
                logger.exception(e)
                self.fail('Https forward failed')
            self.assertEqual(actual_response, response.strip())
            print('http portforward ok')
        finally:
            s.stop()

    def kill_manager(self, manager_port):
        url = 'http://localhost:%s/exit' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=1).read()
            if response.strip() != 'ok':
                print(lineNumber(), response)
            else:
                print('manager killed')
        except Exception as detail:
            print(detail)

    def get_share_count_of_manager(self, manager_port):
        url = 'http://localhost:%s/active_count' % manager_port
        logger.debug('sending get request ' + url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req, timeout=1).read()
            return int(response)

        except Exception as detail:
            print('error contacting the manager: %s %s' % (url, detail))
            raise

    def test_kill_openport_app(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--verbose', '--local-port', '%s' % port,
                                                  '--server', TEST_SERVER,
                                                  '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(2)
        get_remote_host_and_port(p, self.osinteraction)

        print('pid: %s' % p.pid)
        self.osinteraction.kill_pid(p.pid, signal.SIGINT)
        run_method_with_timeout(p.wait, 10)

        output = self.osinteraction.get_output(p)
        print(output[0])
        print(output[1])
        # Sadly, this does not work on windows...
        if not osinteraction.is_windows():
            self.assertTrue('got signal ' in str(output[0]).lower())

        self.assertFalse(self.osinteraction.pid_is_running(p.pid))

    def test_remote_kill_stops_application(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        session = self.db_handler.get_share_by_local_port(port)
        data = {'port': session.server_port, 'session_token': session.server_session_token, }
        print(data)
        r = requests.post('{}/api/v1/kill-session'.format(TEST_SERVER),
                          data)
        logger.debug('#########{}'.format(r.text))

        self.assertEqual(200, r.status_code, r.text)
        self.osinteraction.print_output_continuously_threaded(p, 'p')
        run_method_with_timeout(p.wait, 30)
        self.assertFalse(self.osinteraction.pid_is_running(p.pid))

    def test_version(self):
        p = subprocess.Popen(self.openport_exe + [self.version],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        run_method_with_timeout(p.wait, 10)

        process_output = p.communicate()
        for out in process_output:
            print('output: ', out)

        self.assertFalse(self.application_is_alive(p))
        self.assertEqual(self.app_version, process_output[0].decode('utf-8').strip())

    def test_run_run_command_with_timeout(self):
        self.assertEqual((False, False),
                         run_command_with_timeout([PYTHON_EXE, '-c', 'from time import sleep;sleep(1)'], 2))
        self.assertEqual((False, False),
                         run_command_with_timeout([PYTHON_EXE, '-c', 'from time import sleep;sleep(2)'], 1))
        self.assertEqual(('hello', False), run_command_with_timeout([PYTHON_EXE, '-c', "print('hello')"], 1))
        self.assertEqual(('hello', False),
                         run_command_with_timeout([PYTHON_EXE, '-c', 'from time import sleep;import sys'
                                                                     ";print('hello');sys.stdout.flush()"
                                                                     ';sleep(2)'], 1))

    def test_shell_behaviour(self):
        p = subprocess.Popen('''%s -c "print('hello')"''' % PYTHON_EXE, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.assertEqual(('hello', False), self.osinteraction.get_output(p))

        p = subprocess.Popen([PYTHON_EXE, '-c', 'print("hello")'], shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.assertEqual(('hello', False), self.osinteraction.get_output(p))

    def test_open_for_ip_option__False(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--verbose', '--local-port', '%s' % port,
                                                  '--server', TEST_SERVER,
                                                  '--database', self.db_file, '--ip-link-protection', 'False'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        self.check_application_is_still_alive(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.assertIsNone(link)
        check_tcp_port_forward(self, remote_host, port, remote_port)

    def test_open_for_ip_option__True(self):
        port = self.osinteraction.get_open_port()

        p = subprocess.Popen(self.openport_exe + ['--verbose', '--local-port', '%s' % port,
                                                  '--server', TEST_SERVER,
                                                  '--database', self.db_file, '--ip-link-protection', 'True'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        self.check_application_is_still_alive(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)

        self.assertFalse(check_tcp_port_forward(self, remote_host, port, remote_port, fail_on_error=False))
        self.assertIsNotNone(link)

        click_open_for_ip_link(link)
        check_tcp_port_forward(self, remote_host, port, remote_port)

    def check_migration(self, old_db_file, local_port, old_token, old_remote_port):
        old_db = TEST_FILES_PATH / old_db_file
        old_db_tmp = TEST_FILES_PATH / 'tmp' / old_db_file
        shutil.copy(old_db, old_db_tmp)

        port = self.osinteraction.get_open_port()

        http_server = TestHTTPServer(port)
        http_server.run_threaded()

        try:
            server = f"http://localhost:{port}"
            p = subprocess.Popen(self.openport_exe + ['--local-port', str(local_port),
                                                      '--server', server, '--verbose', '--database', old_db_tmp],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.processes_to_kill.append(p)
            wait_for_response(lambda: len(http_server.requests) > 0, timeout=2)
            request = http_server.requests[0]
            self.assertEqual([old_token], request[b'restart_session_token'])
            self.assertEqual([old_remote_port], request[b'request_port'])
        finally:
            http_server.stop()

    def check_migration__restart_sessions(self, old_db_file, local_port, old_token, old_remote_port):
        old_db = TEST_FILES_PATH / old_db_file
        old_db_tmp = TEST_FILES_PATH / 'tmp' / old_db_file
        shutil.copy(old_db, old_db_tmp)

        port = self.osinteraction.get_open_port()

        http_server = TestHTTPServer(port)
        http_server.run_threaded()

        try:
            server = f"http://localhost:{port}"
            p = subprocess.Popen(self.openport_exe + [self.restart_shares,
                                                      '--server', server, '--verbose', '--database', old_db_tmp],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.processes_to_kill.append(p)
            self.osinteraction.print_output_continuously_threaded(p, 'restart_sessions')

            wait_for_response(lambda: len(http_server.requests) > 0, timeout=2)
            request = http_server.requests[0]
            self.assertEqual([old_token], request[b'restart_session_token'])
            self.assertEqual([old_remote_port], request[b'request_port'])
        finally:
            http_server.stop()

    def test_alembic__0_9_1__new_share(self):
        self.check_migration('openport-0.9.1.db', 22, b"gOFZM7vDDcxsqB1P", b"38261")
        self.check_migration__restart_sessions('openport-0.9.1.db', 22, b"gOFZM7vDDcxsqB1P", b"38261")

    def test_db_migrate_from_1_3_0(self):
        self.check_migration('openport-1.3.0.db', 44, b"Me8eHwaze3F6SMS9", b"26541")
        with self.assertRaises(TimeoutError):
            self.check_migration__restart_sessions('openport-1.3.0.db', 44, b"Me8eHwaze3F6SMS9", b"26541")
            subprocess.Popen(self.openport_exe + self.kill_all, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    def test_db_migrate_from_1_3_0__2(self):
        self.check_migration('openport-1.3.0_2.db', 54613, b"DRADXUnvHW9m6FuS", b"15070")
        with self.assertRaises(TimeoutError):
            self.check_migration__restart_sessions('openport-1.3.0_2.db', 54613, b"DRADXUnvHW9m6FuS", b"15070")
            self.kill_all_in_db(TEST_FILES_PATH / 'tmp' / 'openport-1.3.0_2.db')

    def test_db_migrate_from_1_3_0__3(self):
        self.check_migration('openport-1.3.0_3.db', 44, b"FYfS3a05OnkXWNj4", b"42006")
        self.check_migration__restart_sessions('openport-1.3.0_3.db', 44, b"FYfS3a05OnkXWNj4", b"42006")
        self.kill_all_in_db(TEST_FILES_PATH / 'tmp' / 'openport-1.3.0_3.db')

    def kill_all_in_db(self, db_file: Path):
        subprocess.Popen(self.openport_exe + f"{self.kill_all} --database {db_file}".split(), stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)

    def test_restart_command_from_version_0_9_1(self):
        cmd = "22 --restart-on-reboot --request-port 38261 --request-token gOFZM7vDDcxsqB1P --start-manager False " \
              "--manager-port 57738 --server http://localhost:63771 " \
              f"--database {self.db_file}"
        p = subprocess.Popen(
            self.openport_exe + cmd.split(),
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.osinteraction.print_output_continuously_threaded(p)
        self.processes_to_kill.append(p)
        sleep(1)
        self.assertTrue(self.application_is_alive(p))

    @skip
    def test_alembic__create_migrations(self):
        old_db = TEST_FILES_PATH/'openport-0.9.1.db'
        old_db_tmp = TEST_FILES_PATH / 'tmp/openport-0.9.1.db'

        shutil.copy(old_db, old_db_tmp)

        p = subprocess.Popen(
            self.openport_exe + ['--create-migrations', '--verbose', '--database', old_db_tmp],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        run_method_with_timeout(p.wait, 10)
        process_output = print_all_output(p, self.osinteraction, 'list')
        print(process_output[0])
        self.assertFalse(process_output[1])

    def test_openport_app__no_errors(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
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
        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--restart-on-reboot',
                                                  '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        get_remote_host_and_port(p, self.osinteraction)
        p.kill()

        # This app shouldn't be restarted
        q = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(q)
        remote_host, remote_port, link = get_remote_host_and_port(q, self.osinteraction)
        output = self.osinteraction.get_all_output(q)

        self.assertTrue(
            'Port forward for port %s that would be restarted on reboot will not be restarted anymore.' % port in
            output[0])

    def test_hang(self):
        sleep_and_print = '''from time import sleep
for i in range(%s):
    print(i)
    sleep(1)
print('Now forwarding remote port test.openport.be:12345 to localhost:555')
print('to first go here: http://1235.be .')
print('INFO - You are now connected. You can access the remote pc\\\'s port 7777 on localhost:8888')

for i in range(%s):
    print(i)
    sleep(1)
    '''
        port_out = self.osinteraction.get_open_port()
        if 1 == 1:
            p_out = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port_out,  # --verbose,
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
                p_in = subprocess.Popen(self.openport_exe + [self.forward,
                                                             '--server', TEST_SERVER, '--database', self.db_file,
                                                             '--verbose',
                                                             '--remote-port', str(remote_port), '--restart-on-reboot'],
                                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                host, port_in, link = get_remote_host_and_port(p_in, self.osinteraction, forward_tunnel=True)

            else:
                port_out = self.osinteraction.get_open_port()
                p_in = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port_out,  # --verbose,
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
            p_restart = subprocess.Popen(self.openport_exe + [self.restart_shares, '--verbose',
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
        # run_method_with_timeout(p_restart.wait, 10)
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
        # sleep(20)
        logger.debug('wait_for_response done')

    #   check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)

    def test_list(self):
        port = self.osinteraction.get_open_port()
        p = subprocess.Popen(self.openport_exe + ['--local-port', '%s' % port,
                                                  '--server', TEST_SERVER, '--verbose', '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.check_application_is_still_alive(p)

        session = self.db_handler.get_share_by_local_port(port)

        p = subprocess.Popen(self.openport_exe + [self.list, '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p.wait()
        output = p.communicate()
        for i in output:
            print(i)
        self.assertTrue(session.open_port_for_ip_link in output[0].decode('utf-8'))

    def test_auto_restart_on_disconnect(self):
        port = self.osinteraction.get_open_port()
        proxy, proxy_client = self.get_proxy()

        p = subprocess.Popen(self.openport_exe + [str(port), '--restart-on-reboot', '--database', str(self.db_file),
                                                  '--verbose', '--server', TEST_SERVER,
                                                  '--ip-link-protection', 'False', '--keep-alive', '1',
                                                  '--proxy', f'socks5://{proxy}'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.osinteraction.print_output_continuously_threaded(p)

        self.check_application_is_still_alive(p)
        self.assertIsNone(link)
        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)
        proxy_client.disable()
        self.assertFalse(check_tcp_port_forward(self,
                                                remote_host=remote_host,
                                                local_port=port,
                                                remote_port=remote_port,
                                                fail_on_error=False))

        sleep(5)
        proxy_client.enable()
        remote_host, remote_port, link = get_remote_host_and_port(p, self.osinteraction)
        self.assertIsNone(link)
        check_tcp_port_forward(self, remote_host=remote_host, local_port=port, remote_port=remote_port)

    def get_proxy(self):
        import toxiproxy
        # make sure you've run
        # docker-compose -f docker-compose/toxiproxy.yaml up
        server = toxiproxy.Toxiproxy()
        server.destroy_all()
        ip = get_ip()
        return "127.0.0.1:22220", server.create(
            name="socks_proxy", upstream=f"{ip}:1080", enabled=True, listen="0.0.0.0:22220"
        )

    def test_killed_session_not_restarting(self):
        port = self.osinteraction.get_open_port()
        http_server = TestHTTPServer(port)
        http_server.set_response(
            {
                'session_token': "abc",
                'server_ip': "localhost",
                'server_port': 266,  # nobody is listening
                'fallback_ssh_server_ip': "localhost",
                'fallback_ssh_server_port': 226,  # nobody is listening
                'message': "You will not be able to connect, which is expected",
                'account_id': 1,
                'key_id': 1,
                'session_end_time': None,
                'session_max_bytes': 100,
                'session_id': 1,
                'http_forward_address': "",
                'open_port_for_ip_link': "",
            }
        )
        http_server.run_threaded()

        local_port = self.osinteraction.get_open_port()

        try:
            server = f"http://localhost:{port}"
            logger.info(f"local server: {server}")
            p = subprocess.Popen(self.openport_exe + ['--local-port', str(local_port),
                                                      '--server', server, '--verbose', '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.osinteraction.print_output_continuously_threaded(p)

            self.processes_to_kill.append(p)
            wait_for_response(lambda: len(http_server.requests) > 0, timeout=10)

            http_server.set_response(
                {
                    'error': "Session killed",
                    'fatal_error': True,
                }
            )

            wait_for_response(lambda: p.returncode is not None, timeout=20)
        finally:
            http_server.stop()

    def test_app_keeps_retrying_after_invalid_server_response(self):
        port = self.osinteraction.get_open_port()
        http_server = TestHTTPServer(port)
        http_server.set_response(
            {
                'session_token': "abc",
                'server_ip': "localhost",
                'server_port': 266,  # nobody is listening
                'fallback_ssh_server_ip': "localhost",
                'fallback_ssh_server_port': 226,  # nobody is listening
                'message': "You will not be able to connect, which is expected",
                'account_id': 1,
                'key_id': 1,
                'session_end_time': None,
                'session_max_bytes': 100,
                'session_id': 1,
                'http_forward_address': "",
                'open_port_for_ip_link': "",
            }
        )
        http_server.run_threaded()

        local_port = self.osinteraction.get_open_port()

        try:
            server = f"http://localhost:{port}"
            logger.info(f"local server: {server}")
            p = subprocess.Popen(self.openport_exe + ['--local-port', str(local_port),
                                                      '--server', server, '--verbose', '--database', self.db_file],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            self.osinteraction.print_output_continuously_threaded(p)

            self.processes_to_kill.append(p)
            wait_for_response(lambda: len(http_server.requests) > 0, timeout=10)

            http_server.set_response(
                """
                <html>
                <head><title>504 Gateway Time-out</title></head>
                <body bgcolor="white">
                <center><h1>504 Gateway Time-out</h1></center>
                <hr><center>nginx/1.14.2</center>
                </body>
                </html>
                """
            )
            wait_for_response(lambda: len(http_server.requests) > 3, timeout=60)
        finally:
            http_server.stop()



if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
