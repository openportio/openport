import threading
from openport.services.logger_service import get_logger
logger = get_logger(__name__)

class TimeoutException(Exception):
    pass

def run_method_with_timeout(function, timeout_s, args=[], kwargs={}, raise_exception=True):
    return_value = [None]
    exception = [None]

    def method1():
        try:
            return_value[0] = function(*args, **kwargs)
        except Exception as e:
            exception[0] = e
            return

    thread = threading.Thread(target=method1)
    thread.daemon = True
    thread.start()

    thread.join(timeout_s)
    if exception[0] is not None:
        raise Exception(exception[0])
    if thread.is_alive():
        if raise_exception:
            #logger.error('Timeout!')
            raise TimeoutException('Timeout!')
    return return_value[0]


def _method(function, queue, args, kwargs):
    try:
        queue.put((function(*args, **kwargs), None))
    except Exception as e:
        queue.put((None, e))

def run_method_with_timeout__process(function, timeout_s, args=[], kwargs={}, raise_exception=True):

    from multiprocessing import Process, Queue
    q = Queue()
    p = Process(target=_method, args=(function, q, args, kwargs))
    p.start()
    p.join(timeout_s)
    if p.is_alive():
        if raise_exception:
            raise TimeoutException()
        return
    result = q.get()
    if result[1]:
        raise result[1]
    return result[0]