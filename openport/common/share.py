from openport.common.session import Session

class Share(Session):
    def __init__(self, filePath='', token='', *args, **kwargs):
        super(Share, self).__init__(*args, **kwargs)
        self.filePath = filePath
        self.token = token

    def as_dict(self):
        dict = super(Share, self).as_dict()
        dict['type'] = 'Share'
        dict['filePath'] = self.filePath
        dict['token'] = self.token
        return dict

    def from_dict(self, dict):
        super(Share, self).from_dict(dict)
        self.filePath = dict['filePath']
        self.token = dict['token']
        return self

    def get_link(self):
        return 'http://%s:%s?t=%s' % (self.server, self.server_port, self.token)
