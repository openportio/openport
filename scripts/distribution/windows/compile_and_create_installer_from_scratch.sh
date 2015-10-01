cd $(dirname $0)
start_dir=$(pwd)
git pull
cd ../../client
env/scripts/pip install -r requirements.pip -r requirements.gui.txt
cd $start_dir
pwd
bash -ex compile_and_create_installer.sh