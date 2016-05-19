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
from lockfile import NotMyLock, LockTimeout
from lockfile import LockFile

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

ON_POSIX = 'posix' in sys.builtin_module_names


class OsInteraction(object):

    def __init__(self, use_logger=True):
        if use_logger:
            from openport.services.logger_service import get_logger
            self.logger = get_logger('OsInteraction')
        self.output_queues = {}
        self.all_output = {}

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
    def strip_sudo_command(command):
        if command[0] != 'sudo':
            return command
        result = command[1:]
        while result[0][0] == '-':
            result = OsInteraction.unset_variable(result, result[0])
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

    def start_openport_process(self, share):
        command = self.get_full_restart_command(share)
        if command is None:
            return

        return self.start_process(command)

    def get_full_restart_command(self, share):
        if not share.restart_command:
            self.logger.debug('no restart command for share with local port %s' % share.local_port)
            return
        # Legacy...
        restart_command = self.strip_sudo_command(share.restart_command)
        if 'openport' in restart_command[0]:
            restart_command = restart_command[1:]
        command = self.get_openport_exec()
        #        print share.restart_command
        command.extend(restart_command)
        return command

    def start_process(self, args, cwd=None):
        if isinstance(args, basestring):
            args = args.split()
        if self.logger:
            self.logger.debug('Running command: %s' % args)
            self.logger.debug('cwd: %s' % os.path.abspath(os.curdir))
            self.logger.debug('base_path: %s' % self.get_base_path())
        p = subprocess.Popen(args,
                             bufsize=0, executable=None, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=None, close_fds=not is_windows(), shell=False,
                             cwd=cwd if cwd else self.get_base_path(),
                             env=None,
                             universal_newlines=False, startupinfo=None, creationflags=0)
        return p

    def get_resource_path(self, path):
        dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        if dir[-3:] == 'zip':
            dir = os.path.dirname(dir)
        else:
            dir = os.path.join(dir)

        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            dir = sys._MEIPASS

        return os.path.join(dir, path)

    def get_app_data_path(self, filename=''):
        #Do not use the logger!
        try:
            os.makedirs(self.APP_DATA_PATH)
        except Exception:
            pass
        return os.path.join(self.APP_DATA_PATH, filename)

    def run_shell_command(self, command, cwd=None):
        if isinstance(command, list):
            command = ' '.join(['"%s"' % arg for arg in command])
        s = subprocess.Popen(command,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=True,
                             close_fds=not is_windows(), cwd=cwd)
        return s.communicate()

    def run_command_and_print_output_continuously(self, command_array, prefix='', cwd=None, shell=False):
        creation_flags = self.get_detached_process_creation_flag()
        s = subprocess.Popen(command_array,
                             bufsize=2048, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=creation_flags, shell=shell,
                             close_fds=not is_windows(), cwd=cwd)

        return self.print_output_continuously(s, prefix=prefix), s

    def print_output_continuously(self, s, prefix=''):
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
            output = self.get_output(s)
            if output[0]:
                self.logger.debug('silent command stdout: %s<<<<%s>>>>' % (prefix, output[0]))
            if output[1]:
                self.logger.debug('silent command stderr: %s<<<<%s>>>>' % (prefix, output[1]))

            all_output[0] = append_output(all_output[0], output[0])
            all_output[1] = append_output(all_output[1], output[1])
            if s.poll() is not None:
                break
            sleep(1)
        output = s.communicate()
        if output[0]:
            self.logger.debug('silent command stdout: %s<<<%s>>>' % (prefix, output[0]))
        if output[1]:
            self.logger.debug('silent command stderr: %s<<<%s>>>' % (prefix, output[1]))
        all_output[0] = append_output(all_output[0], output[0])
        all_output[1] = append_output(all_output[1], output[1])
        self.logger.debug('application stopped: stdout %s<<%s>>' % (prefix, all_output[0]))
        self.logger.debug('application stopped: stderr %s<<%s>>' % (prefix, all_output[1]))
        return all_output

    def print_output_continuously_threaded(self, s, prefix=''):
        t_stdout = Thread(target=self.print_output_continuously, args=(s, prefix))
        t_stdout.daemon = True
        t_stdout.start()

    def get_output(self, p):
        return self.non_block_read(p)

    def get_all_output(self, p):
        self.get_output(p)

        if p.pid not in self.all_output:
            return None

        output = [out.strip() for out in self.all_output.get(p.pid)]
        return tuple([out if out else False for out in output])

    def non_block_read(self, process):

        if process.pid in self.output_queues:
            q_stdout = self.output_queues[process.pid][0]
            q_stderr = self.output_queues[process.pid][1]
        else:

            def enqueue_output(out, queue):
                if out:
                    for line in iter(out.readline, b''):
                        queue.put(line)
