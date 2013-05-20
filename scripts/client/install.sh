#!/bin/sh
#sudo apt-get install python-pip python-virtualenv python-dev libsqlite3-dev
virtualenv env
env/bin/pip install -r requirements.pip

sudo ln -s -f $(pwd)/openport-tray /etc/init.d/openport-tray
sudo update-rc.d openport-tray defaults
