__author__ = 'jan'

import os
import sys
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
import xmlrunner
from services.osinteraction import OsInteraction, getInstance
import subprocess
from time import sleep
from services.logger_service import set_log_level


class OsInteractionTest(unittest.TestCase):

    def setUp(self):
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

    def test_strip_sudo_command(self):
        self.assertEqual(['ls', 'test'], OsInteraction.strip_sudo_command(['sudo', '-u', 'jan', 'ls', 'test']))
        self.assertEqual(['ls', 'test'], OsInteraction.strip_sudo_command(['sudo', 'ls', 'test']))
        self.assertEqual(['ls', 'test'], OsInteraction.strip_sudo_command(['ls', 'test']))

    def test_get_variable(self):
        self.assertEqual('jan', OsInteraction.get_variable(['sudo', '-u', 'jan', 'ls', 'test'], '-u'))
        self.assertEqual(None, OsInteraction.get_variable(['ls', 'test'], '-u'))
        self.assertEqual('jan', OsInteraction.get_variable(['sudo', '-u', 'jan', 'ls', '-u', 'test'], '-u'))
        self.assertEqual('jan', OsInteraction.get_variable(['sudo', '-u', 'jan'], '-u'))
        self.assertEqual(None, OsInteraction.get_variable(['ls', '-u'], '-u'))

    def test_non_block_read(self):
        p = subprocess.Popen(['python', '-c', "from time import sleep; print 'aaa'; sleep(1); print 'bbb'"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             bufsize=1, close_fds=False)
        self.assertEqual(('aaa', False), self.os_interaction.non_block_read(p))
        sleep(2)
        self.assertEqual(('bbb', False), self.os_interaction.non_block_read(p))
        #todo: close_fds = ON_POSIX ?

    def test_run_command_and_print_output_continuously(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        command = self.os_interaction.get_python_exec()
        print command
        command.extend(['-c', 'from time import sleep; print "aaa"; sleep(3); print "bbb"'])
        output = self.os_interaction.run_command_and_print_output_continuously(command)
        self.assertEqual(['aaa%sbbb' % os.linesep, False], output)

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
