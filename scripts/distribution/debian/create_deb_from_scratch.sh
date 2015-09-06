cd "$( dirname "${BASH_SOURCE[0]}" )"

git pull
cd ../../client
env/bin/pip install -r requirements.pip
bash -ex ./create_exes.sh
cd ../distribution/debian
bash -ex ./createdeb.sh
