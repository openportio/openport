cd "$( dirname "${BASH_SOURCE[0]}" )"
set -ex

export LD_LIBRARY_PATH=/usr/local/lib/python2.7.9/lib/

git pull
cd ../../openport
virtualenv env
env/bin/pip install -r requirements.txt
cd ../distribution/debian
bash -ex create_exes_and_deb.sh $1
