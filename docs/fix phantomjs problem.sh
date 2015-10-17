#!/bin/bash

sudo apt-get remove phantomjs

sudo unlink /usr/local/bin/phantomjs
sudo unlink /usr/local/share/phantomjs
sudo unlink /usr/bin/phantomjs

cd /usr/local/share

sudo wget https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-1.9.7-linux-x86_64.tar.bz2

#Extract the files to directory

tar xjf phantomjs-1.9.7-linux-x86_64.tar.bz2

#Move files to Phantom’s directory

sudo ln -s /usr/local/share/phantomjs-1.9.7-linux-x86_64/bin/phantomjs /usr/local/share/phantomjs;

sudo ln -s /usr/local/share/phantomjs-1.9.7-linux-x86_64/bin/phantomjs /usr/local/bin/phantomjs;

sudo ln -s /usr/local/share/phantomjs-1.9.7-linux-x86_64/bin/phantomjs /usr/bin/phantomjs

#To check if completed, just type:

phantomjs --version

#Must appear: 1.9.7