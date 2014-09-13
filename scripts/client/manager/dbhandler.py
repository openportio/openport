import pickle
from common.session import Session
from services.logger_service import get_logger
from services import osinteraction

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker

logger = get_logger('dbhandler')

Base = declarative_base()

class OpenportSession(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    server = Column(String(50))
    remote_port = Column(Integer)
    session_token = Column(String(50))
    local_port = Column(Integer)
    pid = Column(Integer)
    active = Column(Boolean)
    restart_command = Column(String(200))

    account_id = Column(Integer)
    key_id = Column(Integer)
    http_forward = Column(Boolean)
    http_forward_address = Column(String(50))

    def __repr__(self):
       return "<Session(local_port='%s', remote_port='%s', session_token='%s')>" % (
                            self.local_port, self.server_port, self.session_token)


class DBHandler(object):

    def __init__(self, db_location):
        self.engine = create_engine('sqlite:///%s' % db_location, echo=True)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.os_interaction = osinteraction.getInstance()
        self.db_location = db_location
        logger.debug('db location: %s' % db_location)

    def init_db(self):
        Base.metadata.create_all(self.engine)

    def add_share(self, share):
        openport_session = OpenportSession()

        openport_session.server = share.server
        openport_session.remote_port = share.server_port
        openport_session.session_token = share.server_session_token
        openport_session.local_port = share.local_port
        openport_session.pid = share.pid
        openport_session.active = share.active
        openport_session.restart_command = pickle.dumps(share.restart_command).encode('UTF-8', 'ignore')
        openport_session.account_id = share.account_id
        openport_session.key_id = share.key_id
        openport_session.http_forward = share.http_forward
        openport_session.http_forward_address = share.http_forward_address

        for previous_session in self.session.query(OpenportSession).filter_by(local_port=share.local_port):
            previous_session.active = False

        self.session.add(openport_session)
        self.session.commit()

        share.id = openport_session.id
        return self.get_share(openport_session.id)

    def get_share(self, id):
        openport_session = self.session.query(OpenportSession).filter_by(id=id).one()
        return self.convert_session_from_db(openport_session)

    def convert_session_from_db(self, openport_session):
        share = Session()
        share.id = openport_session.id
        share.server = openport_session.server
        share.server_port = openport_session.remote_port
        share.server_session_token = openport_session.session_token
        share.local_port = openport_session.local_port
        share.pid = openport_session.pid
        share.active = openport_session.active
        share.account_id = openport_session.account_id
        share.key_id = openport_session.key_id
        share.http_forward = openport_session.http_forward
        share.http_forward_address = openport_session.http_forward_address

        share.restart_command = openport_session.restart_command
        try:
            share.restart_command = pickle.loads(share.restart_command.encode('ascii', 'ignore'))
            pass
        except Exception as e:
            pass

        return share

    def get_shares(self):
        openport_sessions = self.session.query(OpenportSession).filter_by(active=True)
        return list(self.convert_session_from_db(openport_session) for openport_session in openport_sessions)

    def get_share_by_local_port(self, local_port):
        openport_sessions = self.session.query(OpenportSession).filter_by(active=True, local_port=local_port)
        return list(self.convert_session_from_db(openport_session) for openport_session in openport_sessions)


    def stop_share(self, share):
        openport_session = self.session.query(OpenportSession).filter_by(id=share.id)
        openport_session.active = False
        self.session.commit()

instance = None

db_location = ''


def getInstance():
    global db_location

    if db_location == '':
        os_interaction = osinteraction.getInstance()
        db_location = os_interaction.get_app_data_path('openport.db')

    global instance
    if instance is None:
        instance = DBHandler(db_location)
        instance.init_db()
    return instance


def destroy_instance():
    global instance
    instance = None


if __name__ == '__main__':
    db_handler = getInstance()
    rows = db_handler.executeQuery('select count(*) from sessions')
    print 'nr of sessions: %s' % rows[0][0]


