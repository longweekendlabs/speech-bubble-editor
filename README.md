# Speech Bubble Editor

**Add speech bubbles, captions, and text overlays to photos and videos.**
Built by [Long Weekend Labs](https://longweekendlabs.github.io/speech-bubble-editor)

---

## Features

- **7 bubble styles** — Oval, Cloud, Rectangle, Spiky, Text-only, Scrim, and Caption (stroke text)
- **Video support** — MP4, AVI, WebM, MOV, MKV with frame-accurate scrubbing
- **Trim & cut** — select a clip range, cut sections, reverse playback
- **Dual mode** — side-by-side before/after layout
- **Meme mode** — Impact/Anton-style top and bottom caption bars
- **Full-resolution export** — PNG, JPEG, WebP; video export via FFmpeg (audio preserved)
- **Drag & resize** — 8-anchor handles, draggable tail, undo/redo
- **Font controls** — family, size, bold, italic, colour; auto-shrink to fit
- **Windows dark/light mode** — follows your OS theme automatically

---

## Download

Head to the **[Releases page](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest)** to grab the latest build for your platform.

| Platform | File | Notes |
|---|---|---|
| Linux (any distro) | `SpeechBubbleEditor-*.AppImage` | Double-click to run, no install |
| Fedora / RHEL | `speech-bubble-editor-*.rpm` | `sudo dnf install ./file.rpm` |
| Ubuntu / Mint | `speech-bubble-editor_*.deb` | `sudo dpkg -i file.deb` |
| Linux (archive) | `SpeechBubbleEditor-*-linux.tar.gz` | Extract and run |
| Windows | `SpeechBubbleEditor-*-win64-Setup.exe` | Installer |
| Windows portable | `SpeechBubbleEditor-*-win64-portable.zip` | No install needed |

---

## Screenshots

*(Add screenshots to `docs/screenshots/` and update this section)*

---

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

**To build release packages:**

```bash
# Linux
bash build_linux.sh

# Windows — run on a Windows machine
build_windows.bat
```

---

## Releasing a New Version

1. Update `version.py` with the new version number and history entry
2. Commit the change: `git commit -am "Release vX.Y.Z"`
3. Tag it: `git tag vX.Y.Z`
4. Push: `git push && git push --tags`

GitHub Actions will automatically build all packages and publish them to Releases.

---

## Dependencies

- [PyQt6](https://pypi.org/project/PyQt6/) — UI framework
- [OpenCV](https://pypi.org/project/opencv-python/) — video decoding
- [Pillow](https://pypi.org/project/Pillow/) — image export
- [FFmpeg](https://ffmpeg.org/) — video export with audio (must be installed separately)

---

## License

© 2026 Long Weekend Labs. All rights reserved.
