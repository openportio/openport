#!/bin/bash
ps -ef | grep python | grep openport | grep -v grep | awk '{print $2}' | xargs -r kill || echo 'nothing to kill'
cd "$( cd "$( dirname "$0" )" && pwd )"
virtualenv env
#sudo apt-get install libmysqlclient-dev python-dev nodejs sloccount libffi-dev libssl-dev python-virtualenv
#env/bin/easy_install -U distribute
#env/bin/easy_install unittest-xml-reporting
env/bin/pip install -r requirements.pip
env/bin/pip install -r test-requirements.pip
env/bin/nosetests --nocapture --with-xunit tests/*_tests.py || echo there was an error: $?
#./create_exes.sh
ps -ef | grep python | grep openport | grep -v grep | awk '{print $2}' | xargs -r kill || echo 'nothing to kill'
