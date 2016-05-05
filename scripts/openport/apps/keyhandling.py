import os
import paramiko
import StringIO
import shutil
from openport.services.logger_service import get_logger
from openport.services import osinteraction

log = get_logger(__name__)


def get_default_key_locations():
    app_data_path = osinteraction.getInstance().get_app_data_path()
    log.debug('app_data_path: %s' % app_data_path)
    private_key_file = os.path.join(app_data_path, 'id_rsa')
    public_key_file = os.path.join(app_data_path, 'id_rsa.pub')

    return public_key_file, private_key_file


def get_or_create_public_key():
    public_key_file, private_key_file = get_default_key_locations()
    ensure_keys_exist(public_key_file, private_key_file)
    return open(public_key_file, 'r').readline()


def ensure_keys_exist(public_key_file, private_key_file):
    if not os.path.exists(private_key_file) or not os.path.exists(public_key_file):
        system_id_rsa = os.path.expanduser('{}/.ssh/id_rsa'.format(os.environ.get('HOME', '/root')))
        system_id_rsa_pub = os.path.expanduser('{}/.ssh/id_rsa.pub'.format(os.environ.get('HOME', '/root')))
        if os.path.exists(system_id_rsa) and os.path.exists(system_id_rsa_pub):
            try:
                paramiko.RSAKey.from_private_key_file(system_id_rsa)
            except paramiko.PasswordRequiredException:
                write_new_key(private_key_file, public_key_file)
            else:
                shutil.copy(system_id_rsa, private_key_file)
                shutil.copy(system_id_rsa_pub, public_key_file)
        else:
            write_new_key(private_key_file, public_key_file)


def write_new_key(private_key_filename, public_key_filename):
#	print 'writing keys: %s %s' %( private_key_filename, public_key_filename)
    key = paramiko.RSAKey.generate(1024)
    if not os.path.exists(os.path.dirname(private_key_filename)):
        os.makedirs(os.path.dirname(private_key_filename), 0o700)

    log.info('creating private key file: %s' % private_key_filename)
    key.write_private_key_file(private_key_filename)

    pk = paramiko.RSAKey(filename=private_key_filename)
    if not os.path.exists(os.path.dirname(public_key_filename)):
        os.makedirs(os.path.dirname(public_key_filename), 0o700)
    import getpass
    username = getpass.getuser()
    log.info('creating public key file: %s' % public_key_filename)
    open(public_key_filename, 'w', 0o644).write("ssh-rsa %s %s \n" % (pk.get_base64(), username))


def create_new_key_pair(length=1024):
    key = paramiko.RSAKey.generate(length)

    private_key = StringIO.StringIO()
    key.write_private_key(private_key)
    private_key.seek(0)

    pk = paramiko.RSAKey(file_obj=private_key)
    import getpass
    username = getpass.getuser()
    public_key = "ssh-rsa %s %s \n" % (pk.get_base64(), username)

    return private_key.getvalue(), public_key

