import daemon
import sys
from time import sleep
print 'outside'
with daemon.DaemonContext(detach_process=False, stderr=sys.stderr, stdout=sys.stdout):
    print 'inside'
    sleep(20)
print 'out'


