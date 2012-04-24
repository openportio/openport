if __name__ == '__main__':
	import wx
	app = wx.App(redirect=False)

import os
from sys import argv
working_dir = os.getcwd()
os.chdir(os.path.dirname(argv[0]))
from servefile import serve_file_on_port
from openthegate_win import open_port


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

if __name__ == '__main__':
	
	def showMessage(server_ip, server_port):
	
		from Tkinter import Tk
		r = Tk()
		r.withdraw()
		r.clipboard_clear()
		file_address = '%s:%s'%(server_ip, server_port)
		
		print file_address
		r.clipboard_append(file_address.strip())
		r.destroy()
		wx.MessageBox('You can now download your file from %s:%s' %(server_ip, server_port), 'Info', wx.OK | wx.ICON_INFORMATION)
	app.MainLoop()

	open_port_file(os.path.join(working_dir, argv[1]), showMessage)
	from time import sleep
	while True:
		sleep(1000)

	