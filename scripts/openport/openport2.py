#!/usr/bin/python

import os,sys
os.chdir(os.path.dirname(os.path.realpath(__file__)))

os.system('env/bin/python apps/openport_app.py --local-port %s' % sys.argv[1])
