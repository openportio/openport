ARG FROMIMAGE=ubuntu:16.04

FROM $FROMIMAGE
ARG FROMIMAGE
RUN echo $FROMIMAGE > image_version

MAINTAINER JanDeBleser


ENV LANG C.UTF-8
RUN apt-get update
RUN /usr/bin/apt-get install -y git libsqlite3-dev libffi-dev libssl-dev make gcc
RUN apt-get install -y wget bzip2
RUN apt-get remove python
RUN apt-get autoremove
RUN wget https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz ;\
tar xfz Python-2.7.9.tgz
RUN cd Python-2.7.9/ ; ./configure --enable-shared --enable-unicode=ucs4
RUN cd Python-2.7.9/ ; make
RUN cd Python-2.7.9/ ; make install


#cd $current_dir
#./install_wx_ubuntu.sh

#site_packages=$PYTHON_LOCATION/lib/python2.7/site-packages

#cd env/lib/python2.7/site-packages/
#ln -s $site_packages/wx-3.0-gtk2/ .
#ln -s $site_packages/wx.pth .
#ln -s $site_packages/wxversion.py .

#cd ../../../..

ADD openport/requirements.txt /apps/openport/scripts/openport/requirements.txt
#RUN apt-get install -y python-dev

ENV LD_LIBRARY_PATH /Python-2.7.9
#RUN pip install urllib3 --upgrade
RUN wget https://bootstrap.pypa.io/get-pip.py ; python get-pip.py
RUN pip install pip --upgrade

RUN pip install -r /apps/openport/scripts/openport/requirements.txt 
#-r requirements.gui.txt

RUN pip uninstall -y pyinstaller
RUN pip uninstall -y setuptools
RUN pip uninstall -y setuptools

RUN git clone https://github.com/pyinstaller/pyinstaller.git
RUN cd pyinstaller/bootloader ; git reset --hard 7be200b5a6f179f6753ca5a51713f19103f23393 
RUN cd pyinstaller/bootloader ; python ./waf configure build install --no-lsb 
RUN pip install setuptools==19.2 
RUN cd pyinstaller ; pip install .


RUN useradd docker
RUN mkhomedir_helper docker

WORKDIR /apps/openport/
RUN apt-get install -y sudo
CMD sleep infinity
