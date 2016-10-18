#!/bin/bash
set -e
set -x
cd $(dirname $0)

rm -rf dist/*
#deactivate || echo ''
#source openport/env/bin/activate
export LD_LIBRARY_PATH=/Python-2.7.9/
pyinstaller --clean openport.spec -y

no_gui=0
for i in "$@" ; do
    if [[ $i = "--no-gui" ]] ; then
        no_gui=1
        break
    fi
done

if [[ $no_gui != 1 ]]
then
	pyinstaller --clean openport-gui.spec -y
fi

#If the exe fails with "cannot import _counter":
# wget https://github.com/pyinstaller/pyinstaller/tarball/develop
# tar -xf develop
# cd pyinstaller-pyinstaller-*
# ../env/bin/python setup.py
# cd ..
# And try again
