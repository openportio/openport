# -*- mode: python -*-

block_cipher = None


a = Analysis(['openport/gui/openport_gui.py'],
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

migration_script_folder = 'openport/alembic/versions'
for f in listdir(migration_script_folder):
    path = join(migration_script_folder, f)
    if isfile(path):
        a.datas += [(path[9:], path, 'DATA')]

a.datas += [
            ('resources/icon.icns', 'openport/resources/icon.icns', 'DATA'),
            ('resources/icon.ico',  'openport/resources/icon.ico', 'DATA'),
           ]


exe = EXE(pyz,
          a.scripts,
          a.binaries + [('msvcp100.dll', 'C:\\Windows\\System32\\msvcp100.dll', 'BINARY'),
                        ('msvcr100.dll', 'C:\\Windows\\System32\\msvcr100.dll', 'BINARY')]
          if sys.platform == 'win32' else a.binaries,
          a.zipfiles,
          a.datas,
          name='openport-gui' + ('.exe' if sys.platform == 'win32' else ''),
          debug=False,
          strip=None,
          upx=True,
          console=False,
          icon='resources/icon.ico')


# Build a .app if on OS X
if sys.platform == 'darwin':
   app = BUNDLE(exe,
                name='Openport.app',
                icon='resources/icon.icns')
