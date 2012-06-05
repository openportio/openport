import filecmp
from time import sleep
import unittest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
print sys.path

import openportit
from dbhandler import Share

class IntegrationTest(unittest.TestCase):

    def testStartShare(self):
        path = os.path.join(os.path.dirname(__file__), '../logo-base.png')
        self.called_back = False
        self.share = None
        def callback(server_ip, server_port, account_id, key_id,  extra_args):

            print (server_ip, server_port, account_id, key_id,  extra_args)
            self.assertEquals('www.openport.be', server_ip)
            self.assertTrue(server_port>= 2000)
            self.assertTrue(server_port<= 50000)

            self.assertTrue(account_id > 0)
            self.assertTrue(key_id > 0)

            print 'called back, thanks :)'
            self.called_back = True
            self.share = Share( filePath=path, server_ip=server_ip, server_port=server_port)

        openportit.open_port_file(path, callback=callback, extra_args={})
        i = 0
        while i < 10 and not self.called_back:
            i+=1
            sleep(1)

        self.assertTrue(self.called_back)
        temp_file = os.path.join(os.path.dirname(__file__), os.path.basename(self.share.filePath))

        sleep(2)
        try:
            os.remove(temp_file)
        except Exception:
            pass
        self.assertFalse(os.path.exists(temp_file))
        import urllib
        print self.share.get_link()
        urllib.urlretrieve (self.share.get_link(), temp_file)
        self.assertTrue(os.path.exists(temp_file))
        self.assertTrue(filecmp.cmp(self.share.filePath, temp_file))

        os.remove(temp_file)
