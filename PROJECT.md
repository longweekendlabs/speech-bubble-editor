# Speech Bubble Editor

**Brand:** Long Weekend Labs
**Repo:** https://github.com/longweekendlabs/speech-bubble-editor
**Site:** GitHub Pages (longweekendlabs)
**Status:** 🔧 Active — v3 shipped, v4 in progress

---

## Problem

Visual novel and AVN creators need to add speech bubbles, dialogue boxes, and text overlays to static images and video clips. Existing tools are either too heavyweight (Photoshop), too limited (meme generators), or don't handle video. The current v3 codebase is functional but has poor startup performance, no undo coverage for style changes, and a fixed bottom panel that can't accommodate the full inspector needed for v4.

## Goal

A focused, fast, offline desktop tool for adding professional-quality speech bubbles to images and video. v4 introduces a modern side-inspector layout (matching the v4 UI reference), fixes critical bugs (export resolution, missing undo coverage), and cleans up the architecture enough to make ongoing improvements sustainable.

## Stack

- **Language:** Python 3
- **UI:** PyQt6
- **Video decode:** OpenCV (`cv2`) + NumPy — lazy-imported, never at module top level
- **Video export:** FFmpeg (subprocess)
- **Theme:** QSS dark stylesheet (`theme/dark.qss`)
- **Packaging:** PyInstaller

## Platforms

- Linux x86_64 — `.deb` + `.rpm`
- Windows x86_64 — `.exe` (NSIS per-user, no admin)
- Windows ARM64 — `.exe`
- Linux ARM64 — `.deb` + `.rpm`
- macOS ARM64 (Apple Silicon) — `.dmg` (unsigned; requires `brew install ffmpeg` for video export)

## v4 UI Layout (reference: `newui_for_sbe_v40.png`)

```
MainWindow (QMainWindow)
  ├── TopBar         — logo, Open/Export, Undo/Redo, Zoom, settings icons
  ├── Central area (QSplitter)
  │     ├── Left: ToolSidebar  — Select, Move, Bubble, Caption, Text, Layers, Meme Mode, Dual Mode
  │     ├── Center: CanvasArea
  │     │     ├── PhotoView (QGraphicsView)
  │     │     └── VideoStrip  — filmstrip thumbnails + scrubber + playback controls
  │     └── Right: InspectorDock
  │           ├── [Inspector tab]  — Text, Bubble style picker, Colors, Typography, Tail, Stroke, Shadow, Alignment & Arrange
  │           └── [Layers tab]     — ordered list of scene items
  └── StatusBar  — project name, resolution, fps, duration, autosave indicator
```

**Bubble styles (Inspector):** Speech (rounded), Cloud (thought), Rectangle, Starburst, Text-only

## Key Architectural Decisions

- **No separate windows** — everything lives inside the single main window; inspector is a docked sidebar, not a floating panel
- **Lazy imports for cv2/numpy** — imported inside functions that need them, never at module top level; non-negotiable for startup performance
- **Single-instance check before `MainWindow()` construction** — fail fast on duplicate launch
- **All property changes go through undo commands** — style, color, font, text color, opacity all undoable via Ctrl+Z
- **QSS dark theme** — single `theme/dark.qss` file; no in-code QPalette manipulation
- **`constants.py`** — single source of truth for `IMAGE_EXTENSIONS`, `VIDEO_EXTENSIONS`, undo merge IDs, and other shared constants
- **Export at source resolution** — always render at native pixmap/video dimensions, never at display/zoom size
- **`PhotoScene` is a God Object (known)** — do not extend it further; refactor toward `AppModel` + `EditorController` incrementally, not all at once

## Performance Budget

- Cold startup target: < 2 seconds on a mid-spec machine
- Achieved by: lazy `cv2`/`numpy`, deferred `QFontComboBox` init, single-instance check before window build, font loading via `QTimer.singleShot`

## Known Critical Bugs (Copilot code review, 2026-04-29)

| ID | File | Issue | Severity |
|---|---|---|---|
| E1 | `export.py` | Exports at display size, not source resolution | Critical |
| P1 | `properties_panel.py` | Style/color/font changes bypass undo stack | High |
| W4 | `main_window.py` | `VIDEO_EXTENSIONS` import forces `cv2` load at startup | High |
| V1 | `video_player.py` | `cv2`/`numpy` imported at module top level | High |
| C1 | `canvas.py` | `PhotoScene` is a God Object (~500 lines of methods) | High |
| U2 | `undo_commands.py` | Missing undo commands: style, color, font, text color, opacity | High |

Full review in `/AI/Projects/speech-bubble-editor/codereview.md`.

## Build & Deploy Notes

- Packaged via PyInstaller
- Released via GitHub Releases
- Landing page via GitHub Pages under `longweekendlabs` org
- Use `[skip ci]` for docs/config-only commits
- Accumulate local phases before pushing — one CI run per phase group

## Out of Scope

- Cloud storage or sync
- Subscription or in-app purchase
- macOS Intel (x86_64) — Apple Silicon only; Rosetta fallback not tested
- AI-assisted bubble placement (possible future idea)
