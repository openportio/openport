import os
from common.singleton import Singleton
DEFAULT_SERVER = 'https://www.openport.io'


class OpenportAppConfig(object):

    def __init__(self):
        self.account_id = -1
        self.key_id = -1
        self.openport_address = DEFAULT_SERVER
        self.manager_port = -1
        self.manager_port_from_config_file = False
        self.config = os.path.expanduser('~{}/.openport/openport.cfg'.format(os.environ.get('USER', '')))
        self.contact_manager = True
        self.verbose = False
        self.tcp_listeners = set()

        self.app = None
