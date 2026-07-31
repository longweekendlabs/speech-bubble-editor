#!/usr/bin/env bash
# Build a local RPM (Fedora) from the current working tree.
#
# Produces linux/speech-bubble-editor-<version>-1.<dist>.<arch>.rpm using the
# PyInstaller ONEDIR bundle, installed to /opt so the app starts instantly
# rather than re-extracting a ~300 MB archive on every launch.
#
#   ./build_rpm.sh
#
# Requires: rpmbuild, python3. Everything else is installed into .build_venv.
set -euo pipefail
cd "$(dirname "$0")"

APP_ID="speech-bubble-editor"
BUNDLE="SpeechBubbleEditor"
VERSION="$(python3 -c 'import version; print(version.__version__)')"
ARCH="$(uname -m)"
OUT_DIR="linux"
VENV_DIR=".build_venv"
TOP="$(pwd)/.rpmbuild"

echo "=== ${BUNDLE} v${VERSION} — RPM (${ARCH}) ==="

# --- 1. build the PyInstaller onedir bundle -------------------------------
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

python create_icon.py
python -m PyInstaller --clean --noconfirm speech_bubble_rpm.spec
deactivate

[ -d "dist/${BUNDLE}" ] || { echo "PyInstaller produced no dist/${BUNDLE}"; exit 1; }

# --- 2. lay out the install tree ------------------------------------------
rm -rf "$TOP"
mkdir -p "$TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
STAGE="$TOP/stage"
mkdir -p "$STAGE/opt/${APP_ID}" \
         "$STAGE/usr/bin" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/256x256/apps"

cp -a "dist/${BUNDLE}/." "$STAGE/opt/${APP_ID}/"
cp icons/icon.png "$STAGE/usr/share/icons/hicolor/256x256/apps/${APP_ID}.png"

cat > "$STAGE/usr/bin/${APP_ID}" <<EOF
#!/bin/sh
exec /opt/${APP_ID}/${BUNDLE} "\$@"
EOF
chmod 755 "$STAGE/usr/bin/${APP_ID}"

cat > "$STAGE/usr/share/applications/${APP_ID}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Speech Bubble Editor
Comment=Add comic speech bubbles and captions to photos and video
Exec=${APP_ID} %f
Icon=${APP_ID}
Terminal=false
Categories=Graphics;Photography;
MimeType=image/jpeg;image/png;image/webp;video/mp4;video/quicktime;
EOF

# --- 3. spec + build ------------------------------------------------------
cat > "$TOP/SPECS/${APP_ID}.spec" <<EOF
%global __os_install_post %{nil}
%global debug_package %{nil}
# The bundle ships its own Qt/OpenCV .so files; skip the usual mangling and
# auto-dependency scan, which would otherwise demand system Qt packages.
AutoReqProv: no

Name:           ${APP_ID}
Version:        ${VERSION}
Release:        1%{?dist}
Summary:        Add comic speech bubbles and captions to photos and video
License:        MIT
URL:            https://github.com/longweekendlabs/speech-bubble-editor
BuildArch:      ${ARCH}

%description
Speech Bubble Editor places hand-inked comic and manga speech balloons,
captions, speed lines and redactions onto photos and video, and exports
them at full resolution.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -a ${STAGE}/. %{buildroot}/

%files
/opt/${APP_ID}
/usr/bin/${APP_ID}
/usr/share/applications/${APP_ID}.desktop
/usr/share/icons/hicolor/256x256/apps/${APP_ID}.png

%post
/usr/bin/update-desktop-database &>/dev/null || :
/bin/touch --no-create /usr/share/icons/hicolor &>/dev/null || :

%postun
/usr/bin/update-desktop-database &>/dev/null || :
/usr/bin/gtk-update-icon-cache /usr/share/icons/hicolor &>/dev/null || :
EOF

rpmbuild --define "_topdir ${TOP}" -bb "$TOP/SPECS/${APP_ID}.spec"

mkdir -p "$OUT_DIR"
RPM_PATH="$(find "$TOP/RPMS" -name '*.rpm' | head -1)"
cp "$RPM_PATH" "$OUT_DIR/"
rm -rf "$TOP"

echo
echo "OK: ${OUT_DIR}/$(basename "$RPM_PATH")"
echo "Install with:  sudo dnf install ./${OUT_DIR}/$(basename "$RPM_PATH")"
