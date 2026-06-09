# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os

spec_dir = os.path.dirname(os.path.abspath(SPEC))
root_dir = os.path.abspath(os.path.join(spec_dir, ".."))

a = Analysis(
    [os.path.join(root_dir, 'localdog', '__main__.py')],
    pathex=[root_dir],
    binaries=[],
    datas=[
        (os.path.join(root_dir, 'localdog', 'ui'), 'localdog/ui'),
        (os.path.join(root_dir, 'localdog', 'proxy'), 'localdog/proxy'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LocalDog',
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
    icon=os.path.join(root_dir, 'localdog', 'ui', 'icon.ico'),
)
