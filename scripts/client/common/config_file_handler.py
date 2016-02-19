__author__ = 'jan'
import os
import ConfigParser


class ConfigFileHandler(object):
    def __init__(self, config_location):
        self.config_parser = ConfigParser.ConfigParser()
        self.config_location = config_location

        if os.path.exists(self.config_location):
            self.config_parser.read(self.config_location)

    def get(self, section, key):
        return self.config_parser.get(section, key)

    def get_int(self, section, key):
        return self.config_parser.getint(section, key)

    def set(self, section, key, value, write=True):
        if not self.config_parser.has_section(section):
            self.config_parser.add_section(section)
        self.config_parser.set(section, key, value)
        if write:
            self.write()

    def write(self, location=None):
        if not location:
            location = self.config_location

        if not os.path.exists(os.path.dirname(location)):
            os.makedirs(os.path.dirname(location), mode=0600)

        with open(location, 'w') as f:
            self.config_parser.write(f)