#!/bin/sh

package=$(ls -d build/*.pkg)

for f in "$package"
do
    echo "$f"
    pkgutil --flatten "$f" "$f.flat.pkg"

    /usr/bin/productsign --sign "3rd Party Mac Developer Installer: Jan De Bleser (3FJPW62YLR)" "$f.flat.pkg" "$f.signed.pkg"
done


#/usr/sbin/pkgutil --check-signature *.pkg