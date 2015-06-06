#!/bin/sh
rm -rf dist/*
env/bin/pyinstaller --clean openport.spec -y
env/bin/pyinstaller --clean openport_gui_mac.spec -y

#If the exe fails with "cannot import _counter":
# wget https://github.com/pyinstaller/pyinstaller/tarball/develop
# tar -xf develop
# cd pyinstaller-pyinstaller-*
# ../env/bin/python setup.py
# cd ..
# And try again
