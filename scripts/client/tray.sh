#!/bin/sh
cd $(dirname $0)

env/bin/python tray/openporttray.py --no-gui
