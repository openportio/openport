
from ctypes import WINFUNCTYPE, windll
from ctypes.wintypes import BOOL, DWORD
from time import sleep
import os



kernel32 = windll.LoadLibrary('kernel32')
PHANDLER_ROUTINE = WINFUNCTYPE(BOOL, DWORD)
SetConsoleCtrlHandler = kernel32.SetConsoleCtrlHandler
SetConsoleCtrlHandler.argtypes = (PHANDLER_ROUTINE, BOOL)
SetConsoleCtrlHandler.restype = BOOL

CTRL_C_EVENT = 0


@PHANDLER_ROUTINE
def console_handler(ctrl_type):
    if ctrl_type == CTRL_C_EVENT:
        print 'ctrl + c'
    else:
        print 'got signal % s' % ctrl_type
    return False


def _add_handler():
    if not SetConsoleCtrlHandler(console_handler, True):
        raise RuntimeError('SetConsoleCtrlHandler failed.')


def main():
    print 'pid: %s' % (os.getpid(),)
    _add_handler()
    while True:
        sleep(1)


if __name__ == '__main__':
    main()
