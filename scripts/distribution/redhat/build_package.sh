source ../../client/apps/openport_app_version.py
rm BUILD/*.tar.gz
rpmbuild --define "_topdir ${PWD}" -ba SPECS/openport.spec
