__author__ = 'jan'

from integrationtests import IntegrationTest


class LiveIntegrationTest(IntegrationTest):

    def setUp(self):
        IntegrationTest.setUp(self)
        self.test_server='openport.be'