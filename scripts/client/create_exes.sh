#!/bin/sh
env/bin/pyinstaller apps/openport_app.py --clean --onefile --name openport
env/bin/pyinstaller manager/openportmanager.py --clean --onefile
