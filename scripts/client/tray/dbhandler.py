import os
import pickle
from pysqlite2 import dbapi2 as sqlite
from common.share import Share
from common.session import Session
from services import osinteraction

class DBHandler():

    def __init__(self):
        self.os_interaction = osinteraction.getInstance()
        self.connection = sqlite.connect(self.os_interaction.get_app_data_path('openport.db'))
        self.cursor = self.connection.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            server VARCHAR(50),
            server_port INTEGER,
            session_token VARCHAR(50),
            local_port INTEGER,
            pid INTEGER,
            active BOOLEAN,
            restart_command VARCHAR(200)
            )
            ''')

    def add_share(self,share):
        self.cursor.execute('update sessions set active = 0 where local_port = ?', (share.local_port,))
        pickled_restart_command = pickle.dumps(share.restart_command).encode('UTF-8', 'ignore')

        self.cursor.execute('insert into sessions (server, server_port, session_token, local_port, pid, active, restart_command) '
                            'values (?, ?, ?, ?, ?, ?, ?)',
            (share.server, share.server_port, share.server_session_token, share.local_port, share.pid, 1, pickled_restart_command))
        self.connection.commit()
        share.id = self.cursor.lastrowid
        return self.get_share(self.cursor.lastrowid)

    def get_share(self, id):
        self.cursor.execute('select server, server_port, session_token, local_port, pid, active, restart_command, id from sessions'
                            ' where id = ?', (id,))
        row = self.cursor.fetchone()
        return self.get_share_from_row(row)

    def get_share_from_row(self, row):
        share = Session()
        share.server = row[0]
        share.server_port = row[1]
        share.server_session_token = row[2]
        share.local_port = row[3]
        share.pid = row[4]
        share.active = row[5]
        share.restart_command = row[6].split()
        try:
            share.restart_command = pickle.loads(row[6].encode('ascii','ignore'))
            pass
        except (Exception) as e:
            pass

        share.id = row[7]
        return share


    def get_shares(self):
        self.cursor.execute('select server, server_port, session_token, local_port, pid, active, restart_command, id from sessions'
                            ' where active = 1')
        return (self.get_share_from_row(row) for row in self.cursor)

    def stop_share(self, share):
        self.cursor.execute('update sessions set active = 0 where id = ?', (share.id,))
        self.connection.commit()





