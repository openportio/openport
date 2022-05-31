import pickle

DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS = 10


class Session(object):
    def __init__(self, _id=-1, server_ip='', server_port=-1, pid=-1, active=False, account_id=-1,
                 key_id=-1, local_port=-1, server_session_token='', restart_command='', http_forward=False,
                 http_forward_address='', open_port_for_ip_link='', app_management_port=-1,
                 forward_tunnel=False, ip_link_protection=None, keep_alive_interval_seconds=10, proxy='',
                 ssh_server=''):
        # todo: why is this ever a dict?
        if type(_id) == dict:
            self.id = -1
        else:
            self.id = _id
        self.server = server_ip
        self.server_port = server_port
        self.pid = pid
        self.active = active
        self.account_id = account_id
        self.key_id = key_id
        self.local_port = local_port
        self.server_session_token = server_session_token
        self.restart_command = restart_command
        self.http_forward = http_forward
        self.http_forward_address = http_forward_address
        self.open_port_for_ip_link = open_port_for_ip_link
        self.app_management_port = app_management_port
        self.forward_tunnel = forward_tunnel
        self.ip_link_protection = ip_link_protection
        self.keep_alive_interval_seconds = keep_alive_interval_seconds
        self.proxy = proxy
        self.ssh_server = ssh_server

        self.public_key_file = None
        self.private_key_file = None

        self.success_observers = []
        self.error_observers = []
        self.start_observers = []
        self.stop_observers = []

    def get_link(self):
        if self.http_forward_address:
            return self.http_forward_address
        return '%s:%s' % (self.server, self.server_port)

    def as_dict(self):
        return {
            'type':'Session',
            'id': self.id,
            'server': self.server,
            'server_port': self.server_port,
            'pid': self.pid,
            'active': self.active,
            'account_id': self.account_id,
            'key_id': self.key_id,
            'local_port': self.local_port,
            'server_session_token': self.server_session_token,
            'restart_command' : pickle.dumps(self.restart_command),
            'http_forward': self.http_forward,
            'http_forward_address': self.http_forward_address,
            'open_port_for_ip_link': self.open_port_for_ip_link,
            'app_management_port': self.app_management_port,
            'forward_tunnel': self.forward_tunnel,
            'ip_link_protection': self.ip_link_protection,
            'keep_alive_interval_seconds': self.keep_alive_interval_seconds,
            'proxy': self.proxy,
        }

    @staticmethod
    def str_to_bool(string):
        s = '%s' % string
        return s.lower() in ['true', 't', '1', 'yes']

    # todo: make statics
    def from_dict(self, dict):
        try:
            self.id = int(dict['id'])
        except ValueError as e:
            self.id = ''
        self.server = dict['server']
        self.server_port = dict['server_port']
        try:
            self.pid = int(dict['pid'])
        except ValueError as e:
            self.pid = dict['pid']
        self.active = Session.str_to_bool(dict['active'])
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        self.local_port = int(dict.get('local_port', -1))
        self.server_session_token = dict['server_session_token']
        self.restart_command = pickle.loads(dict['restart_command'])
        self.http_forward = Session.str_to_bool(dict['http_forward'])
        self.http_forward_address = dict['http_forward_address']
        self.app_management_port = dict['app_management_port']
        self.open_port_for_ip_link = dict.get('open_port_for_ip_link', '')
        self.forward_tunnel = dict.get('forward_tunnel', False)
        self.ip_link_protection = dict.get('ip_link_protection', None)
        self.keep_alive_interval_seconds = dict.get('keep_alive_interval_seconds', None)
        self.proxy = dict.get('proxy', '')
        return self

    def get_proxy_dict(self):
        if self.proxy:
            return {
                'http': self.proxy,
                'https': self.proxy,
            }
        else:
            return {}



    def notify_success(self):
        for observer in self.success_observers:
            observer(self)

    def notify_error(self, exception):
        for observer in self.error_observers:
            observer(self, exception)

    def notify_start(self):
        self.active = True
        for observer in self.start_observers:
            observer(self)

    def notify_stop(self):
        self.active = False
        for observer in self.stop_observers:
            observer(self)
