#!/bin/sh
env/Scripts/pyinstaller apps/openport_app.py --clean --onefile --name openport
env/Scripts/pyinstaller manager/manager_windows_service.py --clean --onefile --name openport_service
