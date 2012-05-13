from distutils.core import setup
import py2exe

setup(console=['openportit.py'])
setup(windows=['sharerequestsender.py', 'application.py'])
