import sys
import os
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'client'))

from apps.openport_app_version import VERSION

def run_command(c):
	p = subprocess.Popen(c, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
	p.wait()
	c = p.communicate()
	print c[0]
	print c[1]
	return c

command = ["C:\Program Files (x86)\NSIS\makensis.exe", "/DVERSION=%s" % VERSION, "clean.nsi"]
print command
run_command(command)

#signtool_path = "C:\\Program\ Files\\Microsoft\ SDKs\\Windows\\v7.1\\bin\\signtool.exe"
signtool_path = "C:\\Program Files\\Microsoft SDKs\\Windows\\v6.0A\\bin\\signtool.exe"

# As admin, run 'mmc.exe'
# From 'file' add snap in 'certificates' for 'this computer'
# From 'Certificates > more actions' click 'import'
# Browse to the Danger Software.p12 certificate
# Add it to 'Trusted Root Certification Authorities' and to 'Personal'

command = [signtool_path, 'sign',  '/sm', '/a', '/v', '/sm', '/s', 'My', '/n', 'Danger Software', 'openport_%s.exe' %VERSION]
print '" "'.join(command)
run_command(command)

with open('hash-windows.md5', 'wb') as f:
	output = run_command(['md5sum', 'Openport_%s.exe' % VERSION])[0]
	f.write(output.replace('\r\n', '\n'))

#raw_input("press any key to continue...")
