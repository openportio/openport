import threading
from logger_service import get_logger
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

    thread = threading.Thread(target=method1)
    thread.daemon = True
    thread.start()

    thread.join(timeout_s)
    if exception[0] is not None:
        raise exception[0]
    if thread.is_alive():
        if raise_exception:
            #logger.error('Timeout!')
            raise TimeoutException('Timeout!')
    return return_value[0]