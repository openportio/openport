git pull
cd client
env/bin/pip install -r requirements.pip
bash -ex ./create_exes.sh
cd ..
./createdeb.sh
