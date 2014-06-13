import fcntl
import os

def nonBlockRead(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return output.read()
    except:
        return False


def get_all_output(p):
    if p.poll() is None:
        return nonBlockRead(p.stdout), nonBlockRead(p.stderr)
    else:
        return p.stdout.read(), p.stderr.read()