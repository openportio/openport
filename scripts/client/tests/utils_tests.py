__author__ = 'Jan'
import unittest
import datetime
from time import sleep

from services import utils


class AppTcpServerTests(unittest.TestCase):
    def test_run_method_with_timeout(self):
        def foo():
            sleep(0.3)
        start_time = datetime.datetime.now()
        utils.run_method_with_timeout(foo, 0.1, raise_exception=False)
        self.assertTrue(start_time + datetime.timedelta(seconds=0.2) > datetime.datetime.now())

    def test_run_method_with_timeout__exception(self):
        def foo():
            sleep(0.05)
            raise RuntimeError('test!')
        start_time = datetime.datetime.now()
        success = False
        try:
            utils.run_method_with_timeout(foo, 0.1, raise_exception=False)
        except RuntimeError:
            success = True
        self.assertTrue(success)
        self.assertTrue(start_time + datetime.timedelta(seconds=0.2) > datetime.datetime.now())
