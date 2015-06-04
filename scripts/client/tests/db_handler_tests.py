import unittest
import sys
import os
import gc
from time import sleep
from cStringIO import StringIO
import shutil

import xmlrunner


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.share import Share
from services import dbhandler
from services.logger_service import set_log_level
import logging
import threading


class DBHandlerTests(unittest.TestCase):
    def setUp(self):
        print self._testMethodName
        logging.basicConfig()

        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

        dbhandler.TIMEOUT = 3
        self.test_db = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'db_test.db')
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        set_log_level(logging.DEBUG)
        self.dbhandler = dbhandler.DBHandler(self.test_db)
        self.dbhandler.init_db(False)

    def tearDown(self):
        self.dbhandler.close()
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
        share.app_management_port = 43122
        share.open_port_for_ip_link = 'http//openport.io/l/1234/zerazer'

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
        self.assertEquals(share.app_management_port, share2.app_management_port)
        self.assertEquals(share.open_port_for_ip_link, share2.open_port_for_ip_link)

    def test_save(self):
        share = Share()
        self.dbhandler.add_share(share)
        id = share.id
        self.dbhandler.add_share(share)
        self.assertEqual(id, share.id)

    def test_concurrency(self):
        dbhandler2 = dbhandler.DBHandler(self.test_db)

        share = Share()
        share.local_port = 2224
        saved_share = self.dbhandler.add_share(share)
        retrieved_share = dbhandler2.get_share(saved_share.id)
        try:
            self.assertEqual(retrieved_share.local_port, share.local_port)
        finally:
            dbhandler2.close()

    def test_concurrency_2(self):
        dbhandler2 = dbhandler.DBHandler(self.test_db)
        try:

            share = Share(active=True)
            share.local_port = 2224

            share2 = Share(active=True)
            share2.local_port = 2225

            saved_share = self.dbhandler.add_share(share)
            saved_share2 = dbhandler2.add_share(share2)

            retrieved_share2 = self.dbhandler.get_share_by_local_port(2225)[0]
            retrieved_share = self.dbhandler.get_share_by_local_port(2224)[0]

            self.assertEqual(retrieved_share.local_port, share.local_port)
            self.assertEqual(retrieved_share2.local_port, share2.local_port)
        finally:
            dbhandler2.close()

    def test_stress_test(self):  
        share = Share()

        dbhandler2 = dbhandler.DBHandler(self.test_db)

        try:
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
        finally:
            dbhandler2.close()

    def test_stress_test_init_db(self):
        errors = []
        def init_db_test():
            try:
                dbh = dbhandler.DBHandler(self.test_db)
                dbh.init_db(True)
            except Exception, e:
                global errors
                errors.append(e)

        threads = []

        for i in range(10):
            t = threading.Thread(target=init_db_test)
            t.setDaemon(True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
        self.assertEqual([], errors)

    def test_get_active_shares(self):
        share1 = Share(active=False)
        share2 = Share(active=True, local_port=123)
        self.dbhandler.add_share(share1)
        self.dbhandler.add_share(share2)

        active_shares = self.dbhandler.get_active_shares()
        self.assertEqual(1, len(active_shares))
        self.assertEqual(share2.id, active_shares[0].id)

    def test_get_shares_to_restart(self):
        share1 = Share(active=False)
        share2 = Share(active=True, local_port=123, restart_command=['sleep', '5'])
        share3 = Share(active=True, local_port=124, restart_command='')
        self.dbhandler.add_share(share1)
        self.dbhandler.add_share(share2)
        self.dbhandler.add_share(share3)

        active_shares = self.dbhandler.get_shares_to_restart()
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

    def test_multi_thread_2(self):
        share = Share(local_port=22, active=True)
        self.dbhandler.add_share(share)

        def get_share():
            share2 = Share(local_port=23, active=True)
            self.dbhandler.add_share(share2)
            # It is super important that the session is closed on the end of the thread, otherwise this will result in
            # an error when the current thread is trying to close it.
            self.dbhandler.Session.remove()
        thr = threading.Thread(target=get_share)
        thr.setDaemon(True)
        thr.start()

        sleep(2)
        self.assertEqual(2, len(self.dbhandler.get_active_shares()))

    def test_get_share__not_found(self):
        self.assertEqual(None, self.dbhandler.get_share(-1))

    def test_double_add_share(self):
        share = Share(active=True, local_port=444)
        self.dbhandler.add_share(share)

        share2 = Share(active=True, local_port=444)
        self.dbhandler.add_share(share2)

        self.assertEqual(1, len(self.dbhandler.get_active_shares()))

    def test_gc_in_thread(self):

        str1 = StringIO()
        ch = logging.StreamHandler(str1)
        logging.getLogger('sqlalchemy').addHandler(ch)

        def do_gc():
            gc.collect()

        share = Share(active=True, local_port=444)
        self.dbhandler.add_share(share)

        self.assertEqual(1, len(self.dbhandler.get_active_shares()))
        self.assertEqual(share.id, self.dbhandler.get_share(1).id)

        t = threading.Thread(target=do_gc)
        t.setDaemon(True)
        t.start()

        t.join()
        self.assertTrue(not 'ProgrammingError' in str1.getvalue())

    def test_alembic(self):
        old_db = os.path.join(os.path.dirname(__file__), 'testfiles/openport-0.9.1.db')
        old_db_tmp = os.path.join(os.path.dirname(__file__), 'testfiles/tmp/openport-0.9.1.db')

        shutil.copy(old_db, old_db_tmp)

        db_handler = dbhandler.DBHandler(old_db_tmp)

        session = db_handler.get_share_by_local_port(22)
        self.assertNotEqual(None, session)

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
