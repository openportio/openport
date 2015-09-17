#!/bin/sh
env/Scripts/pyinstaller --clean openport.spec -y
env/Scripts/pyinstaller --clean openport_no_console.spec -y
env/Scripts/pyinstaller --clean openport-gui.spec -y
