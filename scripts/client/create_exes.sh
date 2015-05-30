#!/bin/sh
env/bin/pyinstaller --clean openport.spec -y
env/bin/pyinstaller --clean openport_gui.spec -y

codesign --force --sign "Developer ID Application: Jan De Bleser" dist/openport
codesign --force --sign "Developer ID Application: Jan De Bleser" dist/Openport.app


#If the exe fails with "cannot import _counter":
# wget https://github.com/pyinstaller/pyinstaller/tarball/develop
# tar -xf develop
# cd pyinstaller-pyinstaller-*
# ../env/bin/python setup.py
# cd ..
# And try again
