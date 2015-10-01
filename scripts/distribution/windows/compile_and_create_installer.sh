cd $(dirname $0)
git pull
cd ../../client
bash -ex create_exes_win.sh
cd ../distribution/windows
c:/python27/python create_installer.py
