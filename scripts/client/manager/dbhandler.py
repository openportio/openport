from Queue import Queue, Empty
from time import sleep
import pickle
import traceback
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    import sqlite3 as sqlite
from common.session import Session
from services.logger_service import get_logger
from services import osinteraction

logger = get_logger('dbhandler')

TIMEOUT = 10


class TimeOutException(BaseException):
    pass


class DBTask(object):
    def __init__(self, command, args=None):
        self.ready = False
        self.command = command
        self.args = args if args is not None else []
        self.exception = None

    def block(self, timeout=None):
        time = 0
        while not self.ready:
            if timeout is not None and time > timeout:
                raise TimeOutException()
            time += 0.01
            sleep(0.01)


class DBCommandTask(DBTask):

    def execute(self, cursor, connection):
        logger.debug('running command: %s' % self.command)
        try:
            cursor.execute(self.command, self.args)
            connection.commit()
        except Exception, e:
            self.exception = e
        finally:
            self.ready = True


class DBQueryTask(DBTask):
    def __init__(self, query, args=None):
        super(DBQueryTask, self).__init__(query, args)
        self.result = None

    def execute(self, cursor, connection):
        logger.debug('running query: %s' % self.command)
        try:
            cursor.execute(self.command, self.args)
            self.result = cursor.fetchall()
        except Exception, e:
            self.exception = e
        finally:
            self.ready = True


class DBHandler(object):

    def __init__(self, db_location):
        self.os_interaction = osinteraction.getInstance()
        self.db_location = db_location

        self.task_queue = Queue()
        self.stopped = False
        self.startQueueThread()
        self.queue_exception = None

    def checkQueue(self):
        try:
            self.connection = sqlite.connect(self.db_location)
            self.cursor = self.connection.cursor()
            while not self.stopped:
                try:
                    task = self.task_queue.get(block=True, timeout=1)
                    task.execute(self.cursor, self.connection)
                    self.task_queue.task_done()
                except Empty:
                    pass
        except Exception, e:
            tb = traceback.format_exc()
            logger.debug('%s\n%s' % (e, tb))
            self.queue_exception = e
        finally:
            self.connection.close()


    def startQueueThread(self):
        import threading
        t = threading.Thread(target=self.checkQueue)
        t.setDaemon(True)
        t.start()

    def executeCommand(self, command, args=None):
        if self.queue_exception:
            raise self.queue_exception
        task = DBCommandTask(command, args)
        self.task_queue.put(task, block=True)
        task.block(TIMEOUT)
        if task.exception:
            raise task.exception

    def executeQuery(self, query, args=None):
        if self.queue_exception:
            raise self.queue_exception
        task = DBQueryTask(query, args)
        self.task_queue.put(task, block=True)
        task.block(TIMEOUT)
        if task.exception:
            raise task.exception
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

    def add_share(self, share):
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

    def get_share_by_local_port(self, local_port):
        rows = self.executeQuery('select server, server_port, session_token, local_port, pid, active, restart_command, '
                                 'id from sessions where active = 1 and local_port=%s' % local_port)
        return list(self.get_share_from_row(row) for row in rows)

    def stop_share(self, share):
        self.executeCommand('update sessions set active = 0 where id = ?', (share.id,))

    def stop(self):
        self.stopped = True

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
    if instance is not None:
        instance.stop()
    instance = None


if __name__ == '__main__':
    db_handler = getInstance()
    rows = db_handler.executeQuery('select count(*) from sessions')
    print 'nr of sessions: %s' % rows[0][0]


