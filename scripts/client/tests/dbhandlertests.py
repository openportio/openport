import unittest
from common.share import Share
from tray import dbhandler


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.dbhandler = dbhandler.DBHandler()
        self.dbhandler.db_location = 'testfiles/db_test.db'
        self.dbhandler.init_db()

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
