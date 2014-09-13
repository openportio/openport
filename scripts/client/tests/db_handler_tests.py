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


class DBHandlerTests(unittest.TestCase):
    def setUp(self):
        dbhandler.TIMEOUT = 3
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'db_test.db')
        set_log_level(logging.DEBUG)
        self.dbhandler = dbhandler.DBHandler(self.test_db)
        self.dbhandler.init_db()


    def tearDown(self):
        self.dbhandler.stop()
        sleep(1)
        os.remove(self.test_db)

    def testSaveShare(self):
        share = Share()
        share.account_id = 6
        share.key_id = 14
        share.local_port = 2022
        share.id = -1
        self.dbhandler.add_share(share)

        self.assertNotEqual(-1, share.id)

        share2 = self.dbhandler.get_share(share.id)

        self.assertEquals(2022, share2.local_port)


    def test_concurrency(self):
        dbhandler2 = dbhandler.DBHandler(self.test_db)

        share = Share()
        share.local_port = 2224
       # share.key_id = 14
       # share.local_port = 2022
       # share.id = -1

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


    def test_stress_test_2(self):  
        return
        share = Share()


        errors = []
        for i in range(100):
          try:
            share.local_port = i
            saved_share = self.dbhandler.add_share(share)
          except:
            print 'error on i:%s' % i
            errors.append(i)
        self.assertEqual([], errors)


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
