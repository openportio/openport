import subprocess
import unittest

import xmlrunner

from tests.app_tests import AppTests
from pathlib import Path

openport_go_dir = Path(__file__).parents[2] / 'openport-go-client'


class GoAppTests(AppTests):
    openport_exe = [str(openport_go_dir / 'openport')]
    restart_shares = 'restart-sessions'
    kill = 'kill'
    kill_all = 'kill-all'
    version = 'version'
    app_version = '2.0.3'
    forward = 'forward'
    list = 'list'

    @classmethod
    def setUpClass(cls):
        exit_code, output = subprocess.getstatusoutput(str(openport_go_dir / "compile.sh"))
        print(output)
        assert exit_code == 0, exit_code


if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))

