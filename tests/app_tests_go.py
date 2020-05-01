import subprocess
import unittest

import xmlrunner

from tests.app_tests import AppTests


class GoAppTests(AppTests):
    openport_exe = ['/Users/jan/swprojects/openport-go-client/openport']
    restart_shares = 'restart-sessions'
    kill = 'kill'
    kill_all = 'kill-all'
    version = 'version'
    app_version = '2.0.0'
    forward = 'forward'
    list = 'list'

    @classmethod
    def setUpClass(cls):
        exit_code, output = subprocess.getstatusoutput("/Users/jan/swprojects/openport-go-client/build.sh")
        print(output)
        assert exit_code == 0, exit_code


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
