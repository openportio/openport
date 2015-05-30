#!/bin/sh

source ../../client/apps/openport_app_version.py

# get a mac developer licence.
# in xcode, request a "Developer ID Installer" under Preferences>Accounts>View Details

# for the summary image: make it 14 cm wide.

sed "s/\\\$VERSION\\\$/$VERSION/g" packages/Openport.pkgproj > packages/Openport.pkgproj.tmp

packagesbuild -v packages/Openport.pkgproj.tmp

codesign --force --sign "Developer ID Application: Jan De Bleser" packages/build/Openport.pkg

hdiutil create -volname Openport_$VERSION -srcfolder packages/build -ov -format UDZO Openport_$VERSION.dmg
