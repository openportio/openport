source ../../client/apps/openport_app_version.py
rpmbuild --define "_topdir ${PWD}" -ba SPECS/openport.spec
