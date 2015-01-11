#!/bin/sh

package=$(ls -d build/*.pkg)

echo $package

/usr/bin/productsign --sign "3rd Party Mac Developer Installer: Jan De Bleser (3FJPW62YLR)" "$package" "$package.signed.pkg"
