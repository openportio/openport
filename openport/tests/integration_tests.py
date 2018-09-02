from __future__ import print_function
import filecmp
from time import sleep
import unittest
import os
import sys
import urllib
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from openport.apps.keyhandling import get_or_create_public_key, create_new_key_pair
from openport.apps.openport_api import PortForwardResponse, request_port
from openport.services.logger_service import set_log_level, get_logger
from openport.services.crypt_service import get_token
from openport.services import osinteraction
from openport.apps.openport_api import request_open_port
import logging

import xmlrunner

from openport.common.share import Share
from openport.common.session import Session

from .test_utils import SimpleHTTPClient, TestHTTPServer, click_open_for_ip_link, check_tcp_port_forward
from .test_utils import start_openportit_session, start_openport_session, wait_for_response
from openport.services.utils import run_method_with_timeout

TOKEN = 'tokentest'

logger = get_logger(__name__)


class IntegrationTest(unittest.TestCase):

    def setUp(self):
        print(self._testMethodName)
        set_log_level(logging.DEBUG)
        #self.test_server = 'http://test.openport.be'
        self.test_server = 'https://test2.openport.io'
        self.osinteraction = osinteraction.getInstance()

    def tearDown(self):
        if hasattr(self, 'app'):
            self.app.stop()

    def test_start_share(self):
        path = os.path.join(os.path.dirname(__file__), '../resources/logo-base.ico')
        self.assertTrue(os.path.exists(path), 'file does not exist %s' % path)
        share = self.get_share(path)
        self.app = start_openportit_session(self, share)
        click_open_for_ip_link(share.open_port_for_ip_link)
        temp_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp',
                                 os.path.basename(share.filePath) + get_token(3))

        print('temp file: ' + temp_file)
        self.downloadAndCheckFile(share, temp_file)

    def test_start_session(self):
        port_out = self.osinteraction.get_open_port()
        out_session = Session()
        out_session.local_port = port_out
        out_session.server_session_token = None

        out_app = None
        try:
            out_app = start_openport_session(self, out_session)
            remote_host, remote_port, link = out_session.server, out_session.server_port, out_session.open_port_for_ip_link
            click_open_for_ip_link(link)
            print(remote_port)
            sleep(10)
            #sleep(1000)
            check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)
        finally:
            if out_app:
                out_app.stop()

    def get_share(self, path):
        share = Share()
        share.filePath = path
        share.token = TOKEN
        return share

    def downloadAndCheckFile(self, share, temp_file):
        print("removing file %s" % temp_file)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        self.assertFalse(os.path.exists(temp_file))
        print("file %s removed" % temp_file)
        url = share.get_link()
        print('downloading %s' % url)
        try:
            urllib.urlretrieve(url, temp_file)
        except Exception as e:
            print(e)
        print("url %s downloaded to %s" % (url, temp_file))
        self.assertTrue(os.path.exists(temp_file), 'the downloaded file does not exist')
        self.assertTrue(filecmp.cmp(share.filePath, temp_file), 'the file compare did not succeed')
        os.remove(temp_file)

