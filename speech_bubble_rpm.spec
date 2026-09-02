# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Linux RPM build — ONEDIR layout.

Same analysis as speech_bubble.spec but produces a directory bundle
(dist/SpeechBubbleEditor/ with an _internal/ folder) instead of a single
self-extracting binary. Onedir is what the RPM installs to /opt so the app
starts instantly instead of re-extracting ~400 MB to /tmp on every launch.

Build:
    pyinstaller --clean --noconfirm speech_bubble_rpm.spec
"""

import os
import shutil as _shutil

_app_dir = os.path.dirname(os.path.abspath(SPEC))

from PyInstaller.utils.hooks import collect_all as _collect_all
_qt_datas, _qt_binaries, _qt_hidden = _collect_all('PyQt6')

_ffmpeg_bin = _shutil.which('ffmpeg')
_extra_binaries = [(_ffmpeg_bin, '.')] if _ffmpeg_bin else []

_hidden = [
    'cv2',
    'numpy',
    'PIL',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'PyQt6.sip',
] + _qt_hidden

a = Analysis(
    ['main.py'],
    pathex=[_app_dir],
    binaries=_qt_binaries + _extra_binaries,
    datas=[
        (os.path.join(_app_dir, 'fonts'), 'fonts'),
        (os.path.join(_app_dir, 'icons'), 'icons'),
        (os.path.join(_app_dir, 'theme'), 'theme'),
    ] + _qt_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

_icon = os.path.join(_app_dir, 'icons', 'icon.png')

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SpeechBubbleEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SpeechBubbleEditor',
)
