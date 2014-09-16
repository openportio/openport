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


class DBHandlerTests(unittest.TestCase):
    def setUp(self):
        logging.basicConfig()

        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

        dbhandler.TIMEOUT = 3
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'db_test.db')
        try:
            os.remove(self.test_db)
        except:
            pass
        set_log_level(logging.DEBUG)
        self.dbhandler = dbhandler.DBHandler(self.test_db)
        self.dbhandler.init_db()

    def tearDown(self):
        sleep(1)

    def test_save_share(self):
        share = Share()
        share.account_id = 6
        share.key_id = 14
        share.local_port = 2022
        share.id = -1
        share.server_session_token = 'abcd'

        share.server = 'a.openport.io'
        share.server_port = 1234
        share.pid = 234
        share.active = True
        share.restart_command = ['restart', 'command']
        share.http_forward = True
        share.http_forward_address = 'http://jan.u.openport.io'

        self.dbhandler.add_share(share)

        self.assertNotEqual(-1, share.id)

        share2 = self.dbhandler.get_share(share.id)

        self.assertEquals(share.id, share2.id)
        self.assertEquals(share.server, share2.server)
        self.assertEquals(share.server_port, share2.server_port)
        self.assertEquals(share.pid, share2.pid)
        self.assertEquals(share.active, share2.active)
        self.assertEquals(share.account_id, share2.account_id)
        self.assertEquals(share.key_id, share2.key_id)
        self.assertEquals(share.local_port, share2.local_port)
        self.assertEquals(share.server_session_token, share2.server_session_token)
        self.assertEquals(share.restart_command, share2.restart_command)
        self.assertEquals(share.http_forward, share2.http_forward)
        self.assertEquals(share.http_forward_address, share2.http_forward_address)

    def test_concurrency(self):
        dbhandler2 = dbhandler.DBHandler(self.test_db)

        share = Share()
        share.local_port = 2224
        saved_share = self.dbhandler.add_share(share)
        retrieved_share = dbhandler2.get_share(saved_share.id)

        self.assertEqual(retrieved_share.local_port, share.local_port)

    def test_concurrency_2(self):
        dbhandler2 = dbhandler.DBHandler(self.test_db)

        share = Share()
        share.local_port = 2224
        saved_share = self.dbhandler.add_share(share)
        retrieved_share = dbhandler2.get_share(saved_share.id)

        self.assertEqual(retrieved_share.local_port, share.local_port)

    def test_stress_test(self):  
        share = Share()

        dbhandler2 = dbhandler.DBHandler(self.test_db)

        errors = []
        for i in range(100):
          try:
            share.local_port = i
            saved_share = self.dbhandler.add_share(share)
            retrieved_share = dbhandler2.get_share(saved_share.id)
            self.assertEqual(retrieved_share.local_port, share.local_port)

            saved_share = dbhandler2.add_share(share)
            retrieved_share = self.dbhandler.get_share(saved_share.id)
            self.assertEqual(retrieved_share.local_port, share.local_port)
          except:
            print 'error on i:%s' % i
            errors.append(i)
        self.assertEqual([], errors)

    def test_get_shares(self):
        share1 = Share(active=False)
        share2 = Share(active=True, local_port=123)
        self.dbhandler.add_share(share1)
        self.dbhandler.add_share(share2)

        active_shares = self.dbhandler.get_shares()
        self.assertEqual(1, len(active_shares))
        self.assertEqual(share2.id, active_shares[0].id)

    def test_get_share_by_local_port(self):
        share1 = Share(active=False, local_port=123)
        share2 = Share(active=True, local_port=123)
        self.assertEqual(share2.local_port, 123)
        share3 = Share(active=True, local_port=1111)
        self.dbhandler.add_share(share1)
        self.dbhandler.add_share(share2)
        self.dbhandler.add_share(share3)

        shares = self.dbhandler.get_share_by_local_port(123)
        self.assertEqual(1, len(shares))
        self.assertEqual(share2.id, shares[0].id)

    def test_stop_share(self):
        share = Share(active=True, local_port=444)
        self.dbhandler.add_share(share)
        self.assertEqual(1, share.id)
        self.dbhandler.stop_share(share)
        self.assertEqual(False, self.dbhandler.get_share(share.id).active)

    def test_multi_thread(self):
        share = Share(local_port=22)
        self.dbhandler.add_share(share)

        self.share2 = None

        def get_share():
            self.share2 = self.dbhandler.get_share(share.id)
        thr = threading.Thread(target=get_share)
        thr.setDaemon(True)
        thr.start()

        sleep(0.3)
        self.assertNotEqual(None, self.share2)
        self.assertEqual(share.local_port, self.share2.local_port)


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
