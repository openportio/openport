import logging
import pickle
import shutil
from pathlib import Path
from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from openport.services.dbhandler import OpenportSession

logger = logging.getLogger(__name__)


class DBTest(TestCase):
    def test_old_1_3_1_format(self):
        old_db_file = 'openport-1.3.0_3.db'

        old_db = Path(__file__).parent / 'testfiles' / old_db_file
        old_db_tmp = Path(__file__).parent / 'testfiles' / 'tmp' / old_db_file
        shutil.copy(old_db, old_db_tmp)

        self.engine = create_engine('sqlite:///%s' % old_db_tmp, echo=True)
        self.session_factory = sessionmaker(bind=self.engine)
        logger.debug('db location: %s' % old_db_tmp)
        self.Session = scoped_session(self.session_factory)

        session = self.Session()
        openport_session = session.query(OpenportSession).one()

        b = openport_session.restart_command if type(
            openport_session.restart_command) == bytes else openport_session.restart_command.encode('utf-8')
        try:
            openport_session.restart_command = pickle.loads(b)
        except Exception as e:
            try:
                openport_session.restart_command = b.split()
            except:
                raise e
        print(f"<<<{openport_session.restart_command}>>>")
