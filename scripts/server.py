import cgi, urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class ShareRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        print "got post?"
        try:
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers.getheader('content-length'))
                postvars = urlparse.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                postvars = {}
            path = postvars['path'][0]
            print 'path: <%s>' % path
        except Exception, e:
            print e

def main():
    try:
        server = HTTPServer(('', 8001), ShareRequestHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()

if __name__ == '__main__':
    main()