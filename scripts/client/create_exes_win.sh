#!/bin/sh
env/Scripts/pyinstaller --clean openport_win.spec -y
env/Scripts/pyinstaller --clean openport_win_no_console.spec -y
env/Scripts/pyinstaller --clean openport-gui.spec -y
