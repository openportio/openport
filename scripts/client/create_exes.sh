#!/bin/sh
env/bin/pyinstaller apps/openport_app.py --clean --onefile --name openport
env/bin/pyinstaller --clean openport_gui.spec


#If the exe fails with "cannot import _counter":
# wget https://github.com/pyinstaller/pyinstaller/tarball/develop
# tar -xf develop
# cd pyinstaller-pyinstaller-*
# ../env/bin/python setup.py
# cd ..
# And try again
