Summary: Opens a port from your pc to the internet.
Name: openport
Version: 1.0.2
Release: 1
License: GPL
Group: Tools/Networking
Url: htts://openport.io

%description
TODO


%prep
tar -cvf openport-1.0.2.tar.gz $RPM_BUILD_DIR/../../../client/ 


%build
tar -xf *.tar.gz
cd client
virtualenv env --python=/usr/local/bin/python2.7
env/bin/pip install -r requirements.pip
cd $RPM_BUILD_DIR/client
./create_exes.sh


%install
mkdir -p $RPM_BUILD_ROOT/usr/lib/openport
cp $RPM_BUILD_DIR/client/dist/openport/* $RPM_BUILD_ROOT/usr/lib/openport/ -r

mkdir -p $RPM_BUILD_ROOT/etc/init
cp $RPM_BUILD_DIR/../fs/etc/init/openport.conf $RPM_BUILD_ROOT/etc/init/

%clean
rm -rf $RPM_BUILD_ROOT

%files
#%defattr(-,root,root)
#%doc README TODO COPYING ChangeLog

/usr/lib/openport/
/etc/init/openport.conf


%post
ln -s /usr/lib/openport/openport /usr/bin/openport
initctl reload-configuration

%postun
rm /usr/bin/openport

%global __os_install_post %{nil}

