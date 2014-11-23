import unittest
import sys
import xmlrunner
import os
import logging
from time import sleep
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.share import Share
from manager import dbhandler
from services.logger_service import set_log_level
import logging
import threading
from common.config_file_handler import ConfigFileHandler


class ConfigFileHandlerTests(unittest.TestCase):

    def setUp(self):
        print self._testMethodName
        self.config_location = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'config.conf')
        if os.path.exists(self.config_location):
            os.remove(self.config_location)

    def testReadWrite(self):
        config = ConfigFileHandler(self.config_location)
        config.set('testsection', 'testvar', 'testvalue')
        config.set('testsection', 'testvar2', 2)

        config2 = ConfigFileHandler(self.config_location)
        self.assertEqual('testvalue', config2.get('testsection', 'testvar'))
        self.assertEqual(2, config2.get_int('testsection', 'testvar2'))