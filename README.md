# Speech Bubble Editor

**Add speech bubbles, captions, and text overlays to photos and videos.**

[![GitHub Release](https://img.shields.io/github/v/release/longweekendlabs/speech-bubble-editor?style=flat-square)](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platform: Windows | macOS | Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)](#download)

A truly cross-platform tool for adding expressive text to your media. Built for speed, performance, and offline-first workflows.

---

## Features

- **7 bubble styles** — Oval, Cloud, Rectangle, Spiky, Text-only, Scrim, and Caption (stroke text)
- **Video support** — MP4, AVI, WebM, MOV, MKV with frame-accurate scrubbing
- **Trim & cut** — select a clip range, cut sections, reverse playback
- **Dual mode** — side-by-side before/after layout with configurable gap and border
- **Overlay layers** — stack multiple photos or videos on the canvas; right-click to control z-order
- **Meme mode** — Impact/Anton-style top and bottom caption bars
- **Full-resolution export** — PNG, JPEG, WebP; video export via bundled FFmpeg, with optional audio mute
- **Drag & resize** — 8-anchor handles, draggable tail, undo/redo for everything
- **Font controls** — family, size, bold, italic, colour; auto-shrink to fit
- **Single instance** — re-activates the existing window instead of opening a second copy

## Download

Head to the **[Releases page](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest)** to grab the latest build for your platform.

| Platform | Package | Notes |
|---|---|---|
| **Windows x64** | `SpeechBubbleEditor-vX.Y.Z-windows-x64-portable.zip` | No install needed; unzip and run. |
| **Linux x64** | `SpeechBubbleEditor-vX.Y.Z-linux-x64.tar.gz` | Portable binary archive. |
| **macOS Intel** | `SpeechBubbleEditor-vX.Y.Z-macos-x64.zip` | macOS 12+. Right-click → Open first time. |
| **macOS Apple Silicon** | `SpeechBubbleEditor-vX.Y.Z-macos-arm64.zip` | macOS 12+, M1/M2/M3/M4. Right-click → Open first time. |
| **Source code** | `source.zip` / `source.tar.gz` | Also generated automatically by GitHub Releases. |

## Building from Source

**Requirements:** Python 3.11+, pip

```bash
git clone https://github.com/longweekendlabs/speech-bubble-editor.git
cd speech-bubble-editor
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Build release packages:

```bash
# macOS (native Intel or Apple Silicon, depending on build machine)
python create_icon.py
iconutil -c icns icons/icon.iconset -o icons/icon.icns
python -m PyInstaller --clean --noconfirm speech_bubble_macos.spec

# Linux
bash build_linux.sh

# Windows
build_windows.bat
```

## Dependencies

- **PyQt6** — UI framework
- **OpenCV** — video decoding
- **Pillow** — image export
- **FFmpeg** — video export with audio; bundled into official release builds when available in CI

## Release Builds

Release artifacts are built by GitHub Actions from tags named `v*`, for example:

```bash
git tag v4.0.4
git push origin v4.0.4
```

The workflow builds Windows x64, Linux x64, macOS Intel, macOS Apple Silicon, and source archives, then attaches them to the GitHub Release.

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Made with ♥ by **[Long Weekend Labs](https://github.com/longweekendlabs)**
