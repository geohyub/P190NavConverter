# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for P190 NavConverter."""

import sys
from pathlib import Path

block_cipher = None

# CustomTkinter data files
import customtkinter
ctk_path = Path(customtkinter.__file__).parent

a = Analysis(
    ['p190converter/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(ctk_path), 'customtkinter/'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',
        'pyproj',
        'pyproj.database',
        'pyproj._crs',
        'pyproj._transformer',
        'scipy.interpolate',
        'matplotlib.backends.backend_tkagg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'IPython', 'jupyter', 'notebook',
        'sphinx', 'pytest', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='P190_NavConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # GUI application, no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='P190_NavConverter',
)
