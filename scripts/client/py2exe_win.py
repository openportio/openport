from distutils.core import setup
import zipfile
import pkg_resources
import py2exe
import sys

setup(
    windows=['openportit.py', 'openporttray.py'],
    data_files=['logo-base.png', 'server.pem']
)
#setup(windows=['openporttray.py'])
