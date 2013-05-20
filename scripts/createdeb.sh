#!/bin/sh

VERSION=1.0

APPLICATION=openport-client
PACKAGE=openport-client-$VERSION
TARBALL=openport-client_$VERSION.orig.tar.gz

#sudo apt-get install build-essential autoconf automake autotools-dev dh-make debhelper devscripts fakeroot xutils lintian pbuilder

mkdir $PACKAGE
cp client $PACKAGE/ -r
tar -czf $TARBALL $PACKAGE
rm -rf $PACKAGE
rm -rf package
mkdir -p package
cd package
mv ../$TARBALL .
tar -xf $TARBALL
cd $PACKAGE
cp ../../debian . -r
echo "8" > debian/compat
ls debian/
dch --create -v $(echo $VERSION)-1 --package $APPLICATION 
debuild -us -uc

cd ../..
sudo dpkg -i package/openport-client_1.0-1_i386.deb
