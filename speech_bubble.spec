# -*- mode: python ; coding: utf-8 -*-
"""Self-contained directory bundle for Windows, Linux, and macOS.

Installers/archive formats compress this directory for distribution. The app
runs in place: it must never unpack its runtime on each launch.
"""
import os
import shutil
import runpy
import sys
from importlib.metadata import PackageNotFoundError, version

try:
    version('opencv-python')
except PackageNotFoundError:
    pass
else:
    raise RuntimeError('Uninstall opencv-python, then reinstall requirements.txt; '
                       'only opencv-python-headless should provide cv2')

_app_dir = os.path.dirname(os.path.abspath(SPEC))
# Use the real executable, not a package-manager shim (Windows CI supplies it).
_ffmpeg_bin = os.environ.get('SBE_FFMPEG') or shutil.which('ffmpeg')
if not _ffmpeg_bin or not os.path.isfile(_ffmpeg_bin):
    raise RuntimeError('FFmpeg is required for packaged video/audio export')

# PyInstaller's module-specific Qt hooks include the platform, image-format
# and SVG plugins. collect_all('PyQt6') also pulls in QML/Quick, Designer,
# Multimedia, PDF, SQL, developer tools, etc. that this app never uses.
a = Analysis(
    [os.path.join(_app_dir, 'main.py')],
    pathex=[_app_dir],
    binaries=[(_ffmpeg_bin, '.')],
    datas=[(os.path.join(_app_dir, name), name)
           for name in ('fonts', 'icons', 'theme')],
    hiddenimports=[],
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
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(_app_dir, 'icons',
                      'icon.ico' if sys.platform == 'win32' else 'icon.png'),
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=False,
    name='SpeechBubbleEditor',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Speech Bubble Editor.app',
        icon=os.path.join(_app_dir, 'icons', 'icon.icns'),
        bundle_identifier='com.longweekendlabs.speechbubbleeditor',
        version=runpy.run_path(os.path.join(_app_dir, 'version.py'))['__version__'],
        info_plist={
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '15.0',
            'NSHumanReadableCopyright': 'Copyright © 2026 Long Weekend Labs',
        },
    )
