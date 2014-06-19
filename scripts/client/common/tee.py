import sys

class TeeStdOut(object):
    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout
        sys.stdout = self

    def close(self):
        if self.stdout is not None:
            sys.stdout = self.stdout
            self.stdout = None
        if self.file is not None:
            self.file.close()
            self.file = None

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()

    def __del__(self):
        self.close()


class TeeStdErr(object):
     def __init__(self, name, mode):
         self.file = open(name, mode)
         self.stderr = sys.stderr
         sys.stderr = self

     def close(self):
         if self.stderr is not None:
             sys.stderr = self.stderr
             self.stderr = None
         if self.file is not None:
             self.file.close()
             self.file = None

     def write(self, data):
         self.file.write(data)
         self.stderr.write(data)

     def flush(self):
         self.file.flush()
         self.stderr.flush()

     def __del__(self):
         self.close()