#                out.close()

            q_stdout = Queue()
            t_stdout = Thread(target=enqueue_output, args=(process.stdout, q_stdout))
            t_stdout.daemon = True  # thread dies with the program
            t_stdout.start()

            q_stderr = Queue()
            t_stderr = Thread(target=enqueue_output, args=(process.stderr, q_stderr))
            t_stderr.daemon = True  # thread dies with the program
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

        new_output = (read_queue(q_stdout), read_queue(q_stderr))

        if process.pid not in self.all_output:
            self.all_output[process.pid] = ['', '']
        for i, new_out in enumerate(new_output):
            if not new_out:
                new_out = ''
            self.all_output[process.pid][i] = os.linesep.join([self.all_output[process.pid][i], new_out])

        return new_output

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
            path = self.quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openportw.exe'))
            if not os.path.exists(path):
                path = self.quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openport.exe'))
            if not os.path.exists(path):
                path = self.quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'openport'))
            if not os.path.exists(path):
                path = self.quote_path('/usr/bin/openport')
            if not os.path.exists(path):
                path = self.quote_path('/opt/local/bin/openport')
            command.extend([path])
        else:
            command = self.get_python_exec()
            command.extend(['apps/openport_app.py'])
        return command

    def pid_is_openport_process(self, pid):
        process = filter(lambda p: p.pid == pid, psutil.process_iter())
        for i in process:
            return 'openport' in i.name() or 'python' in i.name()  # Is not 100% but best effort. (for mac)
        return False

    def get_base_path(self):
        if self.is_compiled():
            return os.path.dirname(sys.argv[0])
        else:
            self.logger.debug('sys.argv %s' % sys.argv[0])
 #           base_path = os.path.dirname(os.path.dirname(sys.argv[0]))
            base_path = os.path.dirname(os.path.dirname(__file__))
            if base_path == '':
                base_path = '.'
            return base_path

    def run_function_with_lock(self, function, lock_file, timeout=30, args=[], kwargs={}):
        self.logger.debug('starting function with lock: %s' % lock_file)
        lock = LockFile(lock_file)
        try:
            while not lock.i_am_locking():
                try:
                    lock.acquire(timeout=timeout)
                except (LockTimeout, NotMyLock) as e:
                    self.logger.debug('breaking lock')
                    lock.break_lock()
                    lock.acquire()
                    self.logger.exception(e)

            self.logger.debug('lock acquired: starting function')
            return function(*args, **kwargs)
        finally:
            self.logger.debug('function done, releasing lock')

            if lock.is_locked():
                try:
                    lock.release()
                except NotMyLock:
                    try:
                        os.remove(lock_file)
                    except Exception as e:
                        self.logger.exception(e)
            self.logger.debug('lock released')

    def activate_app(self):
        pass

    @staticmethod
    def resource_path(*relative_paths):
        """ Get absolute path to resource, works for dev and for PyInstaller """

        if hasattr(sys, '_MEIPASS'):
            # PyInstaller >= 1.6
            filename = os.path.join(sys._MEIPASS, *relative_paths)
        elif '_MEIPASS2' in os.environ:
            # PyInstaller < 1.6 (tested on 1.5 only)
            filename = os.path.join(os.environ['_MEIPASS2'], *relative_paths)
        else:
            # 2 dots because we start the applications from the apps folder.
            filename = os.path.join(os.path.dirname(__file__), '..', *relative_paths)

        return os.path.abspath(filename)

    def copy_to_clipboard(self, text):
        import pyperclip
        pyperclip.copy(text)

    def user_is_root(self):
        return hasattr(os, 'getuid') and os.getuid() == 0


class LinuxOsInteraction(OsInteraction):

    def __init__(self, use_logger=True):
        super(LinuxOsInteraction, self).__init__(use_logger)
        home_dir = os.path.expanduser("~{}/".format(os.environ.get("USER")))
        if len(home_dir) < 3:
            home_dir = '/root/'
        self.APP_DATA_PATH = os.path.join(home_dir, '.openport')

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
        return sys.argv[0] != 'python' and sys.argv[0][-3:] != '.py' and not 'nosetests' in sys.argv[0]

    def get_python_exec(self):
        virtual_env_python = os.path.join(self.get_base_path(), 'env/bin/python')
        if os.path.exists(virtual_env_python):
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

    def get_username(self):
        import pwd
        return pwd.getpwuid(os.getuid())[0]


