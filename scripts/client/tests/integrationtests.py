from time import sleep
import unittest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
print sys.path

import openportit

class IntegrationTest(unittest.TestCase):

    def testStartShare(self):
        path = '../logo-base.png'
        called_back = False
        def callback():
            print 'called back, thanks :)'
            called_back = True

        openportit.open_port_file(path, callback=callback, extra_args={})
        i = 0
        while i < 0 or not called_back:
            i+=1
            sleep(1)

        self.assertTrue(called_back)

        #todo: download file
