#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="SpeechBubbleEditor"
VERSION="$(python -c 'import version; print(version.__version__)')"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64|amd64) PLATFORM="linux-x64" ;;
  aarch64|arm64) PLATFORM="linux-arm64" ;;
  *) PLATFORM="linux-${ARCH}" ;;
esac

OUT_DIR="linux"
VENV_DIR=".build_venv"

echo "=== Speech Bubble Editor v${VERSION} -- ${PLATFORM} Build ==="

if [ -d "$VENV_DIR" ] && ! "$VENV_DIR/bin/python" -c 'import sys' >/dev/null 2>&1; then
  echo "Removing invalid ${VENV_DIR}"
  rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python create_icon.py
python -m PyInstaller --clean --noconfirm speech_bubble_v3.spec

mkdir -p "$OUT_DIR"
tar -czf "${OUT_DIR}/${APP_NAME}-v${VERSION}-${PLATFORM}.tar.gz" -C dist "$APP_NAME"

echo "OK: ${OUT_DIR}/${APP_NAME}-v${VERSION}-${PLATFORM}.tar.gz"
