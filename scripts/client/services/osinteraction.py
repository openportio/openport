import errno
import os
import platform
import subprocess
import sys
#from services.logger_service import get_logger  #creates a circular reference
from common.share import Share


try:
    APP_DATA_PATH = os.path.join(os.environ['APPDATA'], 'OpenportIt')
except:
    APP_DATA_PATH = "~/.OpenPort"

#logger = get_logger('OsInteraction')

class OsInteraction():

    def copy_to_clipboard(self, text):
        #print 'copying to clipboard: %s' % text
        #todo: subprocess hiervoor gebruiken
        command = 'echo ' + text.strip() + '| clip'
        os.system(command)

#        from Tkinter import Tk
#        r = Tk()
#        r.withdraw()
#        r.clipboard_clear()
#        r.clipboard_append(text.strip())
#        r.destroy()

#        from Tkinter import Tk
#        r = Tk()
#        result = r.selection_get(selection = "CLIPBOARD")
#        logger.debug('tried to copy %s to clipboard, got %s' % (share.get_link(), result))
#        r.destroy()

    def pid_is_running(self, pid):
        """Check whether pid exists in the current process table."""

        if pid < 0:
            return False

        if platform.system() == 'Windows':
            return False
            #todo: psutil?
        #            import wmi
        #            c = wmi.WMI()
        #            for process in c.Win32_Process ():
        #                if pid == process.ProcessId:
        #                    return True
        #            return False
        else:
            try:
                os.kill(pid, 0)
            except OSError, e:
                return e.errno != errno.ESRCH
            else:
                return True
                
    def is_linux(self):
        return platform.system() != 'Windows'

    def kill_pid(self, pid):
        if platform.system() == 'Windows':
            a =  self.run_command_silent(['taskkill', '/pid', '%s' % pid, '/f', '/t'])
            return a.startswith('SUCCESS')
        else:
            os.kill(pid)
            return true

    def is_compiled(self):
        return not self.is_linux() and sys.argv[0][-3:] == 'exe'

    def get_app_name(self):
        return os.path.basename(sys.argv[0])

    def start_openport_process(self, share, hide_message=True, no_clipboard=True, tray_port=8001):
#        print share.restart_command
        p = subprocess.Popen( share.restart_command,
            bufsize=0, executable=None, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=None,
            close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0)
        return p

    def get_resource_path(self, path):
        dir = os.path.dirname( os.path.dirname( os.path.realpath( __file__ ) ) )
        if dir[-3:] == 'zip':
            dir = os.path.dirname(dir)
        else:
            dir = os.path.join(dir, 'resources')
        return os.path.join(dir, path)

    def get_app_data_path(self, filename=''):
        try:
            os.makedirs(APP_DATA_PATH)
        except Exception:
            pass
        return os.path.join(APP_DATA_PATH, filename)

    def run_command_silent(self, command_array):
        s = subprocess.Popen(command_array,
            bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False)
        s.wait()
        return '%s%s' % (s.stdout.read(), s.stderr.read())

    def get_application_dir(self):
        if self.is_compiled():
            return os.path.abspath(os.path.dirname(os.path.dirname(__file__))) #todo: verify
        else:
            return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

