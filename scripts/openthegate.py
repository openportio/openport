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
#        print the_page
        parts = the_page.split()
        if len(parts) < 3 or parts[0] != 'ok':
            print parts[0]
            exit(8)
        else:
            return 0, parts[1], parts[2]
    except Exception, detail:
        print "Err ", detail
        exit(9)


def handleSigTERM(signum, frame):
    global s
    print 'killing process %s' % s.pid
    try:
        os.kill(s.pid, signal.SIGKILL)
    except OSError:
        pass
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

if error_code:
    exit(5)

local_port=argv[1]
timeout=5000

command_list = ['ssh', '-R', '*:%s:localhost:%s' %(server_port, local_port), 'open@%s' % server_ip, '-o', 'StrictHostKeyChecking=no', '-o', 'ExitOnForwardFailure=yes', 'sleep', '%s' % timeout]
#print ' '.join(command_list)

s = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
time.sleep(2)

if s.poll() is not None:
    output = '%s - %s' % (s.stdout.read(), s.stderr.read())
    print '%s ' % output
    exit(7)

print u'you are now connected, you port %s can now be accessed on on %s:%s' % (local_port, server_ip, server_port)
s.wait()
