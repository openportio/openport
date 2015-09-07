#!/bin/bash

set -ex
current_dir=$(pwd)

sudo apt-get install -y libgtk2.0-dev
sudo apt-get install -y libgstreamer-plugins-base0.10-dev 
sudo apt-get install -y libgl1-mesa-dev
sudo apt-get install -y libglu1-mesa-dev
sudo apt-get install -y libopenal-dev

#sudo apt-get install gstreamer-0.10
#sudo apt-get install libgstreamer0.10-dev
#sudo apt-get install libsdl-mixer1.2-dev
#sudo apt-get install libsdl-net1.2-dev

cd ~/Downloads
wget http://downloads.sourceforge.net/wxpython/wxPython-src-3.0.2.0.tar.bz2
tar -xf wxPython-src-3.0.2.0.tar.bz2

cd wxPython-src-3.0.2.0/wxPython

sudo /usr/local/lib/python2.7.9/bin/python build-wxpython.py --install prefix=/usr/local/lib/python2.7.9/

cd $current_dir
