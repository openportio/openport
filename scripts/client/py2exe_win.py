from distutils.core import setup
import zipfile
import pkg_resources
import py2exe
import sys

setup(
    windows=['tray/openporttray.py','apps/openportit.py', 'apps/openport_app.py'],
    data_files=['resources/logo-base.png', 'resources/server.pem']
)
