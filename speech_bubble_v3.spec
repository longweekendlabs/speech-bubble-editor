# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Speech Bubble Editor v3.1.
Supports Linux (x86_64, aarch64) and Windows (x64, ARM64).
macOS support was removed in v3.1.

Build:
    pyinstaller --clean --noconfirm speech_bubble_v3.spec
"""

import os
import sys as _sys

_app_dir = os.path.dirname(os.path.abspath(SPEC))

# Collect ALL PyQt6 submodules + data + binaries so Qt platform plugins
# (libqcocoa.dylib on macOS, qwindows.dll on Windows) are never missing.
from PyInstaller.utils.hooks import collect_all as _collect_all
_qt_datas, _qt_binaries, _qt_hidden = _collect_all('PyQt6')

_hidden = [
    'cv2',
    'numpy',
    'PIL',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',   # QLocalServer / QLocalSocket for single-instance guard
    'PyQt6.sip',
] + _qt_hidden

a = Analysis(
    ['main.py'],
    pathex=[_app_dir],
    binaries=_qt_binaries,
    datas=[
        (os.path.join(_app_dir, 'fonts'), 'fonts'),
        (os.path.join(_app_dir, 'icons'), 'icons'),
    ] + _qt_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ── Linux / Windows — single-file binary ────────────────────────────────────
# UPX disabled for cross-arch compatibility (ARM64 Windows / Linux aarch64).
_icon = os.path.join(_app_dir, 'icons', 'icon.ico') if _sys.platform == 'win32' \
        else os.path.join(_app_dir, 'icons', 'icon.png')

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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
