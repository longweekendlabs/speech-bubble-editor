# Speech Bubble Editor — Roadmap

**Current version:** v3 (shipped)
**Target:** v4
**Status:** Planning — code review done, UI reference locked, ready to start

---

## Current State (v3)

App is shipped and functional. Core features work: speech bubbles on images and video, export, undo for move/resize. Known issues logged below. v4 work has not started — code review and UI reference are the starting point.

**v3 component sizes (for orientation):**

| File | Lines | Notes |
|---|---|---|
| `canvas.py` | ~900 | God Object — do not extend |
| `bubble.py` | ~730 | Oversized, manageable |
| `properties_panel.py` | ~550 | Will be replaced by InspectorDock |
| `video_controls.py` | ~450 | Needs filmstrip + thread fix |
| `main_window.py` | ~370 | 25-signal wire mess |
| `export.py` | ~350 | Critical resolution bug |
| `media_item.py` | ~380 | Duck-typed scene coupling |
| `video_player.py` | ~280 | cv2 eager import |
| `undo_commands.py` | ~210 | Missing 5 command types |
| `toolbar.py` | ~168 | Will become ToolSidebar |
| `main.py` | ~195 | Single-instance order bug |

---

## Phase 1 — Quick Wins (v3 hotfixes, ship before v4 rewrite) `[Copilot]`

> Low effort, high impact. Fix these on v3 before touching architecture.

- [x] Lazy-import `cv2`/`numpy` in `VideoPlayer.load()` and all `export.py` functions — fixes slow startup (W4, V1)
- [x] Move single-instance check before `MainWindow()` in `main.py` — fast fail on duplicate launch (M1)
- [x] Fix export resolution bug in `_export_single_photo` — use native pixmap dimensions, not display size (E1)
- [x] Wrap all `PropertiesPanel` mutations in undo commands — enables Ctrl+Z for style/color/font (P1, U2)
- [x] Extract `IMAGE_EXTENSIONS` / `VIDEO_EXTENSIONS` to `constants.py` — remove three duplicate definitions (C6)
- [x] Add public `stop()` and `current_frame` property to `VideoControls` — remove private attribute access (VC3)
- [x] Cache font-shrink result in `MemeBarItem` — avoid re-computation on every `paint()` (C2)
- [x] Replace `bar._rect = ...` private mutation with `set_geometry()` method on `MemeBarItem` (C4)

---

## Phase 2 — v4 Foundation `[Claude Code]`

> Architecture scaffolding before any UI work.

- [ ] Introduce `constants.py` (if not done in Phase 1)
- [ ] Create `theme/dark.qss` — move all QPalette manipulation out of `main.py` (M3)
- [ ] Add `AppModel` dataclass: holds project metadata, bubble list, media paths — no Qt dependency
- [ ] Add `EditorController`: owns `AppModel`, processes all actions, pushes undo commands, emits signals
- [ ] Wire `EditorController` into `MainWindow` — replace direct cross-component calls with controller methods
- [ ] Defer `QFontComboBox` init — create after window is visible (P3)
- [ ] Defer font loading with `QTimer.singleShot(0, ...)` (M2)

---

## Phase 3 — v4 UI Shell `[Claude Code]` + `[Codex]`

> Build the layout from the reference image (`newui_for_sbe_v40.png`) before any functional wiring.

- [ ] Build `TopBar` widget — logo, Open, Export, Undo/Redo, Zoom control, settings icons
- [ ] Build `ToolSidebar` — vertical icon strip: Select, Move, Bubble, Caption, Text, Layers, Meme Mode, Dual Mode
- [ ] Build `InspectorDock` shell — tabbed: Inspector + Layers tabs, collapsible accordion sections
- [ ] Build `StatusBar` — project name, resolution, fps, duration, autosave indicator
- [ ] Wire `QSplitter` layout: ToolSidebar | CanvasArea | InspectorDock
- [ ] Migrate `VideoControls` into `VideoStrip` inside CanvasArea — add filmstrip thumbnails
- [ ] Apply `dark.qss` across all new widgets

---

## Phase 4 — Inspector Panels `[Codex]`

> Fill in the right-panel accordion sections to match v4 reference.

- [ ] Text section — text input, character counter (19/200 style)
- [ ] Bubble section — 5-style picker (Speech, Cloud, Rectangle, Starburst, Text-only)
- [ ] Colors section — Fill + Stroke color pickers
- [ ] Typography section — font combo, weight, size, text color, alignment
- [ ] Tail section — position dropdown, width control
- [ ] Stroke section — width control
- [ ] Shadow section — toggle, color, blur, offset X/Y, opacity
- [ ] Alignment & Arrange section — align buttons, distribute, z-order
- [ ] Layers tab — list view of scene items with visibility toggles

---

## Phase 5 — Polish & Export `[Copilot]`

- [ ] Fix `VideoPlayer` frame decode to run on background thread — remove UI jank on scrubbing (V3)
- [ ] Add frame cache eviction by memory pressure, not count (V2)
- [ ] Add Cancel button to export progress dialog (E2)
- [ ] Add FFmpeg subprocess timeout (E3)
- [ ] Replace `logging._log` with Python `logging` module (M4)
- [ ] Validate all four build targets: Linux x86/ARM deb+rpm, Windows x86/ARM exe

---

## Backlog (post-v4, not committed)

- [ ] Batch mode — apply same bubble layout to multiple images `[Codex]`
- [ ] Project save/load (`.sbe` format using `AppModel`) `[Claude Code]`
- [ ] Font bundling — ship a set of VN-appropriate fonts
- [ ] Additional bubble shapes via path editor `[Claude Code]`
- [ ] AI-assisted bubble placement (moondream2, local) — not scoped

---

## Reference Files

- UI reference: `/AI/Projects/speech-bubble-editor/newui_for_sbe_v40.png`
- Code review: `/AI/Projects/speech-bubble-editor/codereview.md`
