# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Speech Bubble Editor — macOS arm64 (.app bundle).

Build:
    pyinstaller --clean --noconfirm speech_bubble_macos.spec

Requires icons/icon.icns — generate it first (CI does this via iconutil).
"""

import os
import importlib.util as _ilu

_app_dir = os.path.dirname(os.path.abspath(SPEC))

# Read version from version.py without importing it (avoids Qt at spec time).
_vs = _ilu.spec_from_file_location("version", os.path.join(_app_dir, "version.py"))
_vm = _ilu.module_from_spec(_vs)
_vs.loader.exec_module(_vm)
_VERSION = _vm.__version__

from PyInstaller.utils.hooks import collect_all as _collect_all
import shutil as _shutil
_qt_datas, _qt_binaries, _qt_hidden = _collect_all('PyQt6')

# Bundle FFmpeg if present on PATH (Homebrew on local builds; pre-installed on CI).
# export.py checks sys._MEIPASS/ffmpeg first so the bundled copy is always used.
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
        (os.path.join(_app_dir, 'fonts'),  'fonts'),
        (os.path.join(_app_dir, 'icons'),  'icons'),
        (os.path.join(_app_dir, 'theme'),  'theme'),
    ] + _qt_datas,
    hiddenimports=_hidden,
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
    [],
    exclude_binaries=True,
    name='SpeechBubbleEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(_app_dir, 'icons', 'icon.icns'),
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

app = BUNDLE(
    coll,
    name='SpeechBubbleEditor.app',
    icon=os.path.join(_app_dir, 'icons', 'icon.icns'),
    bundle_identifier='com.longweekendlabs.speechbubbleeditor',
    info_plist={
        'CFBundleName':             'Speech Bubble Editor',
        'CFBundleDisplayName':      'Speech Bubble Editor',
        'CFBundleShortVersionString': _VERSION,
        'CFBundleVersion':          _VERSION,
        'NSHighResolutionCapable':  True,
        'NSPrincipalClass':         'NSApplication',
        'NSAppleScriptEnabled':     False,
        'LSMinimumSystemVersion':   '12.0',
        'CFBundleDocumentTypes':    [],
    },
)