class WindowsOsInteraction(OsInteraction):
    def __init__(self, use_logger=True):
        super(WindowsOsInteraction, self).__init__(use_logger)
        self.APP_DATA_PATH = os.path.join(os.environ['APPDATA'], 'Openport')

    def get_detached_process_creation_flag(self):
        return 8

    def pid_is_running(self, pid):
        """Check whether pid exists in the current process table."""
        return psutil.pid_exists(pid)

    def kill_pid(self, pid, signal=-1):
        # First try killing it nicely, sending Ctrl-Break. This only works if both processes are part of the same console.
        # http://msdn.microsoft.com/en-us/library/windows/desktop/ms682541(v=vs.85).aspx
        import ctypes
        if ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, pid):  # 0 => Ctrl-C, 1 -> Ctrl-Break
            #return True
            pass

        # If that didn't work, kill it with fire.
        sleep(1)
        return os.kill(pid, 9)
        #
        # a = self.run_shell_command(['taskkill', '/pid', '%s' % pid, '/f', '/t'])
        #self.logger.debug('kill command output: %s %s' % a)
        #return a[0].startswith('SUCCESS')

    def handle_signals(self, handler):

        return  # Do not use this, windows will say your program has crashed.

        from ctypes import WINFUNCTYPE, windll
        from ctypes.wintypes import BOOL, DWORD

        kernel32 = windll.LoadLibrary('kernel32')
        PHANDLER_ROUTINE = WINFUNCTYPE(BOOL, DWORD)
        SetConsoleCtrlHandler = kernel32.SetConsoleCtrlHandler
        SetConsoleCtrlHandler.argtypes = (PHANDLER_ROUTINE, BOOL)
        SetConsoleCtrlHandler.restype = BOOL

        @PHANDLER_ROUTINE
        def console_handler(ctrl_type):
            handler(ctrl_type)

        if not SetConsoleCtrlHandler(console_handler, True):
            raise RuntimeError('SetConsoleCtrlHandler failed.')

    def is_compiled(self):
        return sys.argv[0][-3:] == 'exe'

    def get_python_exec(self):
        #self.logger.debug('getting python exec. Cwd: %s' % os.getcwd())
        base_dir = self.get_base_path()
        if os.path.exists(os.path.join(base_dir, 'env/Scripts/python.exe')):
            return [os.path.join(base_dir, 'env\\Scripts\\python.exe')]
        else:
            return ['python.exe']

    def spawn_daemon(self, command):

        args = command
        if self.logger:
            self.logger.debug('Running command: %s' % args)
            self.logger.debug('cwd: %s' % os.path.abspath(os.curdir))
            self.logger.debug('base_path: %s' % self.get_base_path())
        self.logger.debug('start process')
        p = subprocess.Popen(args,
                             bufsize=0, executable=None, stdin=None, stdout=None, stderr=None,
                             preexec_fn=None, close_fds=True, shell=False,
                             cwd=self.get_base_path(),
                             env=None,
                             universal_newlines=False, startupinfo=None,
                             #creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                             creationflags=8,  # from win32process import DETACHED_PROCESS
                             )
        self.logger.debug('process started')

        return p


    def user_is_root(self):
        return False

    def get_username(self):
        return getpass.getuser()

    def start_openport_process(self, share):
        command = self.get_full_restart_command(share)
        if command is None:
            return

        return self.spawn_daemon(command)


class MacOsInteraction(LinuxOsInteraction):
    def __init__(self, use_logger=True):
        super(MacOsInteraction, self).__init__(use_logger)

    def activate_app(self):
        subprocess.Popen(['osascript', '-e', '''\
    tell application "System Events"
      set procName to name of first process whose unix id is %s
    end tell
    tell application procName to activate
''' % os.getpid()])

    def spawn_daemon(self, command):
        try:
            pid = os.fork()
            if pid > 0:
                # parent process, return and keep running
                return pid
        except OSError, e:
            self.logger.error("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        os.setsid()

        # don't do a second fork, OS X doesn't allow it.
        self.run_command_and_print_output_continuously(command)

        # all done
        os._exit(os.EX_OK)


def is_windows():
    return platform.system() == 'Windows'


def is_mac():
    return sys.platform == 'darwin'


def getInstance(use_logger=True):
    if is_mac():
        return MacOsInteraction(use_logger)
    if is_windows():
        return WindowsOsInteraction(use_logger)
    else:
        return LinuxOsInteraction(use_logger)
