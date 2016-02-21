cd $(dirname $0)
cd ../../client
yum install git
yum install python-virtualenv
virtualenv env
yum install gcc
yum install libsqlite3-devel libffi-devel openssl-devl
env/bin/pip install -r requirements.pip

