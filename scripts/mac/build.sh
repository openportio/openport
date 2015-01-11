#!/bin/sh

# get a mac developer licence.
# in xcode, request a "Developer ID Installer" under Preferences>Accounts>View Details

# for the summary image: make it 14 cm wide.

packagesbuild -v packages/Openport.pkgproj

hdiutil create -volname Openport_0.9.1 -srcfolder packages/build -ov -format UDZO Openport_0.9.1.dmg
