PYTHON_LOCATION=/usr/local/lib/python2.7.10
export LD_LIBRARY_PATH="$PYTHON_LOCATION/lib/"

source ../../client/apps/openport_app_version.py
rm BUILD/*.tar.gz
rpmbuild --define "_topdir ${PWD}" -ba SPECS/openport.spec
