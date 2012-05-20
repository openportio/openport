import os
import platform
import subprocess
import sys
import errno
import wx
from server import start_server_thread
from trayicon import OpenPortItTaskBarIcon
from dbhandler import DBHandler
from shares_frame import SharesFrame

class OpenPortItFrame(wx.Frame):

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title, size = (200, 150),
            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE)

        self.share_processes = {}
        self.dbhandler = DBHandler()

        self.addTrayIcon()
        self.startServer()
        self.shares_frame = SharesFrame(self, -1, "Shares")

#        VIEW_LOG=wx.NewId()
#        CHECK_UPDATES=wx.NewId()
#        ABOUT=wx.NewId()

    def addTrayIcon(self):
        self.tbicon = OpenPortItTaskBarIcon(self)
        self.tbicon.addItem('View shares', self.viewShares)
        self.tbicon.menu.AppendSeparator()
        self.tbicon.addItem('Exit', self.exitApp)
        self.tbicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.viewShares)

    def exitApp(self,event):
        self.tbicon.RemoveIcon()
        self.tbicon.Destroy()
        for pid in self.share_processes:
            self.kill_pid(pid)
        sys.exit()

    def startServer(self):
        start_server_thread(onNewShare=self.onNewShare)

    def restart_sharing(self):
        shares = self.dbhandler.get_shares()
        #todo: set all pid's to 0
        app_dir = os.path.realpath(os.path.dirname(sys.argv[0]))
        for share in shares:
            if self.pid_is_running(share.pid):
                self.onNewShare(share)
                pid = share.pid
            else:
            #todo: .py = .exe when compiled
                if sys.argv[0][-3:] == 'exe':
                    command = [os.path.join(app_dir, 'openportit.exe'),]
                else:
                    command = ['python', os.path.join(app_dir, 'openportit.py')]
                command.extend(['--hide-message', '--no-clipboard', '--tray-port', '8001', share.filePath])
                print command
                p = subprocess.Popen( command,
                    bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None,
                    close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0)

            self.share_processes[p.pid]=p

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

    def stop_sharing(self,share):
        print "stopping %s" % share.id
        self.kill_pid(share.pid)
        self.dbhandler.stop_share(share)
        self.shares_frame.remove_share(share)

    def viewShares(self, event):
        self.shares_frame.Show(True)

    def onNewShare(self, share):
        print "adding share %s" % share.id
        callbacks = {'stop': self.stop_sharing}
        self.shares_frame.add_share(share, callbacks=callbacks)


def main():
    print 'server pid:%s' % os.getpid()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart-shares', action='store_true', help='Restart all active shares.')
#    parser.add_argument('--tray-port', type=int, default=8001, help='Specify the port to run on.')
    args = parser.parse_args()

    app = wx.App(False)
    frame = OpenPortItFrame(None, -1, ' ')

    if args.restart_shares:
        frame.restart_sharing()

    import signal
    def handleSigTERM():
        frame.exitApp(None)
    signal.signal(signal.SIGTERM, handleSigTERM)

    app.MainLoop()

if __name__ == '__main__':
    main()