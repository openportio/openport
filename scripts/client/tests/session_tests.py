__author__ = 'jan'
import unittest
from common.share import Share


class SessionTests(unittest.TestCase):

    def setUp(self):
        print self._testMethodName

    def test_as_dict(self):
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

        share2 = Share().from_dict(share.as_dict())

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