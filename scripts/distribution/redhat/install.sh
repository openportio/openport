cd $(dirname $0)
cd ../../client
sudo yum install -y git python-devel gcc libsqlite3-devel libffi-devel openssl-devel rpm-build
curl https://bootstrap.pypa.io/get-pip.py |python -
pip install virtualenv
virtualenv env
env/bin/pip install -r requirements.pip
