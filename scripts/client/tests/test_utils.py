import socket
import sys
from time import sleep
import inspect

class SimpleTcpServer(object):

    def __init__(self, port):
        self.HOST = '127.0.0.1' # Symbolic name meaning the local host
        self.PORT = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((self.HOST, self.PORT))
        self.s.listen(5)
        self.connections_accepted = 0

    def run(self):
        while 1:
            print "connections accepted: ", self.connections_accepted
            self.connections_accepted += 1
            conn, self.address = self.s.accept()
            print 'Connected by', self.address
            data = conn.recv(1024)
            if data:
                conn.send(data)
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

    def close(self):
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()

    def runThreaded(self):
        import threading
        thr = threading.Thread(target=self.run, args=())
        thr.setDaemon(True)
        thr.start()

class SimpleTcpClient(object):
    def __init__(self, host, port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
#            sys.exit(1)

        try:
            self.sock.connect((host, port))
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
#            sys.exit(2)


    def send(self, request):
        self.sock.send('%s\n' % request)

        data = self.sock.recv(1024)
        response = ""
        while len(data):
            response += data
            data = self.sock.recv(1024)
        return response

    def close(self):
        self.sock.close()

def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port

def lineNumber():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

if __name__ == '__main__':

    port = get_open_port()
    s = SimpleTcpServer(port)
    s.runThreaded()
    sleep(1)

    c = SimpleTcpClient('localhost', port)

    var = raw_input('Enter something: ')
    print 'you entered ', var
    print 'server replied', c.send(var)