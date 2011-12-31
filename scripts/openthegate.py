#curl ...
import os
from sys import argv
import subprocess
import signal
import time

if len(argv) < 2:
    print 'please input the port'
    exit(1)

def request_port(server_ip, key):
    """requests a port on the server using the openthegate protocol
        return a tuple with (error_code, server_ip, server_port)
    """

    import urllib, urllib2

    url = 'http://%s/post' % server_ip

    values = {'public_key' : key,}

    try:
        data = urllib.urlencode(values)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        the_page = response.read()
        print the_page
        parts = the_page.split()
        if len(parts) < 3 or parts[0] != 'ok':
            return parts[0],0,0
        else:
            return 0, parts[1], parts[2]
    except Exception, detail:
        print "Err ", detail
        return 2,0,0


def handleSigTERM(signum, frame):
    global s
    print 'killing process %s' % s.pid
    os.kill(s.pid, signal.SIGKILL)
    exit(3)

signal.signal(signal.SIGTERM, handleSigTERM)
signal.signal(signal.SIGINT, handleSigTERM)


key_file = os.path.join(os.path.expanduser('~'), '.ssh', 'id_rsa.pub') #todo
key = ''
f = open(key_file, 'r')
key = f.readline()
if key == '':
    print 'could not read key: %s' % key_file
    exit(4)

http_server_ip='46.137.72.214'

(error_code, server_ip, server_port) = request_port(http_server_ip, key)

if not error_code:
    exit(5)

local_port=argv[1]
timeout=2

s = subprocess.Popen(['ssh', '-R', '*:%s:localhost:%s' %(server_port, local_port), 'open@%s' % server_ip, 'sleep', '%s' % timeout],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)

time.sleep(3)

if s.poll() != '':
    print 'an error has occurred:\n%s ' % s.communicate()[0]
    exit(2)

print u'you are now connected, you port %S can now be accessed on on %s:%s' % (local_port, server_ip, server_port)

while s.poll() is None:
    output = s.communicate()[0]
    if output != '':
        print 'ssh: %s ' % output
    time.sleep(1)



