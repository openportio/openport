import subprocess
import unittest

import xmlrunner

from tests.app_tests import AppTests


class GoAppTests(AppTests):
    openport_exe = ['/Users/jan/swprojects/openport-go-client/openport']
    restart_shares = 'restart-shares'

    @classmethod
    def setUpClass(cls):
        print(subprocess.getoutput("/Users/jan/swprojects/openport-go-client/build.sh"))

    def kill_openport_process(self, port):
        return subprocess.Popen(self.openport_exe + [
            'kill', str(port),
            '--database', self.db_file, '--verbose'],
                                stderr=subprocess.PIPE, stdout=subprocess.PIPE)


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
