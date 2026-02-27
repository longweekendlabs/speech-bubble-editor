# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Speech Bubble Editor v2.
Build with:  pyinstaller speech_bubble_v2.spec
"""

import os

_app_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[_app_dir],
    binaries=[],
    datas=[
        (os.path.join(_app_dir, 'fonts'), 'fonts'),
        (os.path.join(_app_dir, 'icons'), 'icons'),
    ],
    hiddenimports=[
        'cv2',
        'numpy',
        'PIL',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SpeechBubbleEditor',
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
    icon=os.path.join(_app_dir, 'icons', 'icon.ico'),
)
