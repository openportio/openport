import unittest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from manager.globals import Globals

class GlobalsTests(unittest.TestCase):

    def test_globals(self):
        self.assertEqual(Globals.Instance(), Globals.Instance())