# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Speech Bubble Editor v3.
Supports Linux, Windows and macOS from a single spec file.

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

if _sys.platform == 'darwin':
    # ── macOS — directory-bundle EXE + COLLECT + BUNDLE (.app) ──────────────
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
        target_arch=None,
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
        name='SpeechBubbleEditor',
    )
    app = BUNDLE(
        coll,
        name='Speech Bubble Editor.app',
        icon=os.path.join(_app_dir, 'icons', 'icon.icns'),
        bundle_identifier='com.longweekendlabs.speechbubbleeditor',
        info_plist={
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,   # support dark mode
            'LSMinimumSystemVersion': '12.0',
            'CFBundleShortVersionString': '3.0.0',
            'CFBundleName': 'Speech Bubble Editor',
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
        },
    )

else:
    # ── Linux / Windows — single-file binary ────────────────────────────────
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
