#!/usr/bin/env bash
# Package a verified app without copying Finder/Dropbox extended attributes.
set -euo pipefail
APP_PATH="${1:?Usage: package_macos.sh path/to/app output-directory}"
OUTPUT_PATH="${2:?Output directory required}"
VERSION="$(python3 -c 'import version; print(version.__version__)')"
mkdir -p "$OUTPUT_PATH"
STAGE_PATH="$(mktemp -d "${TMPDIR:-/tmp}/sbe-dmg.XXXXXX")"
trap 'rm -rf "$STAGE_PATH"' EXIT
ditto --norsrc --noextattr "$APP_PATH" "$STAGE_PATH/Speech Bubble Editor.app"
codesign --verify --deep --strict "$STAGE_PATH/Speech Bubble Editor.app"
ln -s /Applications "$STAGE_PATH/Applications"
DMG_PATH="$OUTPUT_PATH/SpeechBubbleEditor-v${VERSION}-macos-arm64.dmg"
hdiutil create -volname "Speech Bubble Editor" -srcfolder "$STAGE_PATH" \
  -ov -format UDZO "$DMG_PATH"
hdiutil verify "$DMG_PATH"
