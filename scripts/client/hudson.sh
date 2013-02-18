cd scripts/client
virtualenv env
#sudo apt-get install libmysqlclient-dev python-dev nodejs sloccount gcc libsqlite3-dev
#mysql -uroot -e "grant all privileges on test_openthegate.* to 'hudson'@'localhost';" -p
env/bin/easy_install -U distribute
env/bin/easy_install unittest-xml-reporting
env/bin/pip install -r requirements.pip
env/bin/python tests/integrationtests.py
