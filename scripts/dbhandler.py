from pysqlite2 import dbapi2 as sqlite

class DBHandler():

    def __init__(self):
        self.connection = sqlite.connect('openport.db')
        self.cursor = self.connection.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            filePath VARCHAR(200),
            server VARCHAR(50),
            port INTEGER

            )
            ''')

    def add_file(self,path, server, port):
        self.cursor.execute('insert into files (filePath, server, port) values (?, ?, ?)',  (path, server, port))
        self.connection.commit()

    def remove_file(self, id):
        self.cursor.execute('delete from files where id = ?',  (id,))
        self.connection.commit()

    def get_files(self):
        self.cursor.execute('select id, filePath, server, port from files')
        return [row for row in self.cursor]

