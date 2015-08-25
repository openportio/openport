import threading
from logger_service import get_logger
logger = get_logger(__name__)


def run_method_with_timeout(function, timeout_s, args=[], kwargs={}, raise_exception=True):
    return_value = [None]

    def method1():
        return_value[0] = function(*args, **kwargs)

    thread = threading.Thread(target=method1)
    thread.daemon = True
    thread.start()

    thread.join(timeout_s)
    if thread.is_alive():
        if raise_exception:
            logger.error('Timeout!')
            raise Exception('Timeout!')
    return return_value[0]