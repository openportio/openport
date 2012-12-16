import errno
import os
import platform
import subprocess
import sys
from loggers import get_logger
from common.share import Share


APP_DATA_PATH = os.path.join(os.environ['APPDATA'], 'OpenportIt')

logger = get_logger('OsInteraction')

class OsInteraction():

    def copy_to_clipboard(self, text):
        #print 'copying to clipboard: %s' % text
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

    def kill_pid(self, pid):
        if platform.system() == 'Windows':
            os.system("taskkill /pid %s /f /t" % pid)
        else:
            os.kill(pid)

    def is_compiled(self):
        return sys.argv[0][-3:] == 'exe'

    def get_app_name(self):
        return os.path.basename(sys.argv[0])

    def start_openport_process(self, share, hide_message=True, no_clipboard=True, tray_port=8001):
        command = []
        if share.restart_command.split()[0][-3:] == '.py':
            command.extend(['python.exe'])
        command.extend( share.restart_command.split(' ') )
        command.extend(['--tray-port', '%s' % tray_port, '--request-port', '%s' % share.server_port,
                        '--request-token', share.server_session_token, '--local-port', '%s' % share.local_port])
        if hide_message:
            command.extend(['--hide-message'])
        if no_clipboard:
            command.extend(['--no-clipboard'])
        if isinstance(share, Share):
            command.extend([share.filePath])

        logger.debug( command )
        p = subprocess.Popen( command,
            bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None,
            close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0)
        return p

    def get_resource_path(self, path):
        dir = os.path.dirname( os.path.dirname( os.path.realpath( __file__ ) ) )
#        if dir[-3:] == 'zip':
#            dir = os.path.dirname(dir)
        return os.path.join(dir, path)

    def get_app_data_path(self, filename=''):
        try:
            os.makedirs(APP_DATA_PATH)
        except WindowsError:
            pass
        return os.path.join(APP_DATA_PATH, filename)
