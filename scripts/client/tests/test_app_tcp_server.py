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
from apps.app_tcp_server import is_running
from time import sleep
from services import dbhandler
from test_utils import get_remote_host_and_port


class AppTcpServerTests(unittest.TestCase):
    def setUp(self):
        self.os_interaction = getInstance()
        self.db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'tmp_openport.db')
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except:
                sleep(3)
                os.remove(self.db_file)
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        self.db_handler = dbhandler.DBHandler(self.db_file)

    def test_is_running(self):
        port = self.os_interaction.get_open_port()
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        python_exe = self.os_interaction.get_python_exec()
        p = subprocess.Popen(python_exe + ['apps/openport_app.py', '--local-port', '%s' % port,
                             '--server', 'http://test.openport.be', '--verbose',
                             '--database', self.db_file],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        get_remote_host_and_port(p, self.os_interaction)

        try:
            shares = self.db_handler.get_share_by_local_port(port)
            self.assertEqual(1, len(shares))
            self.assertTrue(is_running(shares[0]))
        finally:
            p.kill()