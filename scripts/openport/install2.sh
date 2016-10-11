#!/bin/sh

PYTHON_LOCATION=/usr/local/lib/python2.7.9

current_dir=$(pwd)

sudo apt-get install -y python-pip python-virtualenv python-dev libsqlite3-dev libffi-dev libssl-dev
#sudo apt-get install python-wxgtk2.8 python-wxtools wx2.8-doc wx2.8-examples wx2.8-headers wx2.8-i18n
# brew install phantomjs python-pyphantomjs

cd ~/Downloads

wget https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz
tar xfz Python-2.7.9.tgz
cd Python-2.7.9/
./configure --prefix $PYTHON_LOCATION --enable-shared --enable-unicode=ucs4
make
sudo make altinstall

echo "export LD_LIBRARY_PATH=$PYTHON_LOCATION/lib/" >> ~/.bashrc
export LD_LIBRARY_PATH="$PYTHON_LOCATION/lib/"


cd $current_dir
./install_wx_ubuntu.sh

virtualenv env --python=$PYTHON_LOCATION/bin/python --no-site-packages
#virtualenv env

site_packages=$PYTHON_LOCATION/lib/python2.7/site-packages

cd env/lib/python2.7/site-packages/
ln -s $site_packages/wx-3.0-gtk2/ .
ln -s $site_packages/wx.pth .
ln -s $site_packages/wxversion.py .

cd ../../../..

env/bin/pip install -r requirements.txt -r requirements.gui.txt

env/bin/python apps/openport_app.py

#sudo ln -s -f $(pwd)/openport-manager /etc/init.d/openport-manager
#sudo update-rc.d openport-manager defaults
