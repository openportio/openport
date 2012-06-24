import os
import paramiko

HOME_DIR = os.path.expanduser('~')
PRIVATE_KEYFILE = os.path.join(HOME_DIR, '.ssh', 'id_rsa')
PUBLIC_KEYFILE =  os.path.join(HOME_DIR, '.ssh', 'id_rsa.pub')

def get_or_create_public_key():
    if not os.path.exists(PRIVATE_KEYFILE) or not os.path.exists(PUBLIC_KEYFILE):
        write_new_key(PRIVATE_KEYFILE, PUBLIC_KEYFILE)

    return open(PUBLIC_KEYFILE, 'r').readline()

def write_new_key(private_key_filename, public_key_filename):
#	print 'writing keys: %s %s' %( private_key_filename, public_key_filename)
    key = paramiko.RSAKey.generate(1024)
    if not os.path.exists( os.path.dirname(private_key_filename) ):
        os.makedirs( os.path.dirname(private_key_filename), 0700)
    key.write_private_key_file(private_key_filename)

    pk = paramiko.RSAKey(filename=private_key_filename)
    if not os.path.exists( os.path.dirname(public_key_filename) ):
        os.makedirs( os.path.dirname(public_key_filename), 0700)
    o = open(public_key_filename ,'w').write("ssh-rsa " +pk.get_base64()+ " \n")

