import errno
import os
import platform
import subprocess
import sys

class OsInteraction():

    def copy_to_clipboard(self, text):
        from Tkinter import Tk
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text.strip())
        r.destroy()

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

    def kill_pid(self, pid):
        if platform.system() == 'Windows':
            os.system("taskkill /pid %s /f /t" % pid)
        else:
            os.kill(pid)

    def start_openport_process(self, filePath):
        app_dir = os.path.realpath(os.path.dirname(sys.argv[0]))
        if sys.argv[0][-3:] == 'exe':
            command = [os.path.join(app_dir, 'openportit.exe'),]
        else:
            command = ['python', os.path.join(app_dir, 'openportit.py')]
        command.extend(['--hide-message', '--no-clipboard', '--tray-port', '8001', filePath])
        print command
        p = subprocess.Popen( command,
            bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None,
            close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0)
        return p

    def get_resource_path(self, path):
        dir = os.path.dirname( os.path.realpath( __file__ ) )
        if dir[-3:] == 'zip':
            dir = os.path.dirname(dir)
        return os.path.join(dir, path)
