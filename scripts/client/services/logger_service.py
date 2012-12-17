import logging
from sys import stdout
from services.osinteraction import OsInteraction

def get_logger(name):
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler(strm=stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    os_interaction = OsInteraction()
    if os_interaction.is_compiled():
        fh = logging.FileHandler(os_interaction.get_app_data_path('%s.log' % os_interaction.get_app_name()))
        fh.setFormatter(formatter)
        fh.setLevel(logging.WARNING)
        logger.addHandler(fh)

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
