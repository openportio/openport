# -*- mode: python -*-

block_cipher = None



def get_crypto_path():
    '''Auto import sometimes fails on linux'''
    import Crypto
    crypto_path = Crypto.__path__[0]
    return crypto_path


a = Analysis(['apps/openport_app.py'],
             pathex=['.'],
             hiddenimports=['cffi', 'cryptography'],
             hookspath=None,
             runtime_hooks=None,
             cipher=block_cipher,
             excludes=None,
            )
pyz = PYZ(a.pure,
             cipher=block_cipher)

dict_tree = Tree(get_crypto_path(), prefix='Crypto', excludes=["*.pyc"])
a.datas += dict_tree

print a.datas

a.binaries = filter(lambda x: 'Crypto' not in x[0], a.binaries)
			 
from os import listdir
from os.path import isfile, join
import os

migration_script_folder = 'alembic/versions'
for f in listdir(migration_script_folder):
    path = join(migration_script_folder, f)
    if isfile(path):
        a.datas += [(path, path, 'DATA')]


exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='openport' + ('.exe' if sys.platform == 'win32' else ''),
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='openport')
