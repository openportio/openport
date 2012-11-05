from distutils.core import setup
import zipfile
import pkg_resources
import py2exe
import sys

setup(
    windows=['apps/openportit.py', 'tray/openporttray.py'],
    data_files=['tray/logo-base.png', 'apps/server.pem']
)
