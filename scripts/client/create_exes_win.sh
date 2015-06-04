#!/bin/sh
env/Scripts/pyinstaller --clean openport.spec -y
env/Scripts/pyinstaller --clean openport_gui.spec -y
