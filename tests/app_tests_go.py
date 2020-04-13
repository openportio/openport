import subprocess
import unittest

import xmlrunner

from tests.app_tests import AppTests


class GoAppTests(AppTests):
    openport_exe = ['/Users/jan/swprojects/openport-go-client/openport']
    restart_shares = 'restart-shares'
    kill = 'kill'
    kill_all = 'kill-all'

    @classmethod
    def setUpClass(cls):
        print(subprocess.getoutput("/Users/jan/swprojects/openport-go-client/build.sh"))


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
