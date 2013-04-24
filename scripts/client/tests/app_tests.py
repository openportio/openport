from time import sleep

__author__ = 'Jan'
import subprocess
import unittest
import os
import fcntl
import signal

from test_utils import SimpleTcpServer, SimpleTcpClient, get_open_port, lineNumber


def nonBlockRead(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return output.read()
    except:
        return False

class app_tests(unittest.TestCase):
    def setUp(self):
        self.processes_to_kill = []

    def tearDown(self):
        for p in self.processes_to_kill:
            try:
                os.kill(p.pid, signal.SIGKILL)
            except Exception, e:
                pass

    def testOpenportApp(self):
        port = get_open_port()
        s = SimpleTcpServer(port)
        s.runThreaded()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        p = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port, '--no-gui', '--no-tray'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p)
        sleep(5)
        process_output = nonBlockRead(p.stdout)
        print 'output: ', process_output

        if p.poll() is not None: # process terminated
            print 'error: %s' % nonBlockRead(p.stderr)
            self.fail('p.poll() should be None but was %s' % p.poll())

        remote_host, remote_port = self.getRemoteHostAndPort(process_output)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        c.close()
        s.close()
        p.kill()

    def check_application_is_still_alive(self, p):
        if p.poll() is not None: # process terminated
            print 'error: %s' % nonBlockRead(p.stderr)
            self.fail('p_app.poll() should be None but was %s' % p.poll())

    def testTray(self):
        db_file = os.path.join(os.path.dirname(__file__), 'testfiles', 'tmp_openport.db')
        try:
            os.remove(db_file)
        except OSError:
            pass

        port = get_open_port()
        s = SimpleTcpServer(port)
        s.runThreaded()

        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        p_tray = subprocess.Popen(['env/bin/python', 'tray/openporttray.py', '--no-gui', '--database', db_file],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p_app = subprocess.Popen(['env/bin/python', 'apps/openport_app.py', '--local-port', '%s' % port, '--no-gui',
                                  '--no-tray', '--verbose'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_tray)
        self.processes_to_kill.append(p_app)
        sleep(5)

        process_output = nonBlockRead(p_app.stdout)
        print lineNumber(), 'output: ', process_output

        self.check_application_is_still_alive(p_tray)
        self.check_application_is_still_alive(p_app)

        remote_host, remote_port = self.getRemoteHostAndPort(process_output)
        print lineNumber(), "remote port:", remote_port

        os.kill(p_app.pid, signal.SIGKILL)
        p_tray.kill()

        print lineNumber(),  "p_app stdout:", nonBlockRead(p_app.stdout)

        p_tray = subprocess.Popen(['env/bin/python', 'tray/openporttray.py', '--no-gui', '--database', db_file, '--verbose'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_tray)
        sleep(10)

        print lineNumber(),  "tray.stdout:", nonBlockRead(p_tray.stdout)
        print lineNumber(),  "tray.stderr:",nonBlockRead(p_tray.stderr)
        self.check_application_is_still_alive(p_tray)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        p_tray.kill()

        response = c.send(request)
        self.assertNotEqual(request, response.strip())

        c.close()
        s.close()



    def getRemoteHostAndPort(self, output):
        import re
        m = re.search(r'Now forwarding remote port ([^:]*):(\d*) to localhost', output)
        return m.group(1), int(m.group(2))