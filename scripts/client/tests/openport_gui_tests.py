import os
import sys
import logging
import wx
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
import xmlrunner
from services.osinteraction import OsInteraction, getInstance, is_windows
import subprocess
from time import sleep
from services.logger_service import set_log_level
from test_utils import run_command_with_timeout, run_command_with_timeout_return_process
from apps.openport_app import OpenportApp
from apps import openport_api
import threading
from manager import dbhandler
from test_utils import set_default_args
from gui.openport_gui import SharesFrame



class OpenportAppTests(unittest.TestCase):
    def setUp(self):
        print self._testMethodName
        self.os_interaction = getInstance()
        set_log_level(logging.DEBUG)
        self.app = OpenportApp()
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'db_test.db')

        self.gui_app = wx.App(False)
        self.gui_frame = SharesFrame(None, -1, ' ', None)
        try:
            os.remove(self.test_db)
        except:
            pass

    def tearDown(self):
        pass

    def test_register_share(self):
        """ Check that if a session_token is denied, the new session token is stored and used. """





        set_default_args(self.app, self.test_db)
        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()






# remove share kills share
# restart shares registers shares
# ...