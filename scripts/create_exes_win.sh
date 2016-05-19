#!/bin/sh
env/Scripts/pyinstaller --clean openport.spec -y
env/Scripts/pyinstaller --clean openport_win_no_console.spec -y
env/Scripts/pyinstaller --clean openport-gui.spec -y

./dist/openport/openport.exe --version