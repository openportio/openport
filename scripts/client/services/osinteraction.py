import errno
import os
import platform
import subprocess
import sys
import signal

class OsInteraction(object):

    def __init__(self, use_logger=True):
        if use_logger:
            from services.logger_service import get_logger
            self.logger = get_logger('OsInteraction')

    def get_app_name(self):
        return os.path.basename(sys.argv[0])

    def start_openport_process(self, share, hide_message=True, no_clipboard=True, tray_port=8001):
#        print share.restart_command
        return self.start_process(share.restart_command)

    def start_process(self, args):
        p = subprocess.Popen(args,
                             bufsize=0, executable=None, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None,
                             universal_newlines=False, startupinfo=None, creationflags=0)
        return p


    def get_resource_path(self, path):
        dir = os.path.dirname( os.path.dirname( os.path.realpath( __file__ ) ) )
        if dir[-3:] == 'zip':
            dir = os.path.dirname(dir)
        else:
            dir = os.path.join(dir, 'resources')
        return os.path.join(dir, path)

    def get_app_data_path(self, filename=''):
        #Do not use the logger!
        try:
            os.makedirs(self.APP_DATA_PATH)
        except Exception:
            pass
        return os.path.join(self.APP_DATA_PATH, filename)

    def run_command_silent(self, command_array):
        s = subprocess.Popen(command_array,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False)
        s.wait()
        return '%s%s' % (s.stdout.read(), s.stderr.read())


class LinuxOsInteraction(OsInteraction):
    def __init__(self, use_logger=True):
        super(LinuxOsInteraction, self).__init__(use_logger)
        self.APP_DATA_PATH = os.path.join(os.path.expanduser('~/.openport'))

    def copy_to_clipboard(self, text):
        from Tkinter import Tk
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text.strip())
        r.destroy()

        r = Tk()
        result = r.selection_get(selection = "CLIPBOARD")
        #logger.debug('tried to copy %s to clipboard, got %s' % (text, result))
        r.destroy()

    def pid_is_running(self, pid):
        """Check whether pid exists in the current process table."""
        if pid < 0:
            return False

        try:
            os.kill(pid, 0)
        except OSError, e:
            return e.errno != errno.ESRCH
        else:
            return True

    def kill_pid(self, pid):
        os.kill(pid, signal.SIGKILL)
        return True

    def is_compiled(self):
        return sys.argv[0] != 'python' and sys.argv[0][-3:] != '.py'

    def get_python_exec(self):
        if os.path.exists('env/bin/python'):
            return ['env/bin/python']
        else:
            return ['python']

    def spawnDaemon(self, func):
        # do the UNIX double-fork magic, see Stevens' "Advanced
        # Programming in the UNIX Environment" for details (ISBN 0201563177)
        try:
            pid = os.fork()
            if pid > 0:
                # parent process, return and keep running
                return
        except OSError, e:
            self.logger.error("fork #1 failed: %d (%s)" % (e.errno, e.strerror) )
            sys.exit(1)

        os.setsid()

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            self.logger.error("fork #2 failed: %d (%s)" % (e.errno, e.strerror) )
            sys.exit(1)

        func()

        # all done
        os._exit(os.EX_OK)


class WindowsOsInteraction(OsInteraction):
    def __init__(self, use_logger=True):
        super(WindowsOsInteraction, self).__init__(use_logger)
        self.APP_DATA_PATH = os.path.join(os.environ['APPDATA'], 'OpenportIt')

    def copy_to_clipboard(self, text):
        #print 'copying to clipboard: %s' % text
        #todo: subprocess hiervoor gebruiken
        command = 'echo ' + text.strip() + '| clip'
        os.system(command)

    def pid_is_running(self, pid):
        """Check whether pid exists in the current process table."""
        return False
        #todo: psutil?
        #            import wmi
        #            c = wmi.WMI()
        #            for process in c.Win32_Process ():
        #                if pid == process.ProcessId:
        #                    return True
        #            return False

    def kill_pid(self, pid):
        a = self.run_command_silent(['taskkill', '/pid', '%s' % pid, '/f', '/t'])
        return a.startswith('SUCCESS')

    def is_compiled(self):
        return sys.argv[0][-3:] == 'exe'

    def get_python_exec(self):
        if os.path.exists('env/Scripts/python.exe'):
            return ['start', 'env/Scripts/python.exe']
        else:
            return ['start', 'python.exe']
    def spawnDaemon(self, func):
        #TODO!
        func()

def is_linux():
    return platform.system() != 'Windows'

def getInstance():
    if is_linux():
        return LinuxOsInteraction()
    else:
        return WindowsOsInteraction()

def getInstance(use_logger=True):
    if is_linux():
        return LinuxOsInteraction(use_logger)
    else:
        return WindowsOsInteraction(use_logger)