#    @unittest.skip("openport it not released")
#    def test_multi_thread(self):
#        path = os.path.join(os.path.dirname(__file__), 'testfiles/WALL_DANGER_SOFTWARE.jpg')
#        share = self.get_share(path)
#        self.app = start_openportit_session(self, share)
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
#            except Exception as e:
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

        self.app = start_openportit_session(self, share)
        port = share.server_port

        dict = request_port(
            url='%s/api/v1/request-port' % self.test_server,
            public_key=get_or_create_public_key(),
            restart_session_token=share.server_session_token,
            request_server_port=port
        )
        response = PortForwardResponse(dict)
        self.assertEqual(port, response.remote_port)

        dict = request_port(
            url='%s/api/v1/request-port' % self.test_server,
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
            url='%s/api/v1/request-port' % self.test_server,
            public_key=public_key
        )

        response = PortForwardResponse(dictionary)

        self.assertNotEqual(None, response.open_port_for_ip_link)
        logger.debug('requesting port')
        dictionary2 = request_port(
            url='%s/api/v1/request-port' % self.test_server,
            public_key=public_key,
            restart_session_token=response.session_token,
            request_server_port=response.remote_port
        )

        response2 = PortForwardResponse(dictionary2)

        self.assertEqual(response2.remote_port, response.remote_port)

        logger.debug('requesting port')
        dictionary3 = request_port(
            url='%s/api/v1/request-port' % self.test_server,
            public_key=public_key,
            restart_session_token='not the same token',
            request_server_port=response.remote_port
        )
        response3 = PortForwardResponse(dictionary3)
        self.assertNotEqual(response3.remote_port, response.remote_port)
        logger.debug('test done')

    def test_long_key(self):
        private_key_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'id_rsa_tmp')
        public_key_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'id_rsa_tmp.pub')

        logger.debug('getting key pair')
        private_key, public_key = create_new_key_pair(4096)
        with open(private_key_file, 'w') as f:
            f.write(private_key)
        with open(public_key_file, 'w') as f:
            f.write(public_key)

        port_out = self.osinteraction.get_open_port()
        out_session = Session()
        out_session.local_port = port_out
        out_session.server_session_token = None
        out_session.public_key_file = public_key_file
        out_session.private_key_file = private_key_file

        out_app = None
        try:
            out_app = start_openport_session(self, out_session)
            remote_host, remote_port, link = out_session.server, out_session.server_port, out_session.open_port_for_ip_link
            click_open_for_ip_link(link)
            print(remote_port)
            sleep(10)
            #sleep(1000)
            check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)
        finally:
            if out_app:
                out_app.stop()

    def test_new_key__not_clicking_open_for_ip_link(self):
        private_key_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'id_rsa_tmp')
        public_key_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp', 'id_rsa_tmp.pub')

        logger.debug('getting key pair')
        private_key, public_key = create_new_key_pair()
        with open(private_key_file, 'w') as f:
            f.write(private_key)
        with open(public_key_file, 'w') as f:
            f.write(public_key)

        path = os.path.join(os.path.dirname(__file__), '../resources/logo-base.ico')
        self.assertTrue(os.path.exists(path), 'file does not exist %s' % path)
        share = self.get_share(path)
        share.private_key_file = private_key_file
        share.public_key_file = public_key_file
        self.app = start_openportit_session(self, share)
        self.assertTrue(share.open_port_for_ip_link)
        temp_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp',
                                 os.path.basename(share.filePath) + get_token(3))

        try:
            urllib.urlretrieve(share.get_link(), temp_file)
            self.fail('the download should have failed.')
        except self.failureException as e:
            raise e
        except Exception as e:
            print(e)

        click_open_for_ip_link(share.open_port_for_ip_link)

        sleep(5)
        print ('temp file: ' + temp_file)
        self.downloadAndCheckFile(share, temp_file)

    def exceptionTest(self):
        try:
            raise ValueError
        except (ValueError, TypeError):
            print ("huray!")

    def test_http_forward(self):

        response = 'cha cha cha'
        port = self.osinteraction.get_open_port()

        s = self.start_http_server(port, response)

        session = Session()
        session.local_port = port
        session.server_port = 80
        session.server_session_token = None
        session.http_forward = True

        self.app = start_openport_session(self, session)

        i=0
        while i < 20 and not session.http_forward_address:
            i += 1
            sleep(1)

