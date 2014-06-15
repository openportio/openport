import unittest
import sys
import xmlrunner
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.share import Share
from manager import dbhandler


class DBHandlerTests(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'db_test.db')
        self.dbhandler = dbhandler.DBHandler(self.test_db)
        self.dbhandler.init_db()

    def tearDown(self):
        self.dbhandler.stop()
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

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))