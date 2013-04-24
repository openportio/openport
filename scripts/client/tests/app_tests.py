from time import sleep

__author__ = 'Jan'
import subprocess
import unittest
import os
import signal
from services import osinteraction

from test_utils import SimpleTcpServer, SimpleTcpClient, get_open_port, lineNumber
from services.utils import nonBlockRead


class app_tests(unittest.TestCase):
    def setUp(self):
        self.processes_to_kill = []
        self.osinteraction = osinteraction.getInstance()

    def tearDown(self):
        for p in self.processes_to_kill:
            try:
                os.kill(p.pid, signal.SIGKILL)
                p.wait()
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
        print 'localport :', port
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
        sleep(10)

        process_output = nonBlockRead(p_app.stdout)
        print lineNumber(), 'output: ', process_output

        self.check_application_is_still_alive(p_tray)
        self.check_application_is_still_alive(p_app)

        remote_host, remote_port = self.getRemoteHostAndPort(process_output)
        print lineNumber(), "remote port:", remote_port

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())
        c.close()
   #     s.close()

        os.kill(p_app.pid, signal.SIGKILL)
        self.assertNotEqual(p_app.wait(), None)
        while self.osinteraction.pid_is_running(p_app.pid):
            print "waiting for pid to be killed: %s" % p_app.pid
            sleep(1)
        os.kill(p_tray.pid, signal.SIGINT)
        print 'waiting for tray to be killed'
        p_tray.wait()
        print lineNumber(),  "tray.stdout:", nonBlockRead(p_tray.stdout)
        print lineNumber(),  "tray.stderr:", nonBlockRead(p_tray.stderr)

        print lineNumber(),  "p_app stdout:", nonBlockRead(p_app.stdout)

        sleep(5)

  #      s = SimpleTcpServer(port)
  #      s.runThreaded()

        p_tray2 = subprocess.Popen(['env/bin/python', 'tray/openporttray.py', '--no-gui', '--database', db_file, '--verbose'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.processes_to_kill.append(p_tray2)
        sleep(10)

        print lineNumber(),  "tray.stdout:", nonBlockRead(p_tray2.stdout)
        print lineNumber(),  "tray.stderr:",nonBlockRead(p_tray2.stderr)
        self.check_application_is_still_alive(p_tray2)

        c = SimpleTcpClient(remote_host, remote_port)
        request = 'hello'
        response = c.send(request)
        self.assertEqual(request, response.strip())

        os.kill(p_tray2.pid, signal.SIGINT)
        p_tray2.wait()
        print lineNumber(),  "tray.stdout:", nonBlockRead(p_tray2.stdout)
        print lineNumber(),  "tray.stderr:",nonBlockRead(p_tray2.stderr)

        response = c.send(request)
        self.assertNotEqual(request, response.strip())

        c.close()
        s.close()


    def getRemoteHostAndPort(self, output):
        import re
        m = re.search(r'Now forwarding remote port ([^:]*):(\d*) to localhost', output)
        return m.group(1), int(m.group(2))