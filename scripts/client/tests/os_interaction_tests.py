__author__ = 'jan'

import os
import sys
import logging
import threading
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
import xmlrunner
from services.osinteraction import OsInteraction, getInstance, is_windows
import subprocess
from time import sleep
from services.logger_service import set_log_level
from test_utils import run_command_with_timeout, run_command_with_timeout_return_process, run_method_with_timeout
from common.share import Share
from mock import Mock, call


class OsInteractionTest(unittest.TestCase):

    def setUp(self):
        print self._testMethodName
        self.os_interaction = getInstance()
        set_log_level(logging.DEBUG)

    def test_set_variable(self):

        args = ['python', 'openport.py', '--one', '--two', '--three', '3']
        self.assertEqual(['python', 'openport.py', '--one', '--two'], OsInteraction.unset_variable(args, '--three'))
        self.assertEqual(['python', 'openport.py', '--one', '--three', '3'], OsInteraction.unset_variable(args, '--two'))
        self.assertEqual(['python', 'openport.py', '--one', '--two', '--three', '3', '--four', '4'],
                         OsInteraction.set_variable(args, '--four', '4'))
        self.assertEqual(['python', 'openport.py', '--one', '--two', '--three', '3', '--four'],
                         OsInteraction.set_variable(args, '--four'))
        self.assertEqual(['python', 'openport.py', '--one', '--two', '--three', '3', '--four', 'False'],
                         OsInteraction.set_variable(args, '--four', False))
        self.assertEqual(args, OsInteraction.unset_variable(args, '--not-there'))

    def test_get_variable(self):
        self.assertEqual('jan', OsInteraction.get_variable(['sudo', '-u', 'jan', 'ls', 'test'], '-u'))
        self.assertEqual(None, OsInteraction.get_variable(['ls', 'test'], '-u'))
        self.assertEqual('jan', OsInteraction.get_variable(['sudo', '-u', 'jan', 'ls', '-u', 'test'], '-u'))
        self.assertEqual('jan', OsInteraction.get_variable(['sudo', '-u', 'jan'], '-u'))
        self.assertEqual(None, OsInteraction.get_variable(['ls', '-u'], '-u'))

    def test_non_block_read(self):
        # The flush is needed for the tests.
        # See http://stackoverflow.com/questions/6257800/incremental-output-with-subprocess-pipe

        p = subprocess.Popen(['python', '-c', "from time import sleep;import sys; print 'aaa'; sys.stdout.flush(); "
                                              "sleep(1); print 'bbb'"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             bufsize=1, close_fds=not is_windows())
        sleep(0.1)
        self.assertEqual(('aaa', False), self.os_interaction.non_block_read(p))
        sleep(2)
        self.assertEqual(('bbb', False), self.os_interaction.non_block_read(p))
        #todo: close_fds = ON_POSIX ?

    def test_run_command_and_print_output_continuously(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        command = self.os_interaction.get_python_exec()
        print command
        command.extend(['-c', "from time import sleep;import sys; print 'aaa'; sys.stdout.flush(); "
                                              "sleep(1); print 'bbb'"])
        output = self.os_interaction.run_command_and_print_output_continuously(command)
        self.assertEqual(['aaa%sbbb' % os.linesep, False], output)

    def test_run_command_and_print_output_continuously__kill_app(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        command = self.os_interaction.get_python_exec()
        print command
        command.extend(['-c', "from time import sleep;import sys; print 'aaa'; sys.stdout.flush(); "
                                              "sleep(5); print 'bbb'"])
        s = run_command_with_timeout_return_process(command, 1)
        sleep(1.5)
        output = self.os_interaction.print_output_continuously(s)
        self.assertEqual(['aaa', False], output)

    def test_get_all_output__kill_app(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        command = self.os_interaction.get_python_exec()
        print command
        command.extend(['-c', "from time import sleep;import sys; print 'aaa'; sys.stdout.flush(); "
                                              "sleep(3); print 'bbb'"])
        output = run_command_with_timeout(command, 1)
        self.assertEqual(('aaa', False), output)

    def test_get_all_output__simple(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        command = self.os_interaction.get_python_exec()
        print command
        command.extend(['-c', "print 'hello'"])
        output = run_command_with_timeout(command, 1)
        self.assertEqual(('hello', False), output)

    def test_get_all_output__stderr(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        command = self.os_interaction.get_python_exec()
        command.extend(['-c', "import sys; sys.stderr.write('hello_err')"])
        output = run_command_with_timeout(command, 1)
        self.assertEqual((False, 'hello_err'), output)

    def test_pid_is_running(self):
        command = self.os_interaction.get_python_exec()
        command.extend(['-c', "print 'hello'"])
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                   shell=is_windows(),
                                   close_fds=not is_windows())
        process.wait()
        self.assertFalse(self.os_interaction.pid_is_running(process.pid))

        command = self.os_interaction.get_python_exec()
        command.extend(['-c', "from time import sleep;sleep(1); print 'hello'"])
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                   shell=is_windows(),
                                   close_fds=not is_windows())
        self.assertTrue(self.os_interaction.pid_is_running(process.pid))

    def test_pid_is_openport_process(self):
        port = self.os_interaction.get_open_port()
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        python_exe = self.os_interaction.get_python_exec()
        p = subprocess.Popen(python_exe + ['apps/openport_app.py', '--local-port', '%s' % port,
                             '--server', 'http://test.openport.be', '--verbose'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            self.assertTrue(self.os_interaction.pid_is_openport_process(p.pid))
        finally:
            p.kill()

    def test_start_openport_process(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        command = ['sudo', '-u', 'pi', '/usr/bin/openport', '2025', '--restart-on-reboot', '--request-port', '31261',
                   '--request-token', 'WkSXfYyksNy4vN2h', '--start-manager', 'False']
        share = Share()
        share.restart_command = command

        method = self.os_interaction.start_process
        self.os_interaction.start_process = Mock(return_value='')
        try:
            self.os_interaction.start_openport_process(share)
            self.os_interaction.start_process.assert_has_calls(
                [call(['env/bin/python', 'apps/openport_app.py', '2025', '--restart-on-reboot', '--request-port',
                       '31261', '--request-token', 'WkSXfYyksNy4vN2h', '--start-manager', 'False'])])
        finally:
            self.os_interaction.start_process = method

    def test_kill_pid(self):
        if not is_windows():
            return
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        python_exe = self.os_interaction.get_python_exec()
        p = subprocess.Popen(python_exe + ['tryouts/signal_test.py'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        sleep(1)

        self.os_interaction.kill_pid(p.pid)

        run_method_with_timeout(p.wait, 2)

        self.assertNotEqual(None, p.poll())
        output = self.os_interaction.get_all_output(p)
        print output[0]
        print output[1]
        if not is_windows():
            self.assertTrue(output[0] and 'got signal' in output[0])

    def test_run_function_with_lock(self):
        x = [0]
        def add_one():
            a = x[0]
            sleep(0.001)
            x[0] = a + 1

        threads = []

        thread_amount = 10  # Setting this number too high will fail the tests because the system cannot generate so much lockfiles
        for i in range(thread_amount):
            t = threading.Thread(target=lambda: self.os_interaction.run_function_with_lock(add_one, 'add_one'))
            t.setDaemon(True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
        self.assertEqual(x[0], thread_amount)

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
