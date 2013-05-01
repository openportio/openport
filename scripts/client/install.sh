sudo apt-get install python-pip python-virtualenv python-dev libsqlite3-dev
virtualenv env
env/bin/pip install -r requirements.pip

ln -s $(dirname $1)/openport-tray /etc/init.d/openport-tray
update-rc.d openport-tray defaults
