__author__ = 'jan'
import sys
import os
import xmlrunner
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from integration_tests import IntegrationTest


class LiveIntegrationTest(IntegrationTest):

    def setUp(self):
        IntegrationTest.setUp(self)
        self.test_server='openport.io'

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))