import errno
import os
import platform
import subprocess
import getpass
import sys
from threading import Thread
from time import sleep
import signal
import psutil

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

ON_POSIX = 'posix' in sys.builtin_module_names


class OsInteraction(object):

    def __init__(self, use_logger=True):
        if use_logger:
            from services.logger_service import get_logger
            self.logger = get_logger('OsInteraction')
        self.output_queues = {}

    def get_app_name(self):
        return os.path.basename(sys.argv[0])

    @staticmethod
    def unset_variable(args, variable):
        result = []
        result.extend(args)
        if variable not in args:
            return result
        location = result.index(variable)
        result.pop(location)
        if len(result) > location and len(result[location]) > 0 and result[location][0] != '-':
            result.pop(location)
        return result

    @staticmethod
    def set_variable(args, variable, value=None):
        result = OsInteraction.unset_variable(args, variable)
        result.append(variable)
        if value is not None:
            result.append(str(value))
        return result

    @staticmethod
    def get_variable(command, variable):
        try:
            location = command.index(variable)
        except ValueError:
            return None
        if location < len(command) - 1:
            return command[location + 1]
        else:
            return None


    def start_openport_process(self, share, manager_port=8001):

        if not 'openport' in share.restart_command[0]:
            command = self.get_openport_exec()
        else:
            command = []

