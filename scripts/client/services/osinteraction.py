import errno
import os
import platform
import subprocess
import getpass
import sys
from threading import Thread
from time import sleep


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
    def strip_sudo_command(command):
        if command[0] != 'sudo':
            return command
        result = command[1:]
        while result[0][0] == '-':
            result = OsInteraction.unset_variable(result, result[0])
        return result

    @staticmethod
    def get_sudo_user_from_command(command):
        if command[0] != 'sudo':
            return command

        return OsInteraction.get_variable(command, '-u')

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
#        print share.restart_command
        command = share.restart_command

        assert isinstance(command, list)
        command = OsInteraction.set_variable(command, "--manager-port", manager_port)
        if OsInteraction.get_sudo_user_from_command(command) == getpass.getuser():
            command = OsInteraction.strip_sudo_command(command)

        return self.start_process(command)

    def start_process(self, args):
        if self.logger:
            self.logger.debug('Running command: %s' % args)
        p = subprocess.Popen(args,
                             bufsize=0, executable=None, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=None, close_fds=False, shell=True, cwd=None, env=None,
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

        def append_output(initial, extra):
            if not initial:
                return extra if extra and len(extra) > 0 else False
            elif not extra or len(extra) == 0:
                return initial
            else:
                return initial + os.linesep + extra

        all_output = [False, False]
        while True:
            output = self.get_all_output(s)
            self.logger.debug('silent command stdout: %s' % output[0])
            self.logger.debug('silent command stderr: %s' % output[1])

            all_output[0] = append_output(all_output[0], output[0])
            all_output[1] = append_output(all_output[1], output[1])
            if s.poll() is not None:
                break
            sleep(1)
        output = s.communicate()
        self.logger.debug('silent command stdout: %s' % output[0])
        self.logger.debug('silent command stderr: %s' % output[1])
        all_output[0] = append_output(all_output[0], output[0])
        all_output[1] = append_output(all_output[1], output[1])
        return all_output

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
                    output += '%s\n' % q.get_nowait()
                    empty = False
            except Empty:
                if empty:
                    return False
                else:
                    return output.rstrip('\n\r')
                #return False if empty else output

        return read_queue(q_stdout), read_queue(q_stderr)

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

    def kill_pid(self, pid, signal=None):
        if signal is None:
            signal = signal.SIGKILL
        os.kill(pid, signal)
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

        self.run_command_and_print_output_continuously(command)

        # all done
        os._exit(os.EX_OK)


class WindowsOsInteraction(OsInteraction):
    def __init__(self, use_logger=True):
        super(WindowsOsInteraction, self).__init__(use_logger)
        self.APP_DATA_PATH = os.path.join(os.environ['APPDATA'], 'OpenportIt')

    def get_detached_process_creation_flag(self):
        return 8

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

    def kill_pid(self, pid, signal='Ignore'):
        a = self.run_shell_command(['taskkill', '/pid', '%s' % pid, '/f', '/t'])
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
