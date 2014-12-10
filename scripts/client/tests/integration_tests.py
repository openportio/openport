import filecmp
from time import sleep
import unittest
import os
import sys
import threading
import urllib

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps.keyhandling import get_or_create_public_key, create_new_key_pair
from apps import keyhandling
from apps.openport_api import PortForwardResponse, request_port
from services.logger_service import set_log_level, get_logger
from services.crypt_service import get_token
from services import osinteraction
import logging
import urllib2

import xmlrunner
print sys.path

from apps.openportit import OpenportItApp
from apps.openport import Openport
from common.share import Share
from common.session import Session

from test_utils import SimpleHTTPClient, TestHTTPServer, click_open_for_ip_link

TOKEN = 'tokentest'

logger = get_logger(__name__)


class IntegrationTest(unittest.TestCase):

    def setUp(self):
        print self._testMethodName
        set_log_level(logging.DEBUG)
        self.test_server = 'test.openport.be'
        self.osinteraction = osinteraction.getInstance()

    def tearDown(self):
        if hasattr(self, 'app'):
            self.app.stop()

    def test_start_share(self):
        path = os.path.join(os.path.dirname(__file__), '../resources/logo-base.ico')
        self.assertTrue(os.path.exists(path), 'file does not exist %s' % path)
        share = self.get_share(path)
        self.app = self.start_openportit_session(share)
        click_open_for_ip_link(share.open_port_for_ip_link)
        temp_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp',
                                 os.path.basename(share.filePath) + get_token(3))

        sleep(5)
        print 'temp file: ' + temp_file
        self.downloadAndCheckFile(share, temp_file)

    def get_share(self, path):
        share = Share()
        share.filePath = path
        share.token = TOKEN
        return share

    def downloadAndCheckFile(self, share, temp_file):
        print "removing file %s" % temp_file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        self.assertFalse(os.path.exists(temp_file))
        print "file %s removed" % temp_file
        url = share.get_link()
        print 'downloading %s' % url
        try:
            urllib.urlretrieve(url, temp_file)
        except Exception, e:
            print e
        print "url %s downloaded to %s" % (url, temp_file)
        self.assertTrue(os.path.exists(temp_file), 'the downloaded file does not exist')
        self.assertTrue(filecmp.cmp(share.filePath, temp_file), 'the file compare did not succeed')
        os.remove(temp_file)

