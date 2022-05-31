from typing import List

import sys
import os
import pickle
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.exc import NoResultFound

from openport.common.session import Session
from openport.services.logger_service import get_logger
from openport.services import osinteraction, migration_service

logger = get_logger('dbhandler')

# Configures the logging for SQLAlchemy
sqlalchemy_logger = get_logger('sqlalchemy')

for handler in sqlalchemy_logger.handlers:
    handler.setLevel(logging.WARN)

Base = declarative_base()


class OpenportSession(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    server = Column(String(50))
    # ssh_server = Column(String(50))
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

    app_management_port = Column(Integer)
    open_port_for_ip_link = Column(String(150))
    # forward_tunnel = Column(Boolean)

    def __repr__(self):
       return "<Session(local_port='%s', remote_port='%s', session_token='%s')>" % (
                            self.local_port, self.server_port, self.session_token)


class DBHandler(object):

    def __init__(self, db_location=None, init_db=True, echo_queries=False):
        self.osinteraction = osinteraction.getInstance()

        if not db_location:
            db_location = self.osinteraction.get_app_data_path('openport.db')

        db_exists = os.path.exists(db_location)
        logger.debug('db location: %s' % db_location)
        self.engine = create_engine('sqlite:///%s' % db_location, echo=echo_queries)
        self.db_location = db_location
        self.session_factory = sessionmaker(bind=self.engine)
        logger.debug('db location: %s' % db_location)
        self.Session = scoped_session(self.session_factory)

        if init_db:
            self.init_db(db_exists)

    def init_db(self, db_exists):
            if db_exists:
                # check alembic tables exists
                result = self.engine.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                alembic_table_count = len(list(result))
                result.close()
                if alembic_table_count <= 0:
                    # if not, put it in the state of version 0.9.1
                    self.engine.execute("CREATE TABLE alembic_version (	version_num VARCHAR(32) NOT NULL )")
                    self.engine.execute("INSERT INTO alembic_version (version_num) VALUES ('init')")

            self.osinteraction.run_function_with_lock(migration_service.update_if_needed, '%s.lock' % self.db_location, args=[self.db_location])

    def _get_session(self):
        logger.debug('getting session')
        return self.Session()

    def init_db_without_migrations(self):
        logger.debug('init_db')
        Base.metadata.create_all(self.engine)
        self.Session.remove()

    def close(self):
        logger.debug('closing')
        self.engine.dispose()

    def add_share(self, share):
        logger.debug('add share')
        session = self._get_session()

        openport_session = None
        if share.id > 0:
            openport_session = session.query(OpenportSession).filter_by(id=share.id).first()

        if openport_session is None:
            openport_session = session.query(OpenportSession).filter_by(local_port=share.local_port).first()

        new_entry = False
        if openport_session is None:
            openport_session = OpenportSession()
            new_entry = True

        openport_session.server = share.server
        openport_session.remote_port = share.server_port
        openport_session.session_token = share.server_session_token
        openport_session.local_port = share.local_port
        openport_session.pid = share.pid
        openport_session.active = share.active
        openport_session.restart_command = self.pickle_restart_command(share)
        openport_session.account_id = share.account_id
        openport_session.key_id = share.key_id
        openport_session.http_forward = share.http_forward
        openport_session.http_forward_address = share.http_forward_address
        openport_session.app_management_port = share.app_management_port
        openport_session.open_port_for_ip_link = share.open_port_for_ip_link

        if new_entry:
            session.add(openport_session)
        session.commit()

        for other_session in session.query(OpenportSession).filter_by(local_port=share.local_port):
            if other_session.id == openport_session.id:
                continue
            session.delete(other_session)
        session.commit()

        share.id = openport_session.id
        self.Session.remove()
        return self.get_share(openport_session.id)

    def pickle_restart_command(self, share):
        try:
            return pickle.dumps(share.restart_command).encode('UTF-8', 'ignore')
        except AttributeError:
            return pickle.dumps(share.restart_command)

    def get_share(self, id):
        logger.debug('get_share')
        session = self._get_session()
        try:
            openport_session = session.query(OpenportSession).filter_by(id=id).one()
        except NoResultFound:
            return None
        share = self.convert_session_from_db(openport_session)
        self.Session.remove()
        return share

    def convert_session_from_db(self, openport_session: OpenportSession) -> Session:
        if openport_session is None:
            return None

        logger.debug('convert_session_from_db')

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
        share.app_management_port = openport_session.app_management_port
        share.open_port_for_ip_link = openport_session.open_port_for_ip_link
        share.restart_command = openport_session.restart_command
        # share.forward_tunnel = openport_session.forward_tunnel
        # share.ssh_server = openport_session.ssh_server
        b = share.restart_command if type(share.restart_command) == bytes else share.restart_command.encode('utf-8')
        try:
            share.restart_command = pickle.loads(b)
        except Exception as e:
            try:
                share.restart_command = b.split()
            except:
                raise e

        return share

    def get_active_shares(self) -> List[OpenportSession]:
        logger.debug('get_active_shares')

        session = self._get_session()
        openport_sessions = list(session.query(OpenportSession).filter_by(active=True))
        openport_sessions = [s for s in openport_sessions if s.remote_port > 0]
        l = list(self.convert_session_from_db(openport_session) for openport_session in openport_sessions)
        self.Session.remove()
        return l

    def get_shares_to_restart(self):
        logger.debug('get_shares_to_restart')

        session = self._get_session()
        openport_sessions = session.query(OpenportSession).filter(OpenportSession.restart_command.isnot(''))
        l = self.filter_sessions_with_restart_command(openport_sessions)
        self.Session.remove()
        return l

    def filter_sessions_with_restart_command(self, openport_sessions):
        l = [self.convert_session_from_db(openport_session) for openport_session in openport_sessions
                 if self.convert_session_from_db(openport_session).restart_command]
        return l

    def get_share_by_local_port(self, local_port, filter_active=True):
        logger.debug('get_share_by_local_port')

        session = self._get_session()
        kwargs = {'local_port': local_port}
        if filter_active:
            kwargs['active'] = True

        openport_session = session.query(OpenportSession).filter_by(**kwargs).order_by(OpenportSession.id.desc()).first()

        self.Session.remove()
        return self.convert_session_from_db(openport_session)

    def stop_share(self, share, restart=True):
        logger.debug('stop_share')
        session = self._get_session()
        openport_session = session.query(OpenportSession).filter_by(id=share.id).first()
        if openport_session:
            openport_session.active = False
            if not restart:
                openport_session.restart_command = ''
            session.commit()
        self.Session.remove()

    def get_all_shares(self):
        logger.debug('get_all_shares')
        session = self._get_session()
        openport_sessions = session.query(OpenportSession).all()
        l = list(self.convert_session_from_db(openport_session) for openport_session in openport_sessions)
        self.Session.remove()
        return l


if __name__ == '__main__':
    db_handler = DBHandler()
    shares = db_handler.get_active_shares()
    print('nr of sessions: %s' % len(shares))


