from BaseHTTPServer import HTTPServer
from StringIO import StringIO
import cgi
from urlparse import urlparse, parse_qs
import SimpleHTTPServer
import SocketServer
import os
import posixpath
import socket
import urllib
from OpenSSL import SSL
from services.logger_service import get_logger
from services.osinteraction import OsInteraction
from ext_http_server import RangeHandler


_file_serve_path = None
_token = None
logger = get_logger(__name__)
osinteraction = OsInteraction()

class FileServeHandler(RangeHandler):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def send_head(self):
        if not self.check_token(): return None
        return self.send_file(_file_serve_path)

    def send_file(self, path):
		f = None
		logger.debug( 'path = %s' % path )
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

    def check_token(self):
        dict = parse_qs(urlparse(self.path).query)
        #print dict, self.path
        if not 't' in dict or len(dict['t']) < 1 or dict['t'][0].strip('/') != _token:
            self.send_error(401, "invalid token")
            return False
        return True

class ThreadingHTTPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer, HTTPServer):
    pass

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

class DirServeHandler(FileServeHandler):
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        if not self.check_token(): return None
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

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s?t=%s">%s</a>\n'
            % (urllib.quote(linkname), _token, cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f


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
        path = _file_serve_path
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path


def serve_file_on_port(path, port, token):
    HandlerClass = DirServeHandler if os.path.isdir(path) else FileServeHandler
    global _file_serve_path
    _file_serve_path = path

    global _token
    _token = token

 #   ServerClass = SecureHTTPServer
    ServerClass = ThreadingHTTPServer
    httpd = ServerClass(('', port), HandlerClass)

    logger.info( "serving at port %s" % port )
    httpd.serve_forever()

if __name__ == '__main__':
    path = os.path.dirname(os.path.abspath(__file__))
    port = 2001

    serve_file_on_port(path, port, 'token')
