__author__ = 'jan'

import os

from openport.common.config_file_handler import ConfigFileHandler
from openport.services import osinteraction
from openport.services.logger_service import get_logger
from openport.services.app_service import AppService

logger = get_logger(__name__)


class ConfigService(object):
    def __init__(self, openport_app_config):
        self.config = openport_app_config
        self.app_service = AppService(openport_app_config)


    def get_and_save_random_manager_port(self):
        config = ConfigFileHandler(self.config.config)
        manager_port = osinteraction.getInstance().get_open_port()
       # manager_port = 22
        self.config.manager_port = manager_port
        config.set('manager', 'port', manager_port)
        self.config.manager_port_from_config_file = True
        return manager_port


    def get_and_save_manager_port(self, manager_port_from_command_line=-1, exit_on_fail=True):
        if manager_port_from_command_line > 0:
            original_port = manager_port_from_command_line
        else:
            # Read port from file (if file, section and entry exist)
            config = ConfigFileHandler(self.config.config)
            try:
                self.config.manager_port = config.get_int('manager', 'port')
                self.config.manager_port_from_config_file = True
                original_port = self.config.manager_port
            except:
                manager_port = self.get_and_save_random_manager_port()
                logger.debug("Manager port not found in config file. Starting manager on port %s." % manager_port)
                return manager_port

        try:
            running = self.app_service.manager_is_running(original_port)
        except:  # An other app is running on that port
            manager_port = self.get_and_save_random_manager_port()
            if original_port != -1:
                logger.info("Port %s is taken by another application. Manager is now running on port %s." %
                            (original_port, manager_port))
            return manager_port
        else:
            if running:
                if exit_on_fail:
                    logger.info('Manager is already running on port %s. Exiting.' % self.config.manager_port)
                    os._exit(1)
                else:
                    return original_port
            else:
                self.config.manager_port = original_port
                return self.config.manager_port
