import cgi, urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import threading
import traceback
import wx
from dbhandler import DBHandler
from globals import Globals
from openportit import Share

onNewShare = None

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

            dict = {}
            for key in postvars:
                dict[key] = postvars[key][0]

            share = Share()
            share.from_dict(dict)

            globals = Globals()
            globals.account_id = share.account_id
            globals.key_id = share.key_id
            print 'path: <%s>' % path

            share=save_request(share)
            if onNewShare:
                wx.CallAfter(onNewShare, share)
            self.write_response('ok')
        except Exception, e:
            traceback.print_stack()
            print e

    def write_response(self, text):
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", str(len(text)))
            self.end_headers()
            self.wfile.write(text)
            self.wfile.close()
        except Exception, e:
            traceback.print_stack()
            print e

def start_server(onNewShareFunc=None):
    try:
        server = HTTPServer(('', 8001), ShareRequestHandler)
        global onNewShare
        onNewShare=onNewShareFunc
        print 'Starting server'
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()

def save_request(share):
    db_handler = DBHandler()
    return db_handler.add_share(share)

def start_server_thread(onNewShare=None):
    t = threading.Thread(target=start_server, args=[onNewShare])
    t.setDaemon(True)
    t.start()

if __name__ == '__main__':
    start_server()