#        remote_port = session.server_port
#        self.assertEqual(80, remote_port)
        remote_host = session.http_forward_address
        print ('remote host:' + remote_host)
        self.assertTrue('.u.' in remote_host, 'expect .u. in remote_host: %s' % remote_host)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, response.strip())
        actual_response = c.get('http://%s' % remote_host)
        self.assertEqual(actual_response, response.strip())

    def test_http_forward__same_address(self):
        response = 'cha cha cha'
        port = self.osinteraction.get_open_port()

        s = self.start_http_server(port, response)
        session = Session()
        session.local_port = port
        session.server_session_token = None
        session.http_forward = True

        self.app = start_openport_session(self, session)

        remote_host = session.http_forward_address
        print ('remote host:' + remote_host)
        self.assertTrue('.u.' in remote_host, 'expect .u. in remote_host: %s' % remote_host)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, response.strip())
        actual_response = c.get('http://%s' % remote_host)
        self.assertEqual(actual_response, response.strip())

        session2 = Session()
        session2.local_port = port
        session2.server_session_token = None
        session2.http_forward = True
        session2.server_port = session.server_port
        session2.server_session_token = session.server_session_token
        self.app = start_openport_session(self, session2)

      #  self.assertEqual(session.server_port, session2.server_port)
        self.assertEqual(session.http_forward_address, session2.http_forward_address)

    def start_http_server(self, port, response):
        s = TestHTTPServer(port)
        s.reply(response)
        s.runThreaded()
        return s

    def test_brute_force_blocked(self):
        port = self.osinteraction.get_open_port()
        expected_response = 'cha cha cha'

        server1 = self.start_http_server(port, expected_response)

        session = Session()
        session.local_port = port
        session.server_session_token = None
        #session.http_forward = True

        self.app = start_openport_session(self, session)

        click_open_for_ip_link(session.open_port_for_ip_link)

        link = session.get_link()
        print ('link: %s' % link)
        self.assertTrue(session.server_port > 1000)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, expected_response.strip())
        i = -1
        try:
            for i in range(20):
                print ("connection %s" % i)
                actual_response = c.get('http://%s' % link)
                self.assertEqual(actual_response, expected_response.strip())
        except (urllib2.HTTPError, urllib2.URLError) as e:
            print (e)
        self.assertTrue(5 < i < 20, 'i should be around 10 but was %s' % i)

        # check download on different port is still ok
        port2 = self.osinteraction.get_open_port()

        session2 = Session()
        session2.local_port = port2
        session2.server_session_token = None

        server2 = self.start_http_server(port2, expected_response)

        openport2 = start_openport_session(self, session2)
        sleep(3)
        print ('http://%s' % session2.get_link())

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

        self.app = start_openport_session(self, session)
        click_open_for_ip_link(session.open_port_for_ip_link)

        link = session.http_forward_address
        print ('link: %s' % link)

        c = SimpleHTTPClient()
        actual_response = c.get('http://localhost:%s' % port)
        self.assertEqual(actual_response, response.strip())
        i = -1
        try:
            for i in range(20):
                print ("connection %s" % i)
                actual_response = c.get('http://%s' % link)
                self.assertEqual(actual_response, response.strip())
        except (urllib2.HTTPError, urllib2.URLError) as e:
            self.fail('url error on connection nr %s' % i)

    def test_forward_tunnel(self):
        port_out = self.osinteraction.get_open_port()

        out_session = Session()
        out_session.local_port = port_out
        out_session.server_session_token = None

        out_app, in_app = None, None
        try:
            out_app = start_openport_session(self, out_session)

            remote_host, remote_port, link = out_session.server, out_session.server_port, out_session.open_port_for_ip_link
            click_open_for_ip_link(link)
            check_tcp_port_forward(self, remote_host=remote_host, local_port=port_out, remote_port=remote_port)

            port_in = self.osinteraction.get_open_port()
            logger.info('port_in: %s' % port_in)

            in_session = Session()
            in_session.forward_tunnel = True
            in_session.server_port = out_session.server_port
            in_session.local_port = port_in

            in_app = start_openport_session(self, in_session)
            sleep(10)

            check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_in)

            port_bad_in = self.osinteraction.get_open_port()
            bad_session = Session()
            bad_session.forward_tunnel = True
            bad_session.server_port = out_session.server_port
            bad_session.local_port = port_bad_in

            keys = create_new_key_pair()
            private_key_file = 'testfiles/tmp/tmp_key'
            with open(private_key_file, 'w') as f:
                f.write(keys[0])

            public_key_file = 'testfiles/tmp/tmp_key.pub'
            with open(public_key_file, 'w') as f:
                f.write(keys[1])

            bad_session.public_key_file = public_key_file
            bad_session.private_key_file = private_key_file

            fail = False
            try:
                in_app = start_openport_session(self, bad_session)
                fail = True
            except AssertionError:
                pass
            self.assertFalse(fail)

            self.assertFalse(check_tcp_port_forward(self, remote_host='127.0.0.1', local_port=port_out, remote_port=port_bad_in, fail_on_error=False))
        finally:
            if out_app:
                out_app.stop()
            if in_app:
                in_app.stop()

    def test_rogue_ssh_sessions(self):
        port = self.osinteraction.get_open_port()
        port2 = self.osinteraction.get_open_port()

        self.assertNotEqual(port, port2)
        request_open_port(port, server=self.test_server)
        command = ['/usr/bin/ssh', 'open@%s' % self.test_server.split('//')[1], '-R',
                   '%s:localhost:%s' % (port2, port2), 'wrong_session_token']
        print (command)
        p = subprocess.Popen(command,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=False)
        failed = wait_for_response(lambda: p.poll() is not None, timeout=10, throw=False)
        sleep(3)
        output = self.osinteraction.non_block_read(p)
        print (output)
        self.assertTrue('remote port forwarding failed for listen port' in output[1])
        self.assertFalse(failed)

    def test_rogue_ssh_session__correct(self):
        port = self.osinteraction.get_open_port()

        response = request_open_port(port, server=self.test_server)
        command = ['/usr/bin/ssh', 'open@%s' % self.test_server.split('//')[1], '-R',
                   '%s:localhost:%s' % (response.remote_port, port), response.session_token]
        print (command)
        p = subprocess.Popen(command,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=False)
        run_method_with_timeout(lambda: wait_for_response(lambda: p.poll() is not None, timeout=10, throw=False), 10, raise_exception=False)
        if p.returncode:
            print (p.communicate())
        self.assertEqual(p.returncode, None)

    def test_rogue_ssh_session__correct__old_version(self):
        port = self.osinteraction.get_open_port()

        response = request_open_port(port, server=self.test_server, client_version='0.9.3')
        command = ['/usr/bin/ssh', 'open@%s' % self.test_server.split('//')[1], '-R',
                   '%s:localhost:%s' % (response.remote_port, port)]  # No response.session_token!
        print (command)
        p = subprocess.Popen(command,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=False)
        run_method_with_timeout(lambda: wait_for_response(lambda: p.poll() is not None, timeout=10, throw=False), 10, raise_exception=False)
        if p.returncode is not None:
            print (p.communicate())
        self.assertEqual(p.returncode, None)


    def test_request_restart_while_still_running(self):
        port_out = self.osinteraction.get_open_port()
        session = Session()
        session.local_port = port_out
        session.server_session_token = None

        openport = start_openport_session(self, session)
        print('session started')
        sleep(30)
        openport.start_port_forward(session)







if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
