import cgi, urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import threading
import traceback
from openportit import open_port_file
from dbhandler import DBHandler

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

            open_port_file(path, callback=save_request, extra_args={'path':path})
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

def start_server():
    try:
        server = HTTPServer(('', 8001), ShareRequestHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()


def showMessage(server_ip, server_port):

    from Tkinter import Tk
    r = Tk()
    r.withdraw()
    r.clipboard_clear()
    file_address = '%s:%s'%(server_ip, server_port)
    print file_address
    r.clipboard_append(file_address.strip())
    r.destroy()

    import wx
    wx.MessageBox('You can now download your file(s) from %s:%s\nThis link has been copied to your clipboard.' %(server_ip, server_port), 'Info', wx.OK | wx.ICON_INFORMATION)


def save_request(server, port, extra_args):
    db_handler = DBHandler()
    db_handler.add_file(extra_args['path'], server, port)
    showMessage(server, port)

def start_server_thread():
    t = threading.Thread(target=start_server)
    t.setDaemon(True)
    t.start()

if __name__ == '__main__':
    start_server()