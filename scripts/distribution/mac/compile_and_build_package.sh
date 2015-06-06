#!/bin/sh

cd ../../client
bash -ex ./create_exes_mac.sh

codesign --force --sign "Developer ID Application: Jan De Bleser" dist/openport
codesign --force --sign "Developer ID Application: Jan De Bleser" dist/Openport.app

cd ../distribution/mac
bash -ex ./build.sh
