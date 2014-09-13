import unittest
import sys
import xmlrunner
import os
from time import sleep
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.share import Share
from manager import dbhandler


class DBHandlerTests(unittest.TestCase):
    def setUp(self):
        dbhandler.TIMEOUT = 3
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'db_test.db')
        self.dbhandler = dbhandler.DBHandler(self.test_db)
        self.dbhandler.init_db()

    def tearDown(self):
        sleep(1)
        os.remove(self.test_db)

    def testSaveShare(self):
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


        share2 = Share()
        share2.local_port = 5000
        saved_share2 = dbhandler2.add_share(share2)
        retrieved_share2 = self.dbhandler.get_share(saved_share2.id)

        self.assertEqual(retrieved_share2.local_port, share2.local_port)

    def test_stress_test(self):
        share = Share()
        dbhandler2 = dbhandler.DBHandler(self.test_db)

        for i in range(1000):
            share.local_port = i
            saved_share = self.dbhandler.add_share(share)
            retrieved_share = dbhandler2.get_share(saved_share.id)
            self.assertEqual(retrieved_share.local_port, share.local_port)

    def test_get_shares(self):
        share1 = Share(active=False)
        share2 = Share(active=True, local_port=123)
        self.dbhandler.add_share(share1)
        self.dbhandler.add_share(share2)

        active_shares = self.dbhandler.get_shares()
        self.assertEqual(1, len(active_shares))
        self.assertEqual(share2.id, active_shares[0].id)

    def get_share_by_local_port(self):
        share1 = Share(active=False)
        share2 = Share(active=True, local_port=123)
        self.dbhandler.add_share(share1)
        self.dbhandler.add_share(share2)

        self.assertEqual(share2, self.dbhandler.get_share_by_local_port(123))

    def stop_share(self):
        share = Share(active=True)
        self.dbhandler.add_share(share)

        self.dbhandler.stop_share(share)
        self.assertEqual(False, self.dbhandler.get_share(share.id).active)

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))