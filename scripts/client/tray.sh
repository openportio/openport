#!/bin/sh

cd $(dirname $0)

env/bin/python tray/openporttray.py --no-gui &
trap "kill $!" 2 3 15
wait
