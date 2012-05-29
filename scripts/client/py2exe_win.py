from distutils.core import setup
import zipfile
import pkg_resources
import py2exe
import sys

setup(
    windows=['openportit.py', 'application.py'],
    data_files=['logo-base.png']
)
#setup(windows=['application.py'])
