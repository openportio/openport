from Queue import Queue
from time import sleep
import os
import pickle
from pysqlite2 import dbapi2 as sqlite
from common.session import Session
from services import osinteraction


class DBTask(object):
    def __init__(self, command, args=[]):
        self.ready = False
        self.command = command
        self.args = args

    def block(self):
        while not self.ready:
            sleep(0.01)


class DBCommandTask(DBTask):

    def execute(self, cursor, connection):
        cursor.execute(self.command, self.args)
        connection.commit()
        self.ready = True


class DBQueryTask(DBTask):
    def __init__(self, query, args=[]):
        super(DBQueryTask, self).__init__(query, args)
        self.result = None

    def execute(self, cursor, connection):
        cursor.execute(self.command, self.args)
        self.result = cursor.fetchall()
        self.ready = True


class DBHandler():

    def __init__(self, db_location):
        self.os_interaction = osinteraction.getInstance()
        self.db_location = db_location

        self.task_queue = Queue()
        self.startQueueThread()

    def checkQueue(self):
        self.connection = sqlite.connect(self.db_location)
        self.cursor = self.connection.cursor()
        while True:
            task = self.task_queue.get(block=True)
            task.execute(self.cursor, self.connection)
            self.task_queue.task_done()

    def startQueueThread(self):
        import threading
        t = threading.Thread(target=self.checkQueue)
        t.setDaemon(True)
        t.start()

    def executeCommand(self, command, args=[]):
        task = DBCommandTask(command, args)
        self.task_queue.put(task, block=True)
        task.block()

    def executeQuery(self, query, args=[]):
        task = DBQueryTask(query, args)
        self.task_queue.put(task, block=True)
        task.block()
        return task.result

    def init_db(self):
        self.executeCommand(
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
        self.executeCommand('update sessions set active = 0 where local_port = ?', (share.local_port,))
        pickled_restart_command = pickle.dumps(share.restart_command).encode('UTF-8', 'ignore')

        self.executeCommand('insert into sessions (server, server_port, session_token, local_port, pid, active, restart_command) '
                            'values (?, ?, ?, ?, ?, ?, ?)',
            (share.server, share.server_port, share.server_session_token, share.local_port, share.pid, 1, pickled_restart_command))
        share.id = self.cursor.lastrowid
        return self.get_share(self.cursor.lastrowid)

    def get_share(self, id):
        rows = self.executeQuery('select server, server_port, session_token, local_port, pid, active, restart_command, '
                                 'id from sessions where id = ?', (id,))
        return self.get_share_from_row(rows[0])

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
        rows = self.executeQuery('select server, server_port, session_token, local_port, pid, active, restart_command, '
                                 'id from sessions where active = 1')
        return list(self.get_share_from_row(row) for row in rows)

    def stop_share(self, share):
        self.executeCommand('update sessions set active = 0 where id = ?', (share.id,))


instance = None

db_location = ''

def getInstance():
    if db_location == '':
        os_interaction = osinteraction.getInstance()
        global db_location
        db_location = os_interaction.get_app_data_path('openport.db')

    global instance
    if instance is None:
        instance = DBHandler(db_location)
        instance.init_db()
    return instance


if __name__ == '__main__':
    db_handler = getInstance()
    rows = db_handler.executeQuery('select count(*) from sessions')
    print 'nr of sessions: %s' % rows[0][0]


