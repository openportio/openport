#!/bin/sh
cd $(dirname $(readlink $0))
env/bin/python apps/openport_app.py --local-port $1 --no-gui
