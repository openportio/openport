import filecmp
from time import sleep
import unittest
import os
import sys
import threading
import urllib

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps.keyhandling import get_or_create_public_key, create_new_key_pair
from apps.openport_api import PortForwardResponse, request_port
from services.logger_service import set_log_level
from services.crypt_service import get_token
import logging

import xmlrunner
print sys.path

from apps.openportit import OpenportItApp
from apps.openport import Openport
from common.share import Share
from common.session import Session

from test_utils import get_open_port, SimpleHTTPClient, TestHTTPServer

TOKEN = 'tokentest'


class IntegrationTest(unittest.TestCase):

    def setUp(self):
        set_log_level(logging.DEBUG)
        self.test_server = 'test.openport.be'

    def test_start_share(self):
        path = os.path.join(os.path.dirname(__file__), '../resources/logo-base.ico')
        share = self.get_share(path)
        self.start_sharing(share)
        temp_file = os.path.join(os.path.dirname(__file__), os.path.basename(share.filePath) + get_token(3))
        sleep(5)
        print 'temp file: ' + temp_file
        self.downloadAndCheckFile(share, temp_file)

    def get_share(self, path):
        share = Share()
        share.filePath = path
        share.token = TOKEN
        return share

    def start_sharing(self, share):
        self.called_back = False
        def callback(share):

            print share.as_dict()
            self.assertEquals(self.test_server, share.server)
            self.assertTrue(share.server_port >= 2000, 'expection serverport >= 2000 but was %s' % share.server_port)
           # self.assertTrue(share.server_port<= 51000)

            self.assertTrue(share.account_id > 0, 'share.account_id was %s' % share.account_id)
            self.assertTrue(share.key_id > 0, 'share.key_id was %s' % share.key_id)

            print 'called back, thanks :)'
            self.called_back = True

        def start_openport_it():
            app = OpenportItApp()
            app.args.server = self.test_server
            app.open_port_file(share, callback=callback)
        thr = threading.Thread(target=start_openport_it)
        thr.setDaemon(True)
        thr.start()

        i = 0
        while i < 10 and not self.called_back:
            i += 1
            sleep(1)
        self.assertTrue(self.called_back, 'I was not called back in the given time')
        return share

    def downloadAndCheckFile(self, share, temp_file):
        print "removing file %s" % temp_file
        try:
            os.remove(temp_file)
        except:
            pass
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

    def test_multi_thread(self):
        path = os.path.join(os.path.dirname(__file__), 'testfiles/WALL_DANGER_SOFTWARE.jpg')
        share = self.get_share(path)
        self.start_sharing(share)
        sleep(3)

        temp_file_path = os.path.join(os.path.dirname(__file__), os.path.basename(share.filePath))
        number_of_threads = 10
        errors = []

        def download(file_path):
            try:
                self.downloadAndCheckFile(share, file_path)
                print "download successful: %s" % file_path
            except Exception, e:
                errors.append(e)

        threads = []
        for i in range(number_of_threads):
            threads.append(threading.Thread(target=download, args=['%s%s' % (temp_file_path, i)]))
            threads[-1].setDaemon(True)
            threads[-1].start()

        seen_multiple_files_at_the_same_time = False

        for j in range(6000):
            seen_one_file = False
            for i in range(number_of_threads):
                if os.path.exists('%s%s' % (temp_file_path, i)) and seen_one_file:
                    seen_multiple_files_at_the_same_time = True
                    break
                elif os.path.exists('%s%s' % (temp_file_path, i)):
                    seen_one_file = True
                    print 'seen one file from thread %s' % i
            if seen_multiple_files_at_the_same_time:
                break

            some_threads_are_still_running = False
            for thread in threads:
                if thread.isAlive():
                    some_threads_are_still_running = True
                    break
            if not some_threads_are_still_running:
                print "all threads stopped"
                break
            sleep(0.01)

        self.assertTrue(seen_multiple_files_at_the_same_time)

        if errors:
            self.fail('number of errors: %s First error: %s' % (len(errors), errors[0]))

    def test_same_port(self):
        path = os.path.join(os.path.dirname(__file__), '../logo-base.ico')
        share = self.get_share(path)
        self.success_called_back = False
        def success_callback(share):
            self.success_called_back = True
            print 'port forwarding success is called'
        share.success_observers.append(success_callback)

        self.start_sharing(share)

        i = 0
        while i < 400 and not self.success_called_back:
            i += 1
            sleep(0.01)
        print "escaped at ",i
        self.assertTrue(self.success_called_back)
        port = share.server_port

        # apparently, the request is not needed, but hey, lets keep it.
        #url = 'http://%s/debug/linkSessionsToPids?key=batterycupspoon' % self.test_server
        #req = urllib2.Request(url)
        #response = urllib2.urlopen(req).read()
        #self.assertEqual('done', response.strip())

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

        private_key, public_key = create_new_key_pair()

        dictionary = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=public_key
        )

        response = PortForwardResponse(dictionary)

        dictionary2 = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=public_key,
            restart_session_token=response.session_token,
            request_server_port=response.remote_port
        )

        response2 = PortForwardResponse(dictionary2)

        self.assertEqual(response2.remote_port, response.remote_port)

        dictionary3 = request_port(
            url='https://%s/api/v1/request-port' % self.test_server,
            public_key=public_key,
            restart_session_token='not the same token',
            request_server_port=response.remote_port
        )
        response3 = PortForwardResponse(dictionary3)
        self.assertNotEqual(response3.remote_port, response.remote_port)


    def exceptionTest(self):
        try:
            raise ValueError
        except ValueError, TypeError:
            print "huray!"

    def test_http_forward(self):

        response = 'cha cha cha'
        port = get_open_port()
        s = TestHTTPServer(port)
        s.reply(response)
        s.runThreaded()

        def callback(ignore):
            print "callback"

        def show_error(error_msg):
            print "error:" + error_msg

        session = Session()
        session.local_port = port
        session.server_port = 80
        session.server_session_token = None
        session.http_forward = True

        def start_openport():
            openport = Openport()
            openport.start_port_forward(session, callback, show_error, server=self.test_server)

        thr = threading.Thread(target=start_openport)
        thr.setDaemon(True)
        thr.start()

        sleep(10)

#        remote_port = session.server_port
#        self.assertEqual(80, remote_port)
        remote_host = session.http_forward_address
        print 'remote host:' + remote_host
        self.assertTrue('.u.%s' % self.test_server in remote_host)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, response.strip())
        actual_response = c.get('http://%s' % remote_host)
        self.assertEqual(actual_response, response.strip())

        # todo: kill thread

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
