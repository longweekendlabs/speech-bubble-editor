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

- [x] Introduce `constants.py` (done in Phase 1)
- [x] Create `theme/dark.qss` — QPalette code removed from `main.py`; dark theme in `theme/dark.qss` loaded via `setStyleSheet` (M3)
- [x] Add `AppModel` dataclass in `app_model.py`: media paths, dual/meme flags — no Qt dependency
- [x] Add `EditorController` in `editor_controller.py`: owns AppModel, wraps scene mutations, emits `media_loaded` / `right_media_loaded` signals
- [x] Wire `EditorController` into `MainWindow` — open media, add bubble/overlay, meme/dual mode all route through controller; undo stack accessed via controller
- [x] Defer `QFontComboBox` init — placeholder widget in layout, real combo created with `QTimer.singleShot(0, ...)` after window visible (P3)
- [x] Defer font loading with `QTimer.singleShot(0, _load_fonts)` in `main()` (M2)

---

## Phase 3 — v4 UI Shell `[Claude Code]` + `[Codex]`

> Build the layout from the reference image (`newui_for_sbe_v40.png`) before any functional wiring.

- [x] Build `TopBar` widget — logo, Open, Export, Undo/Redo, zoom label, About (`top_bar.py`)
- [x] Build `ToolSidebar` — vertical icon strip: Select, Bubble, Layer, Meme Mode, Dual Mode (`tool_sidebar.py`)
- [x] Build `InspectorDock` shell — Inspector tab (PropertiesPanel) + Layers placeholder (`inspector_dock.py`)
- [x] Build `StatusBar` — filename shown on media load via `QMainWindow.statusBar()`
- [x] Wire `QSplitter` layout: ToolSidebar | CanvasArea | InspectorDock (`main_window.py` restructured)
- [x] Apply `dark.qss` across all new widgets — TopBar, ToolSidebar, InspectorDock, splitter handle
- [ ] Migrate `VideoControls` into `VideoStrip` inside CanvasArea — filmstrip thumbnails (Phase 5)

---

## Phase 4 — Inspector Panels `[Codex]`

> Fill in the right-panel accordion sections to match v4 reference.

- [x] Text section — text input, character counter (19/200 style)
- [x] Bubble section — 5-style picker (Speech, Cloud, Rectangle, Starburst, Text-only)
- [x] Colors section — Fill + Stroke color pickers
- [x] Typography section — font combo, weight, size, text color, alignment
- [x] Tail section — position dropdown, width control
- [x] Stroke section — width control
- [x] Shadow section — toggle, color, blur, offset X/Y, opacity
- [x] Alignment & Arrange section — align buttons, distribute, z-order
- [x] Layers tab — list view of scene items with visibility toggles
- Phase 4 implemented in `InspectorDock`; added undo-backed bubble properties for text alignment, tail, shadow, and z-order.
- Corrective design pass: bundled `theme/dark.qss` in PyInstaller, forced v4 dark theme loading, and restyled TopBar/ToolSidebar/Inspector to match the reference more closely.
- v4.0.2 release prep: renamed the Actions workflow to a v4 build/release file and set manual artifact builds to default to 4.0.2.

---

## Phase 4b — v4.0.3 Design Handoff Implementation `[Claude Code]`

> Full UI redesign pass matching the design_handoff spec exactly.

- [x] New `context_toolbar.py` — ContextToolbar shown on selection: chip + 6 align + 4 z-order + 2 flip (stub) + delete; wired to scene undo stack
- [x] TopBar height fixed to 52px; button heights 32px; zoom label → QPushButton with 200/150/100/75/50/Fit Width/Fit Window dropdown
- [x] ToolSidebar width fixed to 80px; button size 66×56px; Caption + Text tools emit signals; wired to add bubbles with correct default style
- [x] InspectorDock: 7 bubble styles (added Scrim + Caption to picker with 5-per-row grid); Justify text-alignment button; style name label below picker
- [x] AccordionSection refactored — separate 16×16 chevron QPushButton, teal when open / muted when closed; title label uses #InspectorSectionTitle
- [x] `editor_controller.add_bubble` accepts optional `style` parameter
- [x] Delete key (global shortcut) bound to delete selected bubble/overlay
- [x] `theme/dark.qss` completely rewritten with exact v4 design tokens (accent #46ddcb, Export #00c4a0, bg #141820, panels #1a1f2e, inputs #252d3d, borders #2e3a50, danger #f87171); ContextToolbar, SectionChevron, ContextChip, ContextDeleteBtn styles added
- [x] `version.py` bumped to 4.0.3

---

## Phase 5 — Polish & Export `[Copilot]`

- [x] Fix `VideoPlayer` frame decode to run on background thread — remove UI jank on scrubbing (V3)
- [x] Add frame cache eviction by memory pressure, not count (V2)
- [x] Add Cancel button to export progress dialog (E2) — already present in export.py
- [x] Add FFmpeg subprocess timeout (E3)
- [x] Replace `logging._log` with Python `logging` module (M4)
- [x] Validate all four build targets: Linux x86/ARM deb+rpm, Windows x86/ARM exe (v4.0.1 shipped)
- Phase 5 implemented: `FrameDecodeWorker` (QThread, latest-wins, pause/resume) in `video_player.py`; wired into `PhotoScene` (canvas.py) for left+right players; `FrameCache` now tracks actual bytes; FFmpeg timeout scales from frame count; Python `logging` module replaces custom `_log`.

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
