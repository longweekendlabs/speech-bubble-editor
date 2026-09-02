# Speech Bubble Editor

**Speech bubbles, comic pages, photo collages, layers, and video edits for desktop.**

[![GitHub Release](https://img.shields.io/github/v/release/longweekendlabs/speech-bubble-editor?style=flat-square)](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platforms](https://img.shields.io/badge/platform-Windows%20x64%20%7C%20Linux%20x64-lightgrey?style=flat-square)](https://longweekendlabs.github.io/speech-bubble-editor/)

Add a speech bubble to a photo, lay out a comic page, build a collage, or trim a video clip. Speech Bubble Editor is a real desktop application, not a web tool: you install it, open it, and your pictures stay on your own machine. Nothing is uploaded, no account is needed, and there is no subscription.

![Speech Bubble Editor interface](docs/screenshots/editor-shape.png)

## Install

Download from the [**latest release**](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest) or the [download page](https://longweekendlabs.github.io/speech-bubble-editor/). Pick one file for your system.

### Windows

| File | Use this when |
| --- | --- |
| `SpeechBubbleEditor-vX.Y.Z-win64-Setup.exe` | **Recommended.** Normal installer, adds Start menu and desktop shortcuts. Installs for your user only, so no administrator password is required. |
| `SpeechBubbleEditor-vX.Y.Z-windows-x64-portable.zip` | You want to run it from a USB stick or without installing. Unzip and run the `.exe`. |

Windows shows a blue "Windows protected your PC" screen the first time, because the installer is not code signed. Click **More info**, then **Run anyway**.

### Linux

| File | Use this when |
| --- | --- |
| `SpeechBubbleEditor-vX.Y.Z-x86_64.AppImage` | **Recommended.** Works on any distribution, no installation, no dependencies. |
| `speech-bubble-editor-X.Y.Z-1.x86_64.rpm` | Fedora, RHEL, openSUSE. |
| `speech-bubble-editor_X.Y.Z_amd64.deb` | Debian, Ubuntu, Mint, Pop!_OS. |
| `SpeechBubbleEditor-vX.Y.Z-linux-x64.tar.gz` | You want a plain folder you can put anywhere. |

AppImage:

```bash
chmod +x SpeechBubbleEditor-*-x86_64.AppImage
./SpeechBubbleEditor-*-x86_64.AppImage
```

Fedora and openSUSE:

```bash
sudo dnf install ./speech-bubble-editor-*.x86_64.rpm
```

Debian and Ubuntu:

```bash
sudo apt install ./speech-bubble-editor_*_amd64.deb
```

The RPM and DEB add Speech Bubble Editor to your applications menu. Everything the app needs, including FFmpeg for video export, is bundled inside the package.

## What it does

- Seven bubble styles: oval, cloud, rectangle, starburst, text-only, scrim, and caption.
- Draggable tails, resize handles, fill and outline colours, opacity, shadows, and full font control.
- Comic Maker with 4, 6, 7, and 8 panel hand-inked layouts you can regenerate without losing your work.
- Photo Collage with 2 to 9 frames, named presets, and portrait, square, story, landscape, or photo canvases.
- Drag photos between frames, move the crop inside a frame, scale from 10% to 500%, and fill the background with blur or a solid colour.
- Lines, blur, and pixelate effects that follow the frame you are working in.
- Video support with a timeline, trim, cut, reverse, slow motion, and audio mute.
- A layer list covering images, videos, bubbles, and captions.
- Meme mode and dual mode for quick social layouts.
- Full resolution image export and video export powered by FFmpeg.
- Undo, redo, reset, keyboard shortcuts, and your operating system's own file dialogs.

## Feedback

Found a bug or want something added? [Open an issue](https://github.com/longweekendlabs/speech-bubble-editor/issues) so it is tracked in public. If you would rather write privately, email [iemrecnl@gmail.com](mailto:iemrecnl@gmail.com?subject=Speech%20Bubble%20Editor%20feedback) and mention which version you are on, shown in the More menu (the three dots at the top right) under About Speech Bubble Editor.

## Build from source

You do not need this to use the app. It is here for anyone who wants to modify it. Requires Python 3.11 or newer.

```bash
git clone https://github.com/longweekendlabs/speech-bubble-editor.git
cd speech-bubble-editor
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Fedora users can build a local RPM with `./build_rpm.sh`. Release packages for both platforms are built automatically by GitHub Actions.

## License

MIT License. See [LICENSE](LICENSE). Free and open source: no licence key, no trial, no subscription.

© 2026 Long Weekend Labs

---

Made with ♥ by **[Long Weekend Labs](https://github.com/longweekendlabs)**
