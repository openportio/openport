from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn
import SimpleHTTPServer
import SocketServer
import os
import posixpath
import socket
from sys import argv
import urllib
from OpenSSL import SSL
from loggers import get_logger
from osinteraction import OsInteraction


file_serve_path = None
logger = get_logger(__name__)
osinteraction = OsInteraction()

class FileServeHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def send_head(self):
        return self.send_file(file_serve_path)

    def send_file(self, path):
		f = None
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


class SecureHTTPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer, HTTPServer):
    def __init__(self, server_address, HandlerClass):
        SocketServer.BaseServer.__init__(self, server_address, HandlerClass)
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        #danger of decryption because every user has the same private key... Make sure to use diffie hellman for key exchange.
        ctx.set_options(SSL.OP_SINGLE_DH_USE)
        #server.pem's location (containing the server private key and
        #the server certificate).
        fpem = osinteraction.get_resource_path('server.pem')
        logger.debug('certificate file: %s' % fpem)
        ctx.use_privatekey_file (fpem)
        ctx.use_certificate_file(fpem)
        self.socket = SSL.Connection(ctx, socket.socket(self.address_family,
            self.socket_type))
        self.server_bind()
        self.server_activate()

class ThreadingHTTPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer, HTTPServer):
    pass


class DirServeHandler(FileServeHandler):
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            return self.list_directory(path)
        else:
            return self.send_file(path)

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)
        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = file_serve_path
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path


def serve_file_on_port(path, port):
    HandlerClass = DirServeHandler if os.path.isdir(path) else FileServeHandler
    global file_serve_path
    file_serve_path = path

    ServerClass = SecureHTTPServer
 #   ServerClass = ThreadingHTTPServer
    httpd = ServerClass(('', port), HandlerClass)

    print "serving at port", port
    httpd.serve_forever()

if __name__ == '__main__':
    path = argv[1]
    port = int(argv[2])

    serve_file_on_port(path, port)
