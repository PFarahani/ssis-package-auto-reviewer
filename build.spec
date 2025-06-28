# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/favicon.ico', 'resources'),
        ('config/property_rules.yml', 'config')
    ],
    hiddenimports=['tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    includes=['tkinter', 'PyYAML', 'lxml'],
    excludes=['pip', 'setuptools', 'wheel', 'distutils', 'email', 'http', 
              'tkinter.test', 'sqlite3', 'unittest', 'altgraph', 'packaging', 
              'pefile', 'pyinstaller', 'pyinstaller-hooks-contrib', 'pywin32-ctypes'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PackageAutoReviewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/favicon.ico',
)