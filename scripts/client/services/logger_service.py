import logging
import logging.handlers
from sys import stdout
from services import osinteraction

log_level = logging.INFO

loggers = {}

long_formatter = logging.Formatter('%(asctime)s - %(process)d:%(thread)d - %(name)s:%(lineno)d - %(levelname)s - %(message)s')
short_formatter = logging.Formatter('%(levelname)s - %(message)s')


def get_logger(name):
    if name in loggers:
        return loggers[name]
    logger = logging.getLogger(name)

    ch = logging.StreamHandler(stdout)
    ch.setFormatter(short_formatter)
    ch.setLevel(log_level)
    logger.addHandler(ch)

    os_interaction = osinteraction.getInstance(use_logger=False)
    fh = logging.handlers.RotatingFileHandler(os_interaction.get_app_data_path('%s.log' % os_interaction.get_app_name()),
                                              maxBytes=1000000, backupCount=5)
    fh.setFormatter(long_formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    loggers[name] = logger
    return logger


def set_log_level(new_log_level):
    global log_level
    log_level = new_log_level
    for name, logger in loggers.iteritems():
        for handler in logger.handlers:
            if type(handler) is logging.StreamHandler:
                handler.setLevel(log_level)
                if log_level == logging.DEBUG:
                    handler.setFormatter(long_formatter)

if __name__ == '__main__':
    logger = get_logger('test')
    i = 1
    logger.error('%d error' % i) ; i += 1
    logger.debug('%d debug' % i) ; i += 1
    logger.info('%d info' % i) ; i += 1
    logger.critical('%d critical' % i) ; i += 1
    logger.warning('%d warning' % i) ; i += 1
    logger.exception('%d exception' % i) ; i += 1

    set_log_level(logging.DEBUG)

    logger.debug('%d debug' % i) ; i += 1

