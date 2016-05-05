__author__ = 'jan'

import os
import sys
import logging
import threading
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
import requests
from services.osinteraction import OsInteraction, getInstance, is_windows
from apps.app_tcp_server import AppTcpServer
import subprocess
from apps.app_tcp_server import is_running
from time import sleep
from services import dbhandler
from test_utils import get_remote_host_and_port
from common.config import OpenportAppConfig


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
            share = self.db_handler.get_share_by_local_port(port)
            self.assertNotEqual(None, share)
            self.assertTrue(is_running(share))
        finally:
            p.kill()

    def test_stop(self):
        config = OpenportAppConfig()
        port = self.os_interaction.get_open_port()

        server = AppTcpServer('localhost', port, config, self.db_handler)
        server.run_threaded()

        r = requests.get('http://localhost:%s/info' % port)
        self.assertEqual('openport', r.text.strip())

        server.stop()

        try:
            r = requests.get('http://localhost:%s/info' % port)
            self.fail('expecting exception')
        except requests.ConnectionError:
            pass