__author__ = 'jan'

from manager.globals import Globals
from common.config_file_handler import ConfigFileHandler
from services import osinteraction
from services.logger_service import get_logger
from services.app_service import manager_is_running
import os
logger = get_logger(__name__)

def get_and_save_random_manager_port():
    config = ConfigFileHandler(Globals().config)
    manager_port = osinteraction.getInstance().get_open_port()
   # manager_port = 22
    Globals().manager_port = manager_port
    config.set('manager', 'port', manager_port)
    Globals().manager_port_from_config_file = True
    return manager_port


def get_and_save_manager_port(manager_port_from_command_line=-1, exit_on_fail=True):
    original_port = Globals().manager_port

    if manager_port_from_command_line > 0:
        original_port = manager_port_from_command_line
    else:
        # Read port from file (if file, section and entry exist)
        config = ConfigFileHandler(Globals().config)
        try:
            Globals().manager_port = config.get_int('manager', 'port')
            Globals().manager_port_from_config_file = True
            original_port = Globals().manager_port
        except:
            manager_port = get_and_save_random_manager_port()
            logger.info("Manager port not found in config file. Starting manager on port %s." % manager_port)
            return manager_port

    try:
        running = manager_is_running(original_port)
    except:  # An other app is running on that port
        manager_port = get_and_save_random_manager_port()
        if original_port != -1:
            logger.info("Port %s is taken by another application. Manager is now running on port %s." %
                        (original_port, manager_port))
        return manager_port
    else:
        if running:
            if exit_on_fail:
                logger.info('Manager is already running on port %s. Exiting.' % Globals().manager_port)
                os._exit(1)
            else:
                return original_port
        else:
            Globals().manager_port = original_port
            return Globals().manager_port