#    @unittest.skip("openport it not released")
#    def test_multi_thread(self):
#        path = os.path.join(os.path.dirname(__file__), 'testfiles/WALL_DANGER_SOFTWARE.jpg')
#        share = self.get_share(path)
#        self.app = self.start_openportit_session(share)
#        sleep(3)
#
#        temp_file_path = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', os.path.basename(share.filePath))
#        number_of_threads = 8  # Less than 10 for the brute force protection
#        errors = []
#
#        def download(file_path):
#            try:
#                self.downloadAndCheckFile(share, file_path)
#                print "download successful: %s" % file_path
#            except Exception, e:
#                errors.append(e)
#
#        threads = []
#        for i in range(number_of_threads):
#            threads.append(threading.Thread(target=download, args=['%s%s' % (temp_file_path, i)]))
#            threads[-1].setDaemon(True)
#            threads[-1].start()
#
#        seen_multiple_files_at_the_same_time = False
#
#        for j in range(6000):
#            seen_one_file = False
#            for i in range(number_of_threads):
#                if os.path.exists('%s%s' % (temp_file_path, i)) and seen_one_file:
#                    seen_multiple_files_at_the_same_time = True
#                    break
#                elif os.path.exists('%s%s' % (temp_file_path, i)):
#                    seen_one_file = True
#                    print 'seen one file from thread %s' % i
#            if seen_multiple_files_at_the_same_time:
#                break
#
#            some_threads_are_still_running = False
#            for thread in threads:
#                if thread.isAlive():
#                    some_threads_are_still_running = True
#                    break
#            if not some_threads_are_still_running:
#                print "all threads stopped"
#                break
#            sleep(0.01)
#
#        self.assertTrue(seen_multiple_files_at_the_same_time)
#
#        if errors:
#            self.fail('number of errors: %s First error: %s %s' % (len(errors), errors[0], errors))

    def test_same_port(self):
        path = os.path.join(os.path.dirname(__file__), '../logo-base.ico')
        share = self.get_share(path)
        self.success_called_back = False
        def success_callback(share):
            self.success_called_back = True
            print 'port forwarding success is called'
        share.success_observers.append(success_callback)

        self.app = self.start_openportit_session(share)

        i = 0
        while i < 100 and not self.success_called_back:
            i += 1
            sleep(0.1)
        print "escaped at ", i
        self.assertTrue(self.success_called_back)
        port = share.server_port

        dict = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=get_or_create_public_key(),
            restart_session_token=share.server_session_token,
            request_server_port=port
        )
        response = PortForwardResponse(dict)
        self.assertEqual(port, response.remote_port)

        dict = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=get_or_create_public_key(),
            restart_session_token='not the same token',
            request_server_port=port
        )
        response = PortForwardResponse(dict)
        self.assertNotEqual(port, response.remote_port)

    def test_same_port_new_key(self):

        logger.debug('getting key pair')
        private_key, public_key = create_new_key_pair()

        logger.debug('requesting port')
        dictionary = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=public_key
        )

        response = PortForwardResponse(dictionary)

        self.assertNotEqual(None, response.open_port_for_ip_link)
        logger.debug('requesting port')
        dictionary2 = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=public_key,
            restart_session_token=response.session_token,
            request_server_port=response.remote_port
        )

        response2 = PortForwardResponse(dictionary2)

        self.assertEqual(response2.remote_port, response.remote_port)

        logger.debug('requesting port')
        dictionary3 = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=public_key,
            restart_session_token='not the same token',
            request_server_port=response.remote_port
        )
        response3 = PortForwardResponse(dictionary3)
        self.assertNotEqual(response3.remote_port, response.remote_port)
        logger.debug('test done')

    def test_new_key(self):
        try:
            keyhandling.PRIVATE_KEY_FILE = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'id_rsa_tmp')
            keyhandling.PUBLIC_KEY_FILE = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'id_rsa_tmp.pub')

            logger.debug('getting key pair')
            private_key, public_key = create_new_key_pair()
            with open(keyhandling.PRIVATE_KEY_FILE, 'w') as f:
                f.write(private_key)
            with open(keyhandling.PUBLIC_KEY_FILE, 'w') as f:
                f.write(public_key)

            path = os.path.join(os.path.dirname(__file__), '../resources/logo-base.ico')
            self.assertTrue(os.path.exists(path), 'file does not exist %s' % path)
            share = self.get_share(path)
            self.app = self.start_openportit_session(share)
            self.assertTrue(share.open_port_for_ip_link)
            temp_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp',
                                     os.path.basename(share.filePath) + get_token(3))

            try:
                urllib.urlretrieve(share.get_link(), temp_file)
                self.fail('the download should have failed.')
            except self.failureException, e:
                raise e
            except Exception, e:
                print e

            click_open_for_ip_link(share.open_port_for_ip_link)

            sleep(5)
            print 'temp file: ' + temp_file
            self.downloadAndCheckFile(share, temp_file)
        finally:
            keyhandling.reset_key_locations()

    def exceptionTest(self):
        try:
            raise ValueError
        except (ValueError, TypeError):
            print "huray!"

    def test_http_forward(self):

        response = 'cha cha cha'
        port = self.osinteraction.get_open_port()

        s = self.start_http_server(port, response)

        session = Session()
        session.local_port = port
        session.server_port = 80
        session.server_session_token = None
        session.http_forward = True

        self.app = self.start_openport_session(session)

        i=0
        while i < 20 and not session.http_forward_address:
            i += 1
            sleep(1)

