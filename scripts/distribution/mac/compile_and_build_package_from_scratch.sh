#!/bin/sh

cd $(dirname $0)

git pull

start_dir=$(pwd)

cd ../../client
env/bin/pip install -r requirements.pip -r requirements.gui.txt

cd $start_dir

bash -ex compile_and_build_package.sh

