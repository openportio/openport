#!/bin/bash
ps -ef | grep python | grep openport | grep -v grep | awk '{print $2}' | xargs -r kill
cd scripts/client
virtualenv env
#sudo apt-get install libmysqlclient-dev python-dev nodejs sloccount libffi-dev
#mysql -uroot -e "grant all privileges on test_openport.* to 'hudson'@'localhost';" -p
#env/bin/easy_install -U distribute
#env/bin/easy_install unittest-xml-reporting
env/bin/pip install -r requirements.pip
env/bin/pip install -r test-requirements.pip
env/bin/nosetests --nocapture --with-xunit tests/*_tests.py || echo there was an error: $?
./create_exes.sh
