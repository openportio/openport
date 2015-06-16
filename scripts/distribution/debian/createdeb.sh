#!/bin/sh

source ../../client/apps/openport_app_version.py

echo $VERSION

APPLICATION=openport
PACKAGE=openport-$VERSION
TARBALL=openport_$VERSION.orig.tar.gz

sudo apt-get --yes install build-essential autoconf automake autotools-dev dh-make debhelper devscripts fakeroot xutils lintian pbuilder python-dev python-pip python-virtualenv libsqlite3-dev

# if you have errors from locale: sudo dpkg-reconfigure locales

sudo dpkg --remove $APPLICATION || echo "$APPLICATION not installed"
# If the uninstall keeps giving errors:
# rm -rf /var/lib/dpkg/info/$APPLICATION.*



rm -rf $PACKAGE
mkdir $PACKAGE
mkdir -p $PACKAGE/usr/lib
cp ../../client/dist/* $PACKAGE/usr/lib/ -r

tar -czf $TARBALL $PACKAGE
rm -rf $PACKAGE
rm -rf package
mkdir -p package
cd package
mv ../$TARBALL .
tar -xf $TARBALL

pwd
rm -f debian/source/include-binaries
ls ../package/openport-*/usr/lib/openport/*.so.* >> ../debian/source/include-binaries
ls ../package/openport-*/usr/lib/openport/openport >> ../debian/source/include-binaries
ls ../package/openport-*/usr/lib/openport_gui/*.so.* >> ../debian/source/include-binaries
ls ../package/openport-*/usr/lib/openport_gui/openport_gui >> ../debian/source/include-binaries
ls ../package/openport-*/usr/lib/openport/alembic/versions/*.pyc >> ../debian/source/include-binaries

cd $PACKAGE
cp ../../debian . -r
echo "8" > debian/compat
ls debian/
DEB_BUILD_OPTIONS="noopt nostrip"
dch --create -v $(echo $VERSION)-1 --package $APPLICATION "TODO 12321"
debuild -us -uc

cd ../..
sudo rm -rf /usr/bin/openport
#if [ -e /etc/init.d/openport ] ; then
#	sudo rm -f /etc/init.d/openport
#fi
sudo rm -f /etc/init.d/openport-manager

sudo killall python || echo "no python process found"
sudo dpkg -i package/openport_$(echo $VERSION)-1_*.deb
openport -h
