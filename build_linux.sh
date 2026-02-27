#!/usr/bin/env bash
# build_linux.sh — Build Speech Bubble Editor v2 for Linux
#
# Outputs to: lin/
#   SpeechBubbleEditor-<VER>-x86_64.AppImage   ← universal (any distro, just double-click)
#   speech-bubble-editor-<VER>.x86_64.rpm      ← Fedora / RHEL / openSUSE
#   speech-bubble-editor_<VER>_amd64.deb       ← Ubuntu / Mint / Debian
#   SpeechBubbleEditor-<VER>-linux.tar.gz      ← plain archive fallback
#
# Requirements (auto-installed if missing):
#   pyinstaller  — bundled in the venv via requirements.txt
#   rpmbuild     — sudo dnf install rpm-build
#   alien        — sudo dnf install alien   (RPM→DEB converter)
#   appimagetool — downloaded automatically the first time

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Config ─────────────────────────────────────────────────────────────────
APP_NAME="SpeechBubbleEditor"
PKG_NAME="speech-bubble-editor"
VERSION="2.1.10"
ARCH="x86_64"
LIN_DIR="$(pwd)/lin"
DIST_DIR="$(pwd)/dist"
TOOLS_DIR="$(pwd)/.build_tools"

echo "=== Speech Bubble Editor v${VERSION} — Linux Build ==="
mkdir -p "$LIN_DIR" "$TOOLS_DIR"

# ── 1. Virtual environment + PyInstaller ───────────────────────────────────
echo ""
echo "[1/5] Building binary with PyInstaller..."
if [ ! -d ".build_venv" ]; then
    python3 -m venv .build_venv
fi
source .build_venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python create_icon.py
python -m PyInstaller --clean --noconfirm speech_bubble_v2.spec
deactivate
rm -rf .build_venv

BINARY="${DIST_DIR}/${APP_NAME}"
if [ ! -f "$BINARY" ]; then
    echo "ERROR: PyInstaller did not produce ${BINARY}" >&2
    exit 1
fi
echo "  ✓ Binary: dist/${APP_NAME}"

# ── 2. tar.gz ──────────────────────────────────────────────────────────────
echo ""
echo "[2/5] Creating tar.gz..."
tar -czf "${LIN_DIR}/${APP_NAME}-${VERSION}-linux.tar.gz" \
    -C "$DIST_DIR" "$APP_NAME"
echo "  ✓ ${APP_NAME}-${VERSION}-linux.tar.gz"

# ── 3. AppImage ────────────────────────────────────────────────────────────
echo ""
echo "[3/5] Creating AppImage..."

APPDIR="${DIST_DIR}/${APP_NAME}.AppDir"
rm -rf "$APPDIR"
mkdir -p "${APPDIR}/usr/bin"

# Copy binary
cp "$BINARY" "${APPDIR}/usr/bin/${APP_NAME}"
chmod +x "${APPDIR}/usr/bin/${APP_NAME}"

# Desktop entry (required by AppImage spec)
cat > "${APPDIR}/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Name=Speech Bubble Editor
Exec=${APP_NAME}
Icon=icon
Type=Application
Categories=Graphics;Photography;
EOF

# Icon (AppImage spec: icon in root named icon.png)
cp "icons/icon.png" "${APPDIR}/icon.png"

# AppRun launcher
cat > "${APPDIR}/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/usr/bin/SpeechBubbleEditor" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

# Download appimagetool if not present
APPIMAGETOOL="${TOOLS_DIR}/appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "  Downloading appimagetool (one-time)..."
    curl -sL \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
        -o "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
fi

APPIMAGE_OUT="${LIN_DIR}/${APP_NAME}-${VERSION}-x86_64.AppImage"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_OUT" 2>/dev/null \
    || ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$APPDIR" "$APPIMAGE_OUT"
chmod +x "$APPIMAGE_OUT"
echo "  ✓ ${APP_NAME}-${VERSION}-x86_64.AppImage"

# ── 4. RPM ─────────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Creating RPM..."

if ! command -v rpmbuild &>/dev/null; then
    echo "  ⚠ rpmbuild not found — skipping RPM"
    echo "    Install with: sudo dnf install rpm-build"
