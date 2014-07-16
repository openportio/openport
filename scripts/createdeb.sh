#!/bin/sh

VERSION=2.0.0

APPLICATION=openport-client
PACKAGE=openport-client-$VERSION
TARBALL=openport-client_$VERSION.orig.tar.gz

sudo apt-get install build-essential autoconf automake autotools-dev dh-make debhelper devscripts fakeroot xutils lintian pbuilder python-dev python-pip python-virtualenv libsqlite3-dev

# if you have errors from locale: sudo dpkg-reconfigure locales

mkdir $PACKAGE
mkdir -p $PACKAGE/usr/bin
mkdir -p $PACKAGE/etc/init.d
cp client/dist/* $PACKAGE/usr/bin/ -r
cp client/openport.startup $PACKAGE/etc/init.d/openport
#rm $PACKAGE/client/env -rf
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
DEB_BUILD_OPTIONS="noopt nostrip"
dch --create -v $(echo $VERSION)-1 --package $APPLICATION "test test"
debuild -us -uc

cd ../..
sudo rm -rf /usr/bin/openport
sudo dpkg -i package/openport-client_$(echo $VERSION)-1_*.deb
openport
