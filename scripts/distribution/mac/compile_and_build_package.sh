#!/bin/sh
source local_settings.sh

cd ../..
bash -ex ./create_exes_mac.sh


security -v unlock-keychain -p $PASSWORD "/Users/jan/Library/Keychains/login.keychain"

codesign --force --sign "Developer ID Application: Jan De Bleser" dist/openport
codesign --force --sign "Developer ID Application: Jan De Bleser" dist/Openport.app

cd distribution/mac
bash -ex ./build.sh