#        print share.restart_command
        command.extend(share.restart_command)

        assert isinstance(command, list)
        command = OsInteraction.set_variable(command, "--manager-port", manager_port)
        share.restart_command = command

        return self.start_process(command)

    def start_process(self, args):
        if self.logger:
            self.logger.debug('Running command: %s' % args)
        p = subprocess.Popen(args,
                             bufsize=0, executable=None, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=None, close_fds=is_linux(), shell=False, cwd=None, env=None,
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

    def run_shell_command(self, command):
        if isinstance(command, list):
            command = ' '.join(['"%s"' % arg for arg in command])
        s = subprocess.Popen(command,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=True,
                             close_fds=is_linux())
        return s.communicate()

    def run_command_and_print_output_continuously(self, command_array):
        creation_flags = self.get_detached_process_creation_flag()
        s = subprocess.Popen(command_array,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=creation_flags, shell=False,
                             close_fds=is_linux())

        return self.print_output_continuously(s)

    def print_output_continuously(self, s):
        def append_output(initial, extra):
            if not initial:
                return extra if extra and len(extra) > 0 else False
            elif not extra or len(extra) == 0:
                return initial
            else:
                newline = '' if initial.endswith(os.linesep) else os.linesep
                return initial + newline + extra

        all_output = [False, False]
        while True:
            output = self.get_all_output(s)
            if output[0]:
                self.logger.debug('silent command stdout: <<<<%s>>>>' % output[0])
            if output[1]:
                self.logger.debug('silent command stderr: <<<<%s>>>>' % output[1])

            all_output[0] = append_output(all_output[0], output[0])
            all_output[1] = append_output(all_output[1], output[1])
            if s.poll() is not None:
                break
            sleep(1)
        output = s.communicate()
        if output[0]:
            self.logger.debug('silent command stdout: %s' % output[0])
        if output[1]:
            self.logger.debug('silent command stderr: %s' % output[1])
        all_output[0] = append_output(all_output[0], output[0])
        all_output[1] = append_output(all_output[1], output[1])
        self.logger.debug('application stopped: <<%s>>' % all_output)
        return all_output

    def print_output_continuously_threaded(self, s):
        t_stdout = Thread(target=self.print_output_continuously, args=(s,))
        t_stdout.daemon = True
        t_stdout.start()

    def get_all_output(self, p):
        return self.non_block_read(p)

    def non_block_read(self, process):

        if process.pid in self.output_queues:
            q_stdout = self.output_queues[process.pid][0]
            q_stderr = self.output_queues[process.pid][1]
        else:

            def enqueue_output(out, queue):
                for line in iter(out.readline, b''):
                    queue.put(line)
#                out.close()

            q_stdout = Queue()
            t_stdout = Thread(target=enqueue_output, args=(process.stdout, q_stdout))
            t_stdout.daemon = True # thread dies with the program
            t_stdout.start()

            q_stderr = Queue()
            t_stderr = Thread(target=enqueue_output, args=(process.stderr, q_stderr))
            t_stderr.daemon = True # thread dies with the program
            t_stderr.start()
            sleep(0.1)
            self.output_queues[process.pid] = (q_stdout, q_stderr)

        def read_queue(q):
            # read line without blocking
            empty = True
            output = ''
            try:
                while True:
                    output += '%s' % q.get_nowait()
                    if not output.endswith(os.linesep):
                        output += os.linesep
                    empty = False
            except Empty:
                if empty:
                    return False
                else:
                    return output.rstrip('\n\r')
                #return False if empty else output

        return read_queue(q_stdout), read_queue(q_stderr)

    def get_open_port(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port

    def quote_path(self, path):
        split = path.split(os.sep)
        #logger.debug( split )
        quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
        return os.sep.join(quoted)

    def get_openport_exec(self):
        if self.is_compiled():
            command = []
            path = self.quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openport.exe'))
            if not os.path.exists(path):
                path = self.quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openport'))
            command.extend([path])
        else:
            command = self.get_python_exec()
            command.extend(['apps/openport_app.py'])
        return command

class LinuxOsInteraction(OsInteraction):

    def __init__(self, use_logger=True):
        super(LinuxOsInteraction, self).__init__(use_logger)
        import os
        import fcntl
        self.APP_DATA_PATH = '/root/.openport' if os.getuid() == 0 else os.path.join(os.path.expanduser('~/.openport'))

    def get_detached_process_creation_flag(self):
        return 0

    def nonBlockRead(self, output):
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return output.read()
        except:
            return False

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

    def kill_pid(self, pid, kill_signal=None):
        if kill_signal is None:
            kill_signal = signal.SIGKILL
        os.kill(pid, kill_signal)
        return True

    def is_compiled(self):
        return sys.argv[0] != 'python' and sys.argv[0][-3:] != '.py'

    def get_python_exec(self):
        if os.path.exists('env/bin/python'):
            return ['env/bin/python']
        else:
            return ['python']

    def spawn_daemon(self, command):
        # do the UNIX double-fork magic, see Stevens' "Advanced
        # Programming in the UNIX Environment" for details (ISBN 0201563177)
        try:
            pid = os.fork()
            if pid > 0:
                # parent process, return and keep running
                return
        except OSError, e:
            self.logger.error("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
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

        # It may seem that this launches 2 applications when using pyinstaller. Don't worry, the first one is the
        # bootloader, the second one the actual application.
        # http://www.pyinstaller.org/export/d3398dd79b68901ae1edd761f3fe0f4ff19cfb1a/project/doc/Manual.html?format=raw#how-one-file-mode-works
        self.run_command_and_print_output_continuously(command)

        # all done
        os._exit(os.EX_OK)

    def user_is_root(self):
        return os.geteuid() == 0


class WindowsOsInteraction(OsInteraction):
    def __init__(self, use_logger=True):
        super(WindowsOsInteraction, self).__init__(use_logger)
        self.APP_DATA_PATH = os.path.join(os.environ['APPDATA'], 'Openport')

    def get_detached_process_creation_flag(self):
        return 8

    def copy_to_clipboard(self, text):
        #print 'copying to clipboard: %s' % text
        #todo: subprocess hiervoor gebruiken
        command = 'echo ' + text.strip() + '| clip'
        os.system(command)

    def pid_is_running(self, pid):
        """Check whether pid exists in the current process table."""
        return psutil.pid_exists(pid)

    def kill_pid(self, pid, signal='Ignore'):
        a = self.run_shell_command(['taskkill', '/pid', '%s' % pid, '/f', '/t'])
        self.logger.debug('kill command output: %s %s' % a)
        return a[0].startswith('SUCCESS')

    def is_compiled(self):
        return sys.argv[0][-3:] == 'exe'

    def get_python_exec(self):
        #self.logger.debug('getting python exec. Cwd: %s' % os.getcwd())
        if os.path.exists('env/Scripts/python.exe'):
            return ['env\\Scripts\\python.exe']
        else:
            return ['python.exe']

    def spawn_daemon(self, command):
        def foo():
            try:
                output = self.run_command_and_print_output_continuously(command)
                self.logger.debug('daemon stopped: %s ' % output)
            except Exception, e:
                self.logger.error(e)

        t = Thread(target=foo)
        t.setDaemon(True)
        t.start()

    def user_is_root(self):
        return False


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
