import os
import unittest

import xmlrunner

if __name__ == '__main__':
    output_folder = os.environ.get('TEST_OUTPUT_PATH', '/test-results')
    unittest.main(module=None, testRunner=xmlrunner.XMLTestRunner(output=output_folder),
                  failfast=False, buffer=False, catchbreak=False,
                  argv=["", "discover", "-p", "app_tests.py"])
