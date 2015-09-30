cd "$( dirname "${BASH_SOURCE[0]}" )"
set -ex

export LD_LIBRARY_PATH=/usr/local/lib/python2.7.9/lib/

git pull
cd ../../client
env/bin/pip install -r requirements.pip
bash -ex ./create_exes.sh
cd ../distribution/debian
bash -ex create_exes_and_deb.sh
