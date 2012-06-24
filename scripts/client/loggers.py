import logging
from sys import stdout

def get_logger(name):
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler(strm=stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    return logger

if __name__ == '__main__':
    logger = get_logger('test')
    i = 1
    logger.error('%d error' % i) ; i += 1
    logger.debug('%d debug' % i) ; i += 1
    logger.info('%d info' % i) ; i += 1
    logger.critical('%d critical' % i) ; i += 1
    logger.warning('%d warning' % i) ; i += 1
    logger.exception('%d exception' % i) ; i += 1
