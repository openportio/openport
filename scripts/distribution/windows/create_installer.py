import sys
import os
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'client'))

from app.version import VERSION

def run_command(c):
	p = subprocess.Popen(c, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
	p.wait()
	c = p.communicate()
	print c[0]
	print c[1]

command = ["C:\Program Files (x86)\NSIS\makensis.exe", "/DVERSION=%s" % VERSION, "clean.nsi"]
print command
run_command(command)

#signtool_path = "C:\\Program Files\\Microsoft SDKs\\Windows\\v7.1\\bin\\signtool.exe"
signtool_path = "C:\\Program Files\\Microsoft SDKs\\Windows\\v6.0A\\bin\\signtool.exe"
run_command([signtool_path, 'sign',  '/p',  'terashare',  '/f', 'Danger Software.p12', 'terashare_windows_v%s.exe' % VERSION])

raw_input("press any key to continue...")