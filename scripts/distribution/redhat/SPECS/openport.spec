Summary: Opens a port from your pc to the internet.
Name: openport
Version: 1.0.1
Release: 1
License: GPL
Group: Tools/Networking
Url: htts://openport.io

%description
TODO


%prep
tar -cvf openport-1.Â0..tar.gz $RPM_BUILD_DIR/../../../client/ 


%build
cd client
virtualenv env
env/bin/pip install -r requirements.pip
cd $RPM_BUILD_DIR/client
./create_exes.sh


%install
mkdir -p $RPM_BUILD_ROOT/usr/lib/openport
cp $RPM_BUILD_DIR/client/dist/openport/* $RPM_BUILD_ROOT/usr/lib/openport/ -r


%clean
rm -rf $RPM_BUILD_ROOT

%files
#%defattr(-,root,root)
#%doc README TODO COPYING ChangeLog

/usr/lib/openport/


%post
ln -s /usr/lib/openport/openport /usr/bin/openport


%global __os_install_post %{nil}

