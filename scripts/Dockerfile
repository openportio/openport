FROM ubuntu:14.04
MAINTAINER JanDeBleser

ENV LANG C.UTF-8
RUN apt-get update
RUN /usr/bin/apt-get install -y git python-pip libsqlite3-dev libffi-dev libssl-dev
RUN apt-get install wget
RUN wget https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz ;\
tar xfz Python-2.7.9.tgz ;\
cd Python-2.7.9/ ;\
./configure --enable-shared --enable-unicode=ucs4 ;\
make ;\
sudo make install

#cd $current_dir
#./install_wx_ubuntu.sh

#site_packages=$PYTHON_LOCATION/lib/python2.7/site-packages

#cd env/lib/python2.7/site-packages/
#ln -s $site_packages/wx-3.0-gtk2/ .
#ln -s $site_packages/wx.pth .
#ln -s $site_packages/wxversion.py .

#cd ../../../..

ADD openport/requirements.txt /apps/openport/scripts/openport/requirements.txt
RUN apt-get install -y python-dev

RUN wget https://bootstrap.pypa.io/get-pip.py ; python get-pip.py


RUN pip install -r /apps/openport/scripts/openport/requirements.txt 
#-r requirements.gui.txt

RUN useradd docker
RUN mkhomedir_helper docker
WORKDIR /apps/openport/
CMD sleep infinity
