from distutils.core import setup
import zipfile
import pkg_resources
import py2exe
import sys

setup(
    console=[
        {
            'script': 'manager/manager_windows_service.py',
        },
        {
            'script': 'apps/openport_app.py',
            'icon_resources': [(1, 'resources/logo-base.ico')]
        }
    ],
    options = {'py2exe': {'compressed':1,
                            'bundle_files': 1,
                            'excludes': ['Tkconstants', 'Tkinter']
                            },
    },
    data_files=['resources/logo-base.ico', 'resources/server.pem']
)
