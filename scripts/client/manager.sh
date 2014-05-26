#!/bin/sh

cd $(dirname $0)

env/bin/python manager/openportmanager.py &
trap "kill $!" 2 3 15
wait
