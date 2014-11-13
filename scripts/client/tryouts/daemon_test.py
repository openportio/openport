import daemon
import os
from time import sleep
import sys
#with file('outside.txt', 'w'):
#    pass
print 'outside'
a = 'a'
with daemon.DaemonContext(working_directory=os.curdir, detach_process=True, stderr=sys.stderr, stdout=sys.stdout):
    print 'inside'
    print a
    #with file('inside.txt', 'w') as f:
    #    print 'writing'
    #    f.write('kuch')
    sleep(20)
    print 'done'
print 'out'


