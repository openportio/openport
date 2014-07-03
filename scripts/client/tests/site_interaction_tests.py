from time import sleep
import unittest
import os
import sys
import subprocess
import xmlrunner
import inspect

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from test_utils import run_command_with_timeout, get_remote_host_and_port, kill_all_processes
from services import osinteraction


class SiteInteractionTest(unittest.TestCase):

    def setUp(self):
        if os.path.exists('/usr/bin/phantomjs'):
            self.browser = webdriver.PhantomJS('/usr/bin/phantomjs')
        else:
            self.browser = webdriver.PhantomJS('/usr/local/bin/phantomjs')

        self.browser.set_window_size(1124, 850)
        #self.browser = webdriver.Firefox()
        self.processes_to_kill = []
        self.os_interaction = osinteraction.getInstance()

    def tearDown(self):
        kill_all_processes(self.processes_to_kill)
        self.browser.quit()

    def test_site_is_online(self):
        self.browser.get('http://test.openport.be/')
        self.browser.save_screenshot(os.path.join(os.path.dirname(__file__), 'testfiles', '%s.png' % inspect.stack()[0][3]))
        self.assertTrue('OpenPort' in self.browser.title)

    def login_to_site(self):
        self.browser.get('http://test.openport.be/user/login')
        elem = self.browser.find_element_by_name("username")
        elem.send_keys("jan")
        elem2 = self.browser.find_element_by_name("password")
        elem2.send_keys("test")
        elem.send_keys(Keys.RETURN)
        self.browser.save_screenshot(os.path.join(os.path.dirname(__file__), 'testfiles', '%s.png' % inspect.stack()[0][3]))


    def test_login_to_site(self):
        self.login_to_site()
        self.browser.save_screenshot(os.path.join(os.path.dirname(__file__), 'testfiles', '%s.png' % inspect.stack()[0][3]))
        self.assertTrue('Welcome, Subscriber' in self.browser.page_source)

    def remove_all_keys_from_account(self):
        self.browser.get('http://test.openport.be/user/keys')
        try:
            while True:
                js_confirm = 'window.confirm = function(){return true;}'
                self.browser.execute_script(js_confirm)
                elem = self.browser.find_element_by_partial_link_text("Remove")
                elem.click()
        except NoSuchElementException:
            pass

    def register_key(self, key_binding_token):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        print run_command_with_timeout(['env/bin/python', 'apps/openport_app.py', '--register-key',
                                        key_binding_token, '--server', 'test.openport.be'], 10)

    def test_add_key_to_account(self):
        self.login_to_site()

        self.remove_all_keys_from_account()

        key_binding_token = self.get_key_binding_token()
        self.register_key(key_binding_token)

        sleep(2)
        try:
            self.browser.get('http://test.openport.be/user/keys')
            self.browser.save_screenshot(os.path.join(os.path.dirname(__file__), 'testfiles', '%s.png' % inspect.stack()[0][3]))
            elem = self.browser.find_element_by_partial_link_text("Remove")
        except NoSuchElementException:
            self.fail('key not added to account')
        #todo: what if key is linked to different account? -> test

    def get_key_binding_token(self):
        self.browser.get('http://test.openport.be/user/keys')
        self.browser.save_screenshot(os.path.join(os.path.dirname(__file__), 'testfiles', '%s.png' % inspect.stack()[0][3]))
        try:
            code_elem = self.browser.find_elements_by_xpath("//*[contains(text(), '--register-key')]")[0]
        except IndexError:
            self.fail('register key div not found in DOM. Check screenshot %s.png' % inspect.stack()[0][3])
        return code_elem.text.strip().split()[-1]

    def test_kill_session(self):
        """ Start a session. Check that it exists on the server. Kill it. Make sure is doesn't restart."""

        self.login_to_site()
        key_binding_token = self.get_key_binding_token()
        self.register_key(key_binding_token)

        p = self.start_session(8888)
        sleep(5)
        process_output = self.os_interaction.get_all_output(p)
        print "process output: ", process_output
        remote_host, server_port = get_remote_host_and_port(process_output[0])
        print 'server port: %s' % server_port

        self.assertTrue(self.session_exists_on_site(server_port))
        self.kill_session(server_port)
        sleep(2)
        self.assertFalse(self.session_exists_on_site(server_port), 'session did not disappear')
        sleep(20)
        process_output = self.os_interaction.get_all_output(p)
        print "process output: ", process_output
        self.assertFalse(self.session_exists_on_site(server_port), 'session came back')

    def start_session(self, local_port):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % local_port,
                              '--start-manager', 'False', '--server', 'test.openport.be', '--verbose', '--manager-port',
                              '-1'],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        return p

    def session_exists_on_site(self, server_port):
        self.browser.get('http://test.openport.be/user/sessions')
        code_elements = self.browser.find_elements_by_xpath("//*[contains(text(), ':%s')]" % server_port)
        return len(code_elements) == 1

    def kill_session(self, server_port):
        self.browser.get('http://test.openport.be/user/sessions')
        try:
            js_confirm = 'window.confirm = function(){return true;}'
            self.browser.execute_script(js_confirm)
            #elem = self.browser.find_element_by_partial_link_text(":%s" % server_port)
            elem = self.browser.find_element_by_xpath("//td[contains(., ':%s')]/following-sibling::td[1]/a" % server_port)
            elem.click()
        except NoSuchElementException:
            self.fail("session not found")


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))