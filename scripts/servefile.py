import SimpleHTTPServer
import SocketServer
import os
from sys import argv

file_serve_path = None

class MyTCPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
	def send_head(self):
		f = None
		path = file_serve_path
		print 'path = ', path
		ctype = self.guess_type(path)
		try:
			# Always read in binary mode. Opening files in text mode may cause
			# newline translations, making the actual size of the content
			# transmitted *less* than the content-length!
			f = open(path, 'rb')
		except IOError:
			self.send_error(404, "File not found")
			return None
		self.send_response(200)
		self.send_header("Content-type", ctype)
		fs = os.fstat(f.fileno())
		self.send_header("Content-Length", str(fs[6]))
		self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
		self.send_header("Content-Disposition", "attachment; filename=%s" % os.path.basename(path))
		self.end_headers()
		return f

		
def serve_file_on_port(path, port):
			
	Handler = MyTCPHandler
	
	global file_serve_path
	file_serve_path = path

	httpd = SocketServer.TCPServer(("", port), Handler)

	print "serving at port", port
	httpd.serve_forever()

if __name__ == '__main__':
	path = argv[1]
	port = int(argv[2])
	
	serve_file_on_port(path, port)
	
	