#!/bin/sh

source ../../openport/apps/openport_app_version.py

export PATH="$PATH:/usr/local/bin"

# get a mac developer licence.
# in xcode, request a "Developer ID Installer" under Preferences>Accounts>View Details

# for the summary image: make it 14 cm wide.

sed "s/\\\$VERSION\\\$/$VERSION/g" packages/Openport.pkgproj > packages/Openport.pkgproj.tmp

packagesbuild -v packages/Openport.pkgproj.tmp

# Login your build user via the GUI and open Keychain Access. Select your signing private key, 
# right-click, choose Get Info, change to the Access Control tab and select the "Allow all applications to access this item".


#codesign --force --sign "Developer ID Application: Jan De Bleser" packages/build/Openport.pkg

hdiutil create -volname Openport_$VERSION -srcfolder packages/build -ov -format UDZO Openport_$VERSION.dmg

md5 -r *.dmg > hash-mac.md5