#        remote_port = session.server_port
#        self.assertEqual(80, remote_port)
        remote_host = session.http_forward_address
        print 'remote host:' + remote_host
        self.assertTrue('.u.%s' % self.test_server in remote_host, 'expect .u. in remote_host: %s' % remote_host)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, response.strip())
        actual_response = c.get('http://%s' % remote_host)
        self.assertEqual(actual_response, response.strip())

    def start_http_server(self, port, response):
        s = TestHTTPServer(port)
        s.reply(response)
        s.runThreaded()
        return s

    def start_openport_session(self, session):
        openport = Openport()

        self.called_back_success = False
        self.called_back_error = False

        def callback(session1):
            print session1.as_dict()
            self.assertEquals(self.test_server, session1.server)
            self.assertTrue(session1.server_port >= 2000, 'expected server_port >= 2000 but was %s' % session1.server_port)
           # self.assertTrue(share.server_port<= 51000)

            self.assertTrue(session1.account_id > 0, 'share.account_id was %s' % session1.account_id)
            self.assertTrue(session1.key_id > 0, 'share.key_id was %s' % session1.key_id)
            print 'called back, thanks :)'

        def session_success_callback(session1):
            self.called_back_success = True

        def session_error_callback(session1, exception):
            self.called_back_error = True
            raise exception

        session.success_observers.append(session_success_callback)
        session.error_observers.append(session_error_callback)

        def show_error(error_msg):
            print "error:" + error_msg

        def start_openport():
            openport.start_port_forward(session, server=self.test_server)

        thr = threading.Thread(target=start_openport)
        thr.setDaemon(True)
        thr.start()
        i = 0
        while i < 30 and (not self.called_back_success or session.server_port < 0):
            if self.called_back_error:
                self.fail('error call back!')
            sleep(1)
            i += 1
        self.assertTrue(self.called_back_success, 'not called back in time')
        print 'called back after %s seconds' % i
        return openport

    def start_openportit_session(self, share):
        self.called_back_success = False
        self.called_back_error = False

        def callback(session1):
            print session1.as_dict()
            self.assertEquals(self.test_server, session1.server)
            self.assertTrue(session1.server_port >= 2000, 'expected server_port >= 2000 but was %s' % session1.server_port)
           # self.assertTrue(share.server_port<= 51000)

            self.assertTrue(session1.account_id > 0, 'share.account_id was %s' % session1.account_id)
            self.assertTrue(session1.key_id > 0, 'share.key_id was %s' % session1.key_id)
            print 'called back, thanks :)'

        def session_success_callback(session1):
            self.called_back_success = True

        def session_error_callback(session1, exception):
            self.called_back_error = True
            raise exception

        share.success_observers.append(session_success_callback)
        share.error_observers.append(session_error_callback)

        app = OpenportItApp()
        app.args.server = self.test_server

        def start_openport_it():
            app.open_port_file(share, callback=callback)
        thr = threading.Thread(target=start_openport_it)
        thr.setDaemon(True)
        thr.start()

        i = 0
        while i < 30 and not self.called_back_success:
            if self.called_back_error:
                self.fail('error call back!')
            sleep(1)
            i += 1
        self.assertTrue(self.called_back_success, 'not called back in time')
        print 'called back after %s seconds' % i
        return app

    def test_brute_force_blocked(self):

        port = self.osinteraction.get_open_port()
        expected_response = 'cha cha cha'

        server1 = self.start_http_server(port, expected_response)

        session = Session()
        session.local_port = port
        session.server_session_token = None
        #session.http_forward = True

        self.app = self.start_openport_session(session)

        click_open_for_ip_link(session.open_port_for_ip_link)

        link = session.get_link()
        print 'link: %s' % link
        self.assertTrue(session.server_port > 1000)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, expected_response.strip())
        i = -1
        try:
            for i in range(20):
                print "connection %s" % i
                actual_response = c.get('http://%s' % link)
                self.assertEqual(actual_response, expected_response.strip())
        except (urllib2.HTTPError, urllib2.URLError) as e:
            print e
        self.assertTrue(5 < i < 20, 'i should be around 10 but was %s' % i)

        # check download on different port is still ok
        port2 = self.osinteraction.get_open_port()

        session2 = Session()
        session2.local_port = port2
        session2.server_session_token = None

        server2 = self.start_http_server(port2, expected_response)

        openport2 = self.start_openport_session(session2)
        sleep(3)
        print 'http://%s' % session2.get_link()

        click_open_for_ip_link(session2.open_port_for_ip_link)
        actual_response = c.get('http://%s' % session2.get_link())
        self.assertEqual(actual_response, expected_response.strip())

        server1.stop()
        server2.stop()
        openport2.stop_port_forward()

    def test_brute_force_blocked__not_for_http_forward(self):

        port = self.osinteraction.get_open_port()

        response = 'cha cha cha'

        s = self.start_http_server(port, response)

        session = Session()
        session.local_port = port
        session.server_port = 80
        session.server_session_token = None
        session.http_forward = True

        self.app = self.start_openport_session(session)
        click_open_for_ip_link(session.open_port_for_ip_link)

        link = session.http_forward_address
        print 'link: %s' % link

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, response.strip())
        i = -1
        try:
            for i in range(20):
                print "connection %s" % i
                actual_response = c.get('http://%s' % link)
                self.assertEqual(actual_response, response.strip())
        except (urllib2.HTTPError, urllib2.URLError) as e:
            self.fail('url error on connection nr %s' % i)


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
