# -*- mode: python -*-

block_cipher = None


a = Analysis(['apps/openport_app.py'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             cipher=block_cipher,
             excludes=None,
            )
pyz = PYZ(a.pure,
             cipher=block_cipher)

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
