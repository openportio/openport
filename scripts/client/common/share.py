class Share():
    def __init__(self, id=-1, filePath='', server_ip='', server_port='', pid=-1, active=0, account_id=-1,
                 key_id=-1, local_port=-1, token='', server_session_token=''):
        self.id = id
        self.filePath = filePath
        self.server = server_ip
        self.server_port = server_port
        self.pid = pid
        self.active = active
        self.account_id = account_id
        self.key_id = key_id
        self.local_port = local_port
        self.token = token
        self.server_session_token = server_session_token

        self.success_observers = []
        self.error_observers = []

    def get_link(self):
        return 'http://%s:%s?t=%s' % (self.server, self.server_port, self.token)

    def as_dict(self):
        return {
            'id': self.id,
            'filePath': self.filePath,
            'server': self.server,
            'server_port': self.server_port,
            'pid': self.pid,
            'active': self.active,
            'account_id': self.account_id,
            'key_id': self.key_id,
            'local_port': self.local_port,
            'token': self.token,
            'server_session_token': self.server_session_token
        }

    def from_dict(self, dict):
        self.id = dict['id']
        self.filePath = dict['filePath']
        self.server = dict['server']
        self.server_port = dict['server_port']
        self.pid = dict['pid']
        self.active = dict['active']
        self.account_id = dict['account_id']
        self.key_id = dict['key_id']
        self.local_port = dict['local_port']
        self.token = dict['token']
        self.server_session_token = dict['server_session_token']


    def notify_success(self):
        for observer in self.success_observers:
            observer(self)

    def notify_error(self):
        for observer in self.error_observers:
            observer(self)
