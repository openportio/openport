cd "$( dirname "${BASH_SOURCE[0]}" )"
set -ex

git pull
cd ../../client
env/bin/pip install -r requirements.pip
bash -ex ./create_exes.sh
cd ../distribution/debian
bash -ex create_exes_and_deb.sh
