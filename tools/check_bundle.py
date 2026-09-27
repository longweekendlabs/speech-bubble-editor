"""Audit a frozen directory bundle before installers/archive files are made."""
import json
from pathlib import Path
import subprocess
import sys


def audit(root):
    root = Path(root)
    files = [p for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
    if not files:
        raise RuntimeError(f'No directory bundle at {root}')
    is_app = root.suffix == '.app'
    internal = root / ('Contents/Frameworks' if is_app else '_internal')
    exe = 'SpeechBubbleEditor.exe' if sys.platform == 'win32' else 'SpeechBubbleEditor'
    ffmpeg = internal / ('ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
    executable = root / 'Contents/MacOS' / exe if is_app else root / exe
    for path in (executable, ffmpeg, internal / 'theme/dark.qss',
                 internal / 'fonts/ComicNeue-BoldItalic.ttf', internal / 'icons/icon.png'):
        if not path.is_file():
            raise RuntimeError(f'Missing runtime resource: {path}')
    qt = internal / 'PyQt6'
    for plugin in ('platforms', 'imageformats'):
        if not any(p.is_file() for directory in qt.rglob(plugin)
                   for p in directory.iterdir()):
            raise RuntimeError(f'Missing Qt {plugin} plugins')
    unwanted = ('QtQml', 'QtQuick', 'Qt6Qml', 'Qt6Quick', 'QtWebEngine',
                'Qt6WebEngine', 'QtDesigner', 'Qt6Designer', 'QtMultimedia',
                'Qt6Multimedia')
    excess = [str(p.relative_to(root)) for p in files
              if any(name in p.name for name in unwanted)]
    if excess:
        raise RuntimeError(f'Unused Qt components bundled: {excess}')
    # This also catches accidentally packaging a Chocolatey launcher shim.
    subprocess.run([str(ffmpeg.resolve()), '-version'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
    total = sum(p.stat().st_size for p in files)
    result = {
        'bundle_mib': round(total / 1024**2, 2),
        'files': len(files),
        'largest': [{'path': str(p.relative_to(root)),
                     'mib': round(p.stat().st_size / 1024**2, 2)}
                    for p in sorted(files, key=lambda p: p.stat().st_size,
                                    reverse=True)[:15]],
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    audit(sys.argv[1])
