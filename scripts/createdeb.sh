#!/bin/sh

VERSION=2.0.0

APPLICATION=openport
PACKAGE=openport-$VERSION
TARBALL=openport_$VERSION.orig.tar.gz

sudo apt-get --yes install build-essential autoconf automake autotools-dev dh-make debhelper devscripts fakeroot xutils lintian pbuilder python-dev python-pip python-virtualenv libsqlite3-dev

# if you have errors from locale: sudo dpkg-reconfigure locales

rm -rf $PACKAGE
mkdir $PACKAGE
mkdir -p $PACKAGE/usr/bin
#mkdir -p $PACKAGE/etc/init.d
cp client/dist/* $PACKAGE/usr/bin/ -r
cp client/openport.startup $PACKAGE/etc/init.d/openport-manager.startup
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
dch --create -v $(echo $VERSION)-1 --package $APPLICATION "TODO 12321"
debuild -us -uc

cd ../..
sudo rm -rf /usr/bin/openport
killall python
sudo dpkg -i package/openport_$(echo $VERSION)-1_*.deb
openport
