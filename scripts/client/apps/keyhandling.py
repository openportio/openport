import os
import paramiko
import StringIO
from services.logger_service import get_logger

log = get_logger(__name__)


HOME_DIR = os.path.expanduser('~')

if len(HOME_DIR) < 3:
    log.debug('ERROR!!! saving keys to / : <<<%s>>>' % HOME_DIR)
    log.debug('os.environ:')
    log.debug(os.environ)

PRIVATE_KEY_FILE = os.path.join(HOME_DIR, '.ssh', 'id_rsa')
PUBLIC_KEY_FILE =  os.path.join(HOME_DIR, '.ssh', 'id_rsa.pub')


def get_or_create_public_key():
    if not os.path.exists(PRIVATE_KEY_FILE) or not os.path.exists(PUBLIC_KEY_FILE):
        write_new_key(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)

    return open(PUBLIC_KEY_FILE, 'r').readline()


def write_new_key(private_key_filename, public_key_filename):
#	print 'writing keys: %s %s' %( private_key_filename, public_key_filename)
    key = paramiko.RSAKey.generate(1024)
    if not os.path.exists(os.path.dirname(private_key_filename)):
        os.makedirs(os.path.dirname(private_key_filename), 0700)

    log.info('creating private key file: %s' % private_key_filename)
    key.write_private_key_file(private_key_filename)

    pk = paramiko.RSAKey(filename=private_key_filename)
    if not os.path.exists(os.path.dirname(public_key_filename)):
        os.makedirs(os.path.dirname(public_key_filename), 0700)
    import getpass
    username = getpass.getuser()
    log.info('creating public key file: %s' % public_key_filename)
    o = open(public_key_filename ,'w').write("ssh-rsa %s %s \n" % (pk.get_base64(), username))


def create_new_key_pair():
    key = paramiko.RSAKey.generate(1024)

    private_key = StringIO.StringIO()
    key.write_private_key(private_key)
    private_key.seek(0)

    pk = paramiko.RSAKey(file_obj=private_key)
    import getpass
    username = getpass.getuser()
    public_key = "ssh-rsa %s %s \n" % (pk.get_base64(), username)

    return private_key.getvalue(), public_key

