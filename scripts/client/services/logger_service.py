import logging
from sys import stdout
from services import osinteraction

log_level = logging.INFO

loggers = {}

def get_logger(name):
    if name in loggers:
        return loggers[name]
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler(stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    os_interaction = osinteraction.getInstance(use_logger=False)
    fh = logging.FileHandler(os_interaction.get_app_data_path('%s.log' % os_interaction.get_app_name()))
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.setLevel(log_level)
    loggers[name] = logger
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

def set_log_level(new_log_level):
    global log_level
    log_level = new_log_level
    for name, logger in loggers.iteritems():
        logger.setLevel(log_level)
