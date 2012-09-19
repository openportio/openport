import filecmp
from time import sleep
import unittest
import os
import sys
import threading
import urllib

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
print sys.path

import openportit
from dbhandler import Share

TOKEN = 'tokentest'

class IntegrationTest(unittest.TestCase):

    def testStartShare(self):
        path = os.path.join(os.path.dirname(__file__), '../logo-base.png')
        self.start_sharing(path)
        temp_file = os.path.join(os.path.dirname(__file__), os.path.basename(self.share.filePath))
        self.downloadAndCheckFile(self.share.get_link(), self.share.filePath, temp_file)

    def start_sharing(self, path):
        self.called_back = False
        self.share = None
        def callback(portForwardResponse):

            print (portForwardResponse.server, portForwardResponse.remote_port, portForwardResponse.account_id, portForwardResponse.key_id)
            self.assertEquals('www.openport.be', portForwardResponse.server)
            self.assertTrue(portForwardResponse.remote_port>= 2000)
            self.assertTrue(portForwardResponse.remote_port<= 51000)

            self.assertTrue(portForwardResponse.account_id > 0)
            self.assertTrue(portForwardResponse.key_id > 0)

            print 'called back, thanks :)'
            self.called_back = True
            self.share = Share( filePath=path, server_ip=portForwardResponse.server, server_port=portForwardResponse.remote_port, token=TOKEN)

        share = Share()
        share.filePath = path
        share.token = TOKEN

        def start_openport_it():
            openportit.open_port_file(share, callback=callback)
        thr = threading.Thread(target=start_openport_it)
        thr.setDaemon(True)
        thr.start()

        i = 0
        while i < 10 and not self.called_back:
            i+=1
            sleep(1)
        self.assertTrue(self.called_back)


    def downloadAndCheckFile(self, url, ref_file_path, temp_file):
        try:
            os.remove(temp_file)
        except Exception:
            pass
        self.assertFalse(os.path.exists(temp_file))
        print self.share.get_link()
        urllib.urlretrieve (url, temp_file)
        self.assertTrue(os.path.exists(temp_file))
        self.assertTrue(filecmp.cmp(ref_file_path, temp_file))
        os.remove(temp_file)


    def testMultiThread(self):
        path = os.path.join(os.path.dirname(__file__), 'testfiles/WALL_DANGER_SOFTWARE.jpg')
        self.start_sharing(path)
        temp_file = os.path.join(os.path.dirname(__file__), os.path.basename(self.share.filePath))
        temp_file_path_1 = temp_file  + '1'
        temp_file_path_2 = temp_file  + '2'

        self.errors = []

        def download(temp_file_path):
            try:
                self.downloadAndCheckFile(self.share.get_link(), self.share.filePath, temp_file_path)
            except Exception, e:
                self.errors.append(e)

        thr1 = threading.Thread(target=download, args=[temp_file_path_1])
        thr1.setDaemon(True)
        thr2 = threading.Thread(target=download, args=[temp_file_path_2])
        thr2.setDaemon(True)

        thr1.start()
        thr2.start()

        seen_both_files_at_the_same_time = False

        i = 0
        while i < 6000 and (thr1.isAlive() or thr2.isAlive()):
            sleep(0.01)
            i += 1
            if os.path.exists(temp_file_path_1) and os.path.exists(temp_file_path_2):
                seen_both_files_at_the_same_time = True

        self.assertTrue(seen_both_files_at_the_same_time)

        self.assertFalse(thr1.isAlive())
        self.assertFalse(thr2.isAlive())


        self.assertEqual(0, len(self.errors))

