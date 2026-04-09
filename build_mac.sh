#!/bin/bash
# build_mac.sh — Build Speech Bubble Editor for macOS
set -e
cd "$(dirname "$0")"
source venv/bin/activate
pip install --upgrade pyinstaller
pyinstaller \
  --name "Speech Bubble Editor" \
  --windowed \
  --icon icons/icon.icns \
  --add-data "fonts:fonts" \
  --add-data "icons:icons" \
  --hidden-import "cv2" \
  --hidden-import "numpy" \
  main.py
echo "Build complete: dist/Speech Bubble Editor.app"
