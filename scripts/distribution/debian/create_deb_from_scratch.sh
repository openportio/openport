#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"
set -ex

export LD_LIBRARY_PATH=/usr/local/lib/python2.7.9/lib/

git pull
cd ../../openport
rm -rf env
virtualenv env --python=/usr/local/lib/python2.7.9/bin/python --no-site-packages
env/bin/pip install -r requirements.txt
cd ../distribution/debian
bash -ex create_exes_and_deb.sh $1