else
    RPM_BUILD="${HOME}/rpmbuild"
    mkdir -p "${RPM_BUILD}"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

    # Stage files to a known absolute path; pass it to spec via --define
    RPM_STAGE="${DIST_DIR}/_rpm_stage"
    rm -rf "$RPM_STAGE"
    mkdir -p "${RPM_STAGE}/usr/local/bin"
    mkdir -p "${RPM_STAGE}/usr/share/applications"
    mkdir -p "${RPM_STAGE}/usr/share/pixmaps"

    cp "$BINARY" "${RPM_STAGE}/usr/local/bin/${APP_NAME}"

    cat > "${RPM_STAGE}/usr/share/applications/${PKG_NAME}.desktop" << EOF
[Desktop Entry]
Version=1.0
Name=Speech Bubble Editor
Comment=Annotate photos and videos with speech bubbles
Exec=/usr/local/bin/${APP_NAME}
Icon=${PKG_NAME}
Terminal=false
Type=Application
Categories=Graphics;Photography;
EOF

    cp "icons/icon.png" "${RPM_STAGE}/usr/share/pixmaps/${PKG_NAME}.png"

    # Write spec — references %{_app_src} macro passed via --define
    RPM_SPEC="${RPM_BUILD}/SPECS/${PKG_NAME}.spec"
    {
        echo "Name:           ${PKG_NAME}"
        echo "Version:        ${VERSION}"
        echo "Release:        1%{?dist}"
        echo "Summary:        Speech Bubble Editor — annotate photos and videos"
        echo "License:        Proprietary"
        echo "BuildArch:      x86_64"
        echo ""
        echo "%description"
        echo "Speech Bubble Editor v2 — add speech bubbles to photos and videos."
        echo "Supports trim, cut, reverse, dual-media mode, and meme mode."
        echo "Developed by Long Weekend Labs."
        echo ""
        echo "%install"
        echo "mkdir -p %{buildroot}/usr/local/bin"
        echo "mkdir -p %{buildroot}/usr/share/applications"
        echo "mkdir -p %{buildroot}/usr/share/pixmaps"
        echo "cp %{_app_src}/usr/local/bin/${APP_NAME} %{buildroot}/usr/local/bin/"
        echo "cp %{_app_src}/usr/share/applications/${PKG_NAME}.desktop %{buildroot}/usr/share/applications/"
        echo "cp %{_app_src}/usr/share/pixmaps/${PKG_NAME}.png %{buildroot}/usr/share/pixmaps/"
        echo ""
        echo "%files"
        echo "/usr/local/bin/${APP_NAME}"
        echo "/usr/share/applications/${PKG_NAME}.desktop"
        echo "/usr/share/pixmaps/${PKG_NAME}.png"
        echo ""
        echo "%changelog"
        echo "* $(date '+%a %b %d %Y') Long Weekend Labs <longweekendlabs@users.noreply.github.com> - ${VERSION}-1"
        echo "- Release v${VERSION}"
    } > "$RPM_SPEC"

    # RPM macros don't quote — use a space-free symlink if the path has spaces
    STAGE_LINK="/tmp/sbg_rpm_stage_$$"
    rm -f "$STAGE_LINK"
    ln -s "$RPM_STAGE" "$STAGE_LINK"

    rpmbuild -bb \
        --define "_app_src ${STAGE_LINK}" \
        --define "__strip /bin/true" \
        "$RPM_SPEC" 2>&1 | grep -E "^(Wrote|error|warning:)" || true

    rm -f "$STAGE_LINK"

    RPM_FILE=$(find "${RPM_BUILD}/RPMS" -name "${PKG_NAME}-${VERSION}*.rpm" 2>/dev/null | head -1)
    if [ -n "$RPM_FILE" ]; then
        cp "$RPM_FILE" "$LIN_DIR/"
        echo "  ✓ $(basename "$RPM_FILE")"
    else
        echo "  ⚠ RPM build produced no output — check ~/rpmbuild/BUILD/ for logs"
    fi
fi

# ── 5. DEB ─────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Creating DEB..."

DEB_OUT="${LIN_DIR}/${PKG_NAME}_${VERSION}_amd64.deb"

