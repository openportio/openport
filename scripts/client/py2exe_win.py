from distutils.core import setup
import zipfile
import pkg_resources
import py2exe
import sys

setup(
    windows=[
        {
            'script': 'tray/openporttray.py',
            'icon_resources': [(1, 'resources/logo-base.ico')]
        },
        {
            'script': 'apps/openportit.py',
            'icon_resources': [(1, 'resources/logo-base.ico')]
        },
        {
            'script': 'apps/openport_app.py',
            'icon_resources': [(1, 'resources/logo-base.ico')]
        }
    ],
    data_files=['resources/logo-base.ico', 'resources/server.pem']
)
