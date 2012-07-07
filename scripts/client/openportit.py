from optparse import OptionParser
import pprint
import subprocess
import sys

if __name__ == '__main__':
	import wx
	app = wx.App(redirect=False)

import os
from sys import argv

working_dir = os.getcwd()
os.chdir(os.path.realpath(os.path.dirname(argv[0])))
from servefile import serve_file_on_port
from openport_win import open_port

def get_open_port():
	import socket
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(("",0))
	s.listen(1)
	port = s.getsockname()[1]
	s.close()
	return port

def open_port_file(path, callback=None):
	import threading
	serving_port = get_open_port()
	thr = threading.Thread(target=serve_file_on_port, args=(path, serving_port))
	thr.setDaemon(True)
	thr.start()
	
	thr2 = threading.Thread(target=open_port, args=(serving_port,callback))
	thr2.setDaemon(True)
	thr2.start()

def start_tray_application():
    #todo: linux/mac
    if sys.argv[0][-3:] == '.py':
        command = ['start', 'python', 'application.py']
    else:
        command = ['start', quote_path(os.path.join(os.path.dirname(sys.argv[0]), 'application.exe'))]
    print command
    subprocess.call(' '.join(command), shell=True)

def quote_path(path):
    split = path.split(os.sep)
    print split
    quoted = ['"%s"' % dir if ' ' in dir else dir for dir in split]
    return os.sep.join(quoted)


if __name__ == '__main__':

#    print quote_path('c:\\hallo\\jan\\hoe ist\\goed.txt')
#    sys.exit(0)

    print 'client pid:%s' % os.getpid()
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hide-message', action='store_true', help='Do not show the message.')
    parser.add_argument('--no-clipboard', action='store_true', help='Do not copy the link to the clipboard.')
    parser.add_argument('--tray-port', type=int, default=8001, help='Inform the tray app of the new share.')
    parser.add_argument('filename', help='The file you want to openport.')
    args = parser.parse_args()

    def copy_share_to_clipboard(share):
        from Tkinter import Tk
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        file_address = share.get_link()

        r.clipboard_append(file_address.strip())
        r.destroy()

    def show_message_box(share):
        wx.MessageBox('You can now download your file(s) from %s\nThis link has been copied to your clipboard.' %(share.get_link()), 'Info', wx.OK | wx.ICON_INFORMATION)

    def inform_tray_app(share, tray_port, start_tray=True):
        import urllib, urllib2
        url = 'http://127.0.0.1:%s' % tray_port

        try:
            data = urllib.urlencode(share.as_dict())
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req).read()
            if response.strip() != 'ok':
                print response
        except Exception, detail:
            print "An error has occured while informing the tray: ", detail
            if start_tray:
                start_tray_application()
                sleep(3)
                inform_tray_app(server_ip, server_port, tray_port, account_id, key_id, start_tray=False)


    def callback(portForwardResponse):
        share = Share()
        share.filePath = os.path.join(working_dir, args.filename)
        share.server = portForwardResponse.server
        share.server_port = portForwardResponse.remote_port
        share.pid = os.getpid()

        if args.tray_port > 0:
            inform_tray_app(share, args.tray_port)
        if not args.no_clipboard:
            copy_share_to_clipboard(share)
        if not args.hide_message:
            show_message_box(share)

    app.MainLoop()
    open_port_file(os.path.join(working_dir, args.filename), callback)
    from time import sleep
    while True:
       sleep(1000)


class Share():
    def __init__(self, id=-1, filePath='', server_ip='', server_port='', pid=-1, active=0, account_id=-1, key_id=-1):
        self.id = id
        self.filePath = filePath
        self.server = server_ip
        self.server_port = server_port
        self.pid = pid
        self.active = active
        self.account_id = account_id
        self.key_id = key_id

    def get_link(self):
        return 'https://%s:%s'%(self.server, self.server_port)

    def as_dict(self):
        return {
            'id': self.id,
            'filePath' : self.filePath,
            'server': self.server,
            'server_port': self.server_port,
            'pid': self.pid,
            'active': self.active,
            'account_id': self.account_id,
            'key_id': self.key_id,
        }

    def from_dict(self, dict):
        self.id = dict['id']
        self.filePath = dict['filePath']
        self.server = dict['server']
        self.server_port = dict['server_port']
        self.pid = dict['pid']
        self.active = dict['active']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']

