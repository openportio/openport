__author__ = 'jan'

import os
import sys
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
import xmlrunner
from services.osinteraction import OsInteraction, getInstance, is_linux
import subprocess
from time import sleep
from services.logger_service import set_log_level
from test_utils import run_command_with_timeout, run_command_with_timeout_return_process
from apps.openport_app import OpenportApp
from apps import openport_api
import threading
from manager import dbhandler

class OpenportAppTests(unittest.TestCase):

    def setUp(self):
        self.os_interaction = getInstance()
        set_log_level(logging.DEBUG)
        self.app = OpenportApp()
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'db_test.db')
        try:
            os.remove(self.test_db)
        except:
            pass
        self.stop_port_forward = False

    def tearDown(self):

        self.stop_port_forward = True

    def set_default_args(self, app):
        app.args.local_port = -1
        app.args.register_key = ''
        app.args.port = -1
        app.args.manager = -1

        app.args.manager_port = 8001
        app.args.start_manager = True
        app.args.database = self.test_db
        app.args.request_port = -1
        app.args.request_token = ''
        app.args.verbose = True
        app.args.http_forward = False
        app.args.server = 'testserver.jdb'
        app.args.restart_on_reboot = False
        app.args.no_manager = False



    def test_request_same_port_if_old_port_is_denied(self):
        """ Check that if a session_token is denied, the new session token is stored and used. """

        self.set_default_args(self.app)

        this_test = self
        this_test.raise_exception = False

        this_test.received_session = None
        this_test.received_success_callback = None
        this_test.received_error_callback = None
        this_test.received_server = None

        this_test.returning_token = 'first token'
        this_test.received_token = None

        this_test.returning_server_port = 1111
        this_test.received_server_port = None

        def extra_function(session):
            pass

        def fake_start_port_forward(session, callback=None, error_callback=None, server=None):
            this_test.received_session = session
            this_test.received_success_callback = callback
            this_test.received_error_callback = error_callback
            this_test.received_server = server

            this_test.received_token = session.server_session_token
            session.server_session_token = this_test.returning_token

            this_test.received_server_port = session.server_port
            session.server_port = this_test.returning_server_port

            session.server = 'testserver123.jdb'

            extra_function(session)

            while not this_test.stop_port_forward:
                sleep(1)
                if this_test.raise_exception:
                    raise Exception('test exception')

        self.app.openport.start_port_forward = fake_start_port_forward

        # Start new session without a session_token

        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()

        sleep(0.5)
        self.assertEqual(this_test.received_server, 'testserver.jdb')

        self.assertEqual(self.app.session.server_port, 1111)
        self.assertEqual(this_test.received_server_port, -1)
        self.assertEqual(this_test.received_token, '')

        # Fake response with a session token
        this_test.received_success_callback(this_test.received_session)

        # Stopping the app will make the share inactive.
        #self.app.stop()
        self.stop_port_forward = True

        sleep(3)

        self.assertFalse(thr.isAlive())


        # Restart session with the same token
        # Fake response where session_token is denied, returns new session_token

        this_test.returning_server_port = 2222
        this_test.returning_token = 'second token'
        self.stop_port_forward = False

        dbhandler.destroy_instance()

        self.app = OpenportApp()
        self.set_default_args(self.app)
        self.app.openport.start_port_forward = fake_start_port_forward

        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()

        sleep(1)
        self.assertEqual('first token', this_test.received_token)
        self.assertEqual(1111, this_test.received_server_port)
        self.assertEqual('second token', this_test.received_session.server_session_token)
        self.assertEqual(2222, this_test.received_session.server_port)

        # Fake response with a session token
        this_test.received_success_callback(this_test.received_session)


        # Stopping the app will make the share inactive.
        #self.app.stop()
        self.stop_port_forward = True

        sleep(3)

        self.assertFalse(thr.isAlive())



        # Check that new session_token is used

        this_test.returning_server_port = 2222
        this_test.returning_token = 'second token'
        self.stop_port_forward = False

        dbhandler.destroy_instance()

        self.app = OpenportApp()
        self.set_default_args(self.app)
        self.app.openport.start_port_forward = fake_start_port_forward

        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()

        sleep(1)
        self.assertEqual('second token', this_test.received_token)
        self.assertEqual(2222, this_test.received_server_port)
        self.assertEqual('second token', this_test.received_session.server_session_token)
        self.assertEqual(2222, this_test.received_session.server_port)

        # Stopping the app will make the share inactive.
        #self.app.stop()
        self.stop_port_forward = True
