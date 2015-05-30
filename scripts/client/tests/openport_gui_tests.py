import os
import sys
import logging
import threading
import unittest
from time import sleep

import wx


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.osinteraction import getInstance
from services.logger_service import set_log_level, get_logger
from test_utils import wait_for_response
from apps.openport_app import OpenportApp
from services import dbhandler
from test_utils import set_default_args
from gui.openport_gui import SharesFrame
from common.session import Session
from services.app_service import AppService
from common.config import OpenportAppConfig

logger = get_logger(__name__)


def gui_test(func):
    def inner(self):
        def test_thread():
            try:
                func(self)
            except Exception as e:
                self.exception = e
                raise
            finally:
                #wx.Exit()
                self.gui_frame.exitApp(None)
        thr = threading.Thread(target=test_thread)
        thr.setDaemon(True)
        thr.start()
        self.gui_app.MainLoop()
        if self.exception:
            raise self.exception
    return inner


class OpenportAppTests(unittest.TestCase):
    def setUp(self):
        print self._testMethodName
        self.os_interaction = getInstance()
        set_log_level(logging.DEBUG)
        self.app = OpenportApp()
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'db_test.db')
        try:
            os.remove(self.test_db)
        except:
            pass

        self.gui_app = wx.App()
        self.gui_frame = SharesFrame(wx_app=self.gui_app, db_location=self.test_db)
        self.exception = None

    def tearDown(self):
        pass

    @gui_test
    def test_register_share(self):

        self.gui_frame.initialize()
        self.assertEqual(0, len(self.gui_frame.share_panels))

        set_default_args(self.app, self.test_db)
        self.app.args.database = self.test_db

        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()
        wait_for_response(lambda: self.app.session and self.app.session.active)
        sleep(5)

        db_handler = dbhandler.DBHandler(self.test_db)
        self.assertEqual(1, len(db_handler.get_shares()))
        self.assertEqual(1, len(self.gui_frame.share_panels))
        logger.debug('Success!')

    @gui_test
    def test_show_shares_in_db(self):
        set_default_args(self.app, self.test_db)
        self.app.args.database = self.test_db

        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()

        wait_for_response(lambda: self.app.session and self.app.session.active)

        self.gui_frame.initialize()
        self.assertEqual(1, len(self.gui_frame.share_panels))

    @gui_test
    def test_stop_share(self):

        self.gui_frame.initialize()
        self.assertEqual(0, len(self.gui_frame.share_panels))

        set_default_args(self.app, self.test_db)
        self.app.args.database = self.test_db

        self.app.args.local_port = 24
        thr = threading.Thread(target=self.app.start)
        thr.setDaemon(True)
        thr.start()
        wait_for_response(lambda: self.app.session and self.app.session.active)
        sleep(5)

        db_handler = dbhandler.DBHandler(self.test_db)
        self.assertEqual(1, len(db_handler.get_shares()))
        self.assertEqual(1, len(self.gui_frame.share_panels))

        stop_button = self.find_element_with_label(self.gui_frame.share_panels[self.app.session.id], 'Stop sharing')
        command_event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, -1)
        stop_button.Command(command_event)

        wait_for_response(lambda: self.app.session and not self.app.session.active)
        sleep(5)

        self.assertEqual(0, len(db_handler.get_shares()))
        self.assertEqual(0, len(self.gui_frame.share_panels))

        logger.debug('Success!')

    def find_element_with_label(self, widget, label):
        for child in widget.GetChildren():
            print child.GetLabel()
            if child.GetLabel() == label:
                return child
            sub_child = self.find_element_with_label(child, label)
            if sub_child:
                return sub_child
        return None

    def test_restart_gui(self):
        processes = {}

        def test_thread():
            try:
                self.gui_frame.initialize()
                self.assertEqual(0, len(self.gui_frame.share_panels))

                port = self.os_interaction.get_open_port()

                app_service = AppService(OpenportAppConfig())
                session = Session()
                session.local_port = port
                global p
                p = app_service.start_openport_process_from_session(session, database=self.test_db)
                processes[p.pid] = p

                db_handler = dbhandler.DBHandler(self.test_db)
                wait_for_response(lambda: len(db_handler.get_shares()) > 0)

                self.assertEqual(1, len(self.gui_frame.share_panels))
            finally:
                #wx.Exit()
                self.gui_frame.exitApp(None)
        thr = threading.Thread(target=test_thread)
        thr.setDaemon(True)
        thr.start()
        self.gui_app.MainLoop()


        def test_thread():
            try:
                self.gui_frame.initialize()
                self.assertEqual(1, len(self.gui_frame.share_panels))
                logger.debug('Success!')
            finally:
                #wx.Exit()
                for pid, p in processes.iteritems():
                    logger.debug('killing %s' % p.pid)
                    self.os_interaction.kill_pid(p.pid)
                self.gui_frame.exitApp(None)
        thr = threading.Thread(target=test_thread)
        thr.setDaemon(True)
        thr.start()
        self.gui_app.MainLoop()

