# Speech Bubble Editor

Speech bubbles, comic pages, photo collages, layers, and video edits for desktop.

[![GitHub Release](https://img.shields.io/github/v/release/longweekendlabs/speech-bubble-editor?style=flat-square)](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platforms](https://img.shields.io/badge/platform-Windows%20x64%20%7C%20Linux%20x64-lightgrey?style=flat-square)](https://longweekendlabs.github.io/speech-bubble-editor/)

Speech Bubble Editor is a native desktop app for expressive bubbles, captions, comic pages, and photo collages. Open media, build and rearrange a composition, tune its frames and effects, or edit a video—all locally, without uploading your files to a cloud service.

![Speech Bubble Editor interface](docs/screenshots/editor-shape.png)

## Download

Get the latest builds from the [download page](https://longweekendlabs.github.io/speech-bubble-editor/) or the [GitHub Releases page](https://github.com/longweekendlabs/speech-bubble-editor/releases/latest).

| Platform | Builds |
| --- | --- |
| Windows x64 | Setup `.exe`, portable `.zip` |
| Linux x64 | AppImage, DEB, RPM, portable `.tar.gz` |
| Source | `.zip`, `.tar.gz`, or clone this repository |

## Highlights

- Natural speech bubble styles: oval, cloud, rectangle, starburst, text-only, scrim, and caption.
- Draggable bubble tails, resize handles, fill/stroke controls, opacity, shadows, and font styling.
- Comic Maker with 4, 6, 7, or 8-panel hand-inked layouts, live layout controls, and nondestructive regeneration.
- Photo Collage with 2–9 frames, visual layout choices, named presets, and portrait, square, story, landscape, or photo canvases.
- Magnetic drag-and-drop photo reordering plus independent crop movement, 10–500% image scaling, Fit, and blurred or solid frame backgrounds.
- Frame-aware lines, blur, and pixelate effects with a clearly highlighted active frame.
- Photo and video support with timeline controls, trim, cut, reverse, slow-down, and optional audio mute.
- Layer list for stacked images, videos, bubbles, and captions.
- Meme mode and dual mode for fast social-style layouts.
- Full-resolution image export and FFmpeg-powered video export.
- Undo/redo, reset, keyboard shortcuts, and native file pickers.

## Run from Source

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/longweekendlabs/speech-bubble-editor.git
cd speech-bubble-editor
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

On Windows, activate the virtual environment with:

```powershell
venv\Scripts\activate
```

## Build Packages

Official cross-platform release builds are produced by GitHub Actions. Fedora users can also build an RPM locally:

```bash
./build_rpm.sh
```

## Project Layout

```text
.
├── main.py                 # app entry point
├── main_window.py          # primary window and actions
├── canvas_widget.py        # canvas, selection, drawing, media placement
├── inspector_dock.py       # right-side inspector controls
├── video_controls.py       # timeline and playback controls
├── icons/                  # app icons and Long Weekend Labs logo
├── fonts/                  # bundled fonts
├── theme/                  # Qt stylesheet
├── docs/                   # GitHub Pages website and screenshots
├── speech_bubble.spec      # cross-platform PyInstaller configuration
├── speech_bubble_rpm.spec  # Fedora RPM PyInstaller configuration
└── build_rpm.sh            # local Fedora RPM builder
```

## Release Process

Every push to `main` builds test artifacts for Windows and Linux. Releases are driven by tags named `v*`.

```bash
git tag v4.5.0
git push origin v4.5.0
```

The release workflow tests the app, builds Windows x64 and Linux x64 packages plus source archives, and attaches tagged builds to the GitHub Release.

## License

MIT License. See [LICENSE](LICENSE).

---

Made with ♥ by **[Long Weekend Labs](https://github.com/longweekendlabs)**
