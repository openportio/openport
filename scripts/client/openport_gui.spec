# -*- mode: python -*-

block_cipher = None


a = Analysis(['gui/shares_frame.py'],
             pathex=['/Users/jan/swprojects/openport-client/scripts/client'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries + [('msvcp100.dll', 'C:\\Windows\\System32\\msvcp100.dll', 'BINARY'),
                        ('msvcr100.dll', 'C:\\Windows\\System32\\msvcr100.dll', 'BINARY')]
          if sys.platform == 'win32' else a.binaries,
          a.zipfiles,
          a.datas + [('resources/icon.icns', 'resources/icon.icns', 'DATA'),
                    ],
          name=os.path.join('dist', 'Openport_GUI' + ('.exe' if sys.platform == 'win32' else '')),
          debug=False,
          strip=None,
          upx=True,
          console=False,
          icon='resources/icon.icns')

# Build a .app if on OS X
if sys.platform == 'darwin':
   app = BUNDLE(exe,
                name='Openport.app',
                icon='resources/icon.icns')