if command -v dpkg-deb &>/dev/null; then
    # Build DEB from scratch
    DEBDIR="${DIST_DIR}/deb/${PKG_NAME}_${VERSION}_amd64"
    rm -rf "$DEBDIR"
    mkdir -p "${DEBDIR}/DEBIAN"
    mkdir -p "${DEBDIR}/usr/local/bin"
    mkdir -p "${DEBDIR}/usr/share/applications"
    mkdir -p "${DEBDIR}/usr/share/pixmaps"

    cp "$BINARY" "${DEBDIR}/usr/local/bin/${APP_NAME}"
    chmod +x "${DEBDIR}/usr/local/bin/${APP_NAME}"

    cat > "${DEBDIR}/usr/share/applications/${PKG_NAME}.desktop" << EOF
[Desktop Entry]
Version=1.0
Name=Speech Bubble Editor
Comment=Annotate photos and videos with speech bubbles
Exec=/usr/local/bin/${APP_NAME}
Icon=${PKG_NAME}
Terminal=false
Type=Application
Categories=Graphics;Photography;
EOF

    cp "$(pwd)/icons/icon.png" "${DEBDIR}/usr/share/pixmaps/${PKG_NAME}.png"

    {
        echo "Package: ${PKG_NAME}"
        echo "Version: ${VERSION}"
        echo "Architecture: amd64"
        echo "Maintainer: Long Weekend Labs <longweekendlabs@users.noreply.github.com>"
        echo "Description: Speech Bubble Editor"
        echo " Annotate photos and videos with speech bubbles."
        echo " Supports trim, cut, reverse, dual-media mode, and meme mode."
    } > "${DEBDIR}/DEBIAN/control"

    dpkg-deb --build "$DEBDIR" "$DEB_OUT"
    echo "  ✓ $(basename "$DEB_OUT")"

elif command -v alien &>/dev/null; then
    RPM_FILE=$(find "$LIN_DIR" -name "${PKG_NAME}-${VERSION}*.rpm" | head -1)
    if [ -n "$RPM_FILE" ]; then
        echo "  Converting RPM → DEB via alien..."
        pushd "$LIN_DIR" > /dev/null
        alien --to-deb "$(basename "$RPM_FILE")" 2>/dev/null
        popd > /dev/null
        echo "  ✓ DEB created via alien"
    else
        echo "  ⚠ No RPM found to convert — skipping DEB"
    fi

elif command -v ar &>/dev/null; then
    # Build .deb manually using the ar/tar archive format
    # A .deb is: ar archive of (debian-binary, control.tar.gz, data.tar.gz)
    DEB_TMP="${DIST_DIR}/_deb_build"
    rm -rf "$DEB_TMP"
    mkdir -p "$DEB_TMP"
    pushd "$DEB_TMP" > /dev/null

    echo "2.0" > debian-binary

    mkdir control_dir
    {
        echo "Package: ${PKG_NAME}"
        echo "Version: ${VERSION}"
        echo "Architecture: amd64"
        echo "Maintainer: Long Weekend Labs <longweekendlabs@users.noreply.github.com>"
        echo "Description: Speech Bubble Editor"
        echo " Annotate photos and videos with speech bubbles."
        echo " Supports trim, cut, reverse, dual-media mode, and meme mode."
    } > control_dir/control
    cd control_dir && tar czf ../control.tar.gz --owner=0 --group=0 ./control && cd ..

    mkdir -p data/usr/local/bin data/usr/share/applications data/usr/share/pixmaps
    cp "$BINARY" data/usr/local/bin/${APP_NAME}
    chmod 755 data/usr/local/bin/${APP_NAME}
    cp "${RPM_STAGE}/usr/share/applications/${PKG_NAME}.desktop" data/usr/share/applications/
    cp "${SCRIPT_DIR}/icons/icon.png" data/usr/share/pixmaps/${PKG_NAME}.png
    cd data && tar czf ../data.tar.gz --owner=0 --group=0 ./usr && cd ..

    ar -r "$DEB_OUT" debian-binary control.tar.gz data.tar.gz 2>/dev/null
    popd > /dev/null
    echo "  ✓ $(basename "$DEB_OUT") (built via ar)"

else
    echo "  ⚠ No DEB tool found (dpkg-deb, alien, or ar)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "=== Build complete — output in lin/ ==="
ls -lh "$LIN_DIR/" 2>/dev/null || true
