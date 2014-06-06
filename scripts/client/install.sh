#!/bin/sh
#sudo apt-get install python-pip python-virtualenv python-dev libsqlite3-dev phantomjs libffi-dev
# brew install phantomjs
virtualenv env
env/bin/pip install -r requirements.pip

sudo ln -s -f $(pwd)/openport-manager /etc/init.d/openport-manager
sudo update-rc.d openport-manager defaults
