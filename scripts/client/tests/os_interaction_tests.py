__author__ = 'jan'

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
import xmlrunner
from services.osinteraction import OsInteraction

class IntegrationTest(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
