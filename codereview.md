# Speech Bubble Editor — Code Review & Architecture Analysis

> Reviewed by: GitHub Copilot  
> Target version: v4 Next  
> Date: 2026-04-29

---

## Table of Contents

1. [Current Architecture Overview](#1-current-architecture-overview)
2. [Component Map](#2-component-map)
3. [Critical Issues: Slow Startup](#3-critical-issues-slow-startup)
4. [Anti-patterns & Code Smells](#4-anti-patterns--code-smells)
5. [UI/UX Analysis (v3 vs v4 Target)](#5-uiux-analysis-v3-vs-v4-target)
6. [Proposed v4 Architecture](#6-proposed-v4-architecture)
7. [File-by-File Findings](#7-file-by-file-findings)
8. [Quick-Wins (Low Effort, High Impact)](#8-quick-wins-low-effort-high-impact)
9. [Summary Scorecard](#9-summary-scorecard)

---

## 1. Current Architecture Overview

The application is a **flat, procedural PyQt6 desktop app** with no formal architecture pattern. All state is held directly in Qt widgets/items — there is no model layer and no separation between data and view.

```
main.py
  └── MainWindow (QMainWindow)
        ├── MainToolbar (QToolBar)          ← actions only
        ├── PhotoView (QGraphicsView)       ← render + pan/zoom + drops
        │     └── PhotoScene (QGraphicsScene)  ← ALL state lives here
        │           ├── MediaItem (bg photo/video frame)
        │           ├── BubbleItem (speech bubble)
        │           ├── MemeBarItem
        │           ├── DualSeamItem
        │           └── RightMediaPlaceholder
        ├── ZoomBar (QWidget)
        ├── VideoControls (QWidget)         ← scrubber + playback
        │     └── VideoPlayer (OpenCV)      ← frame decode + cache
        └── PropertiesPanel (QWidget)       ← context-sensitive controls
```

**Style:** Everything talks to everything. `MainWindow._connect_signals()` wires ~25 cross-component signals. `PropertiesPanel` directly mutates `BubbleItem` properties. `MediaItem` reaches into its parent scene via `hasattr()` duck-typing guards.

---

## 2. Component Map

| File | Role | Lines |
|---|---|---|
| `main.py` | Entry point, single-instance, theme setup | ~195 |
| `main_window.py` | Window shell + signal wiring + media routing | ~370 |
| `canvas.py` | Scene + view + zoom + all scene helpers | **~900** |
| `bubble.py` | Speech bubble item + resize/tail handles | **~730** |
| `properties_panel.py` | Bottom inspector panel (4 stacked pages) | ~550 |
| `video_player.py` | OpenCV wrapper + LRU frame cache | ~280 |
| `video_controls.py` | Scrubber + playback controls | ~450 |
| `toolbar.py` | Top toolbar actions | ~168 |
| `media_item.py` | Resizable photo/video background item | ~380 |
| `undo_commands.py` | QUndoCommand subclasses | ~210 |
| `export.py` | Photo + video export (OpenCV + FFmpeg) | ~350 |

**Total: ~4,585 lines** across 11 files. A reasonable size, but `canvas.py` and `bubble.py` are significantly oversized.

---

## 3. Critical Issues: Slow Startup

### 3.1 Synchronous Heavyweight Imports at Launch

`main()` does **all** of the following before the window appears:

```python
from PyQt6.QtWidgets import QApplication   # ~150ms cold import
from main_window import MainWindow          # triggers ALL module imports below
  → from canvas import PhotoScene, PhotoView, ZoomBar
      → from video_player import VideoPlayer   # imports cv2, numpy
  → from toolbar import MainToolbar
  → from properties_panel import PropertiesPanel
  → from video_controls import VideoControls
  → import export as exporter               # imports cv2, numpy, shutil again
```

**`cv2` (OpenCV) and `numpy` are among the heaviest Python packages to import — easily 400–800ms each on a cold start.** They are imported unconditionally at module level even when the user opens a photo (not a video). The same packages are imported in both `video_player.py` and `export.py`, so the overhead hits at module load time for every startup.

**Fix:** Lazy-import `cv2` and `numpy` inside the functions that actually need them:

```python
# video_player.py — load() method
def load(self, path: str) -> bool:
    import cv2          # only pay this cost when loading a video
    ...
```

This alone will likely cut startup time by 50–70%.

### 3.2 `QFontComboBox` in `PropertiesPanel.__init__`

`QFontComboBox` enumerates all system fonts synchronously during `__init__`. This is called at startup inside `_build_ui()`, which blocks the main thread for 100–300ms on systems with many fonts.

**Fix:** Create `PropertiesPanel` lazily after the window is visible, or use `QFontComboBox` with `setWritingSystem()` to limit the font scan.

### 3.3 Single-Instance Check After Window Creation

```python
window = MainWindow()                    # heavy: ~1s to build entire UI
if not _setup_single_instance(window):  # only THEN check if we should exit
    sys.exit(0)
```

The window is **fully constructed** before checking if another instance is running. On a fast machine this wastes ~500ms on startup if the user accidentally double-launches.

**Fix:** Perform the single-instance probe _before_ creating `MainWindow`.

### 3.4 All Fonts Loaded Synchronously Before `MainWindow` Is Created

```python
for fname in os.listdir(fonts_dir):
    QFontDatabase.addApplicationFont(os.path.join(fonts_dir, fname))
```

This blocks the main thread. With many bundled fonts, this adds measurable startup latency.

**Fix:** Load fonts in a `QTimer.singleShot(0, ...)` after the window is shown, or load only required fonts eagerly and defer the rest.

---

## 4. Anti-patterns & Code Smells

### 4.1 God Object: `PhotoScene`

`canvas.py → PhotoScene` is responsible for:

- Holding all media state (`_photo_item`, `_photo_item_right`, players, overlays)
- Loading photos and videos (`load_photo`, `load_video`, `load_right_photo`, `load_right_video`)
- All dual-mode layout logic (`enable_dual_mode`, `_relayout_dual`, `_snap_right_to_left`, `_install_right_media`)
- Meme mode (`enable_meme_mode`, `_update_meme_bar_layout`)
- Overlay layer management (`create_overlay_item`, `remove_overlay`, `_clear_overlays`)
- Scene geometry (`fit_scene_to_media`, `setSceneRect`)
- Mouse event routing (`mousePressEvent`, `mouseDoubleClickEvent`)
- Owning the undo stack

A `QGraphicsScene` should only manage items and paint events. All state and business logic belongs in a separate model or controller.

### 4.2 Duck-Typed Scene Coupling in `MediaItem` and `undo_commands`

Multiple places probe the scene with `hasattr()` to avoid hard imports:

```python
# media_item.py
if sc and hasattr(sc, '_snap_right_to_left'):
    sc._snap_right_to_left()
if sc and hasattr(sc, 'undo_stack'):
    from undo_commands import ResizeMediaCommand
    ...
if sc and hasattr(sc, 'fit_scene_to_media'):
    sc.fit_scene_to_media()
```

```python
# undo_commands.py
if not self._item._is_overlay and hasattr(self._scene, 'fit_scene_to_media'):
    self._scene.fit_scene_to_media()
```

This is fragile. Items should communicate via signals or a narrow interface, not by probing parent scenes by attribute name. It creates invisible circular dependencies and makes refactoring dangerous.

### 4.3 PropertiesPanel Directly Mutates Model

```python
# properties_panel.py
def _on_style(self, key: str):
    if self._bubble:
        self._bubble.set_style(key)   # direct mutation, no undo command
```

Property changes from the panel do not go through the undo stack. Changing a bubble's style, font, color, or border width cannot be undone with Ctrl+Z. This is a significant UX regression compared to move/resize which are correctly undoable.

### 4.4 Private Attribute Access Across Module Boundaries

```python
# canvas.py — _update_meme_bar_layout
bar._rect = QRectF(sr.x(), y, w, bar_h)         # reaches into MemeBarItem._rect
bar._text_item.setTextWidth(w - 32)              # reaches into internal text item
```

```python
# canvas.py — _relayout_dual, _snap_right_to_left
ph._rect = QRectF(snap_x, ly, pw, pht)          # reaches into RightMediaPlaceholder._rect
```

These private accesses bypass encapsulation, making it impossible to change the internal representation of `MemeBarItem` or `RightMediaPlaceholder` without breaking `PhotoScene`. Each class should expose a public `set_geometry()` or similar method.

### 4.5 Duplicate `IMAGE_EXTENSIONS` Definition

`IMAGE_EXTENSIONS` is defined in **three separate files**:

```python
# canvas.py       line 22
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')
# toolbar.py      line 11
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')
# main_window.py  line 27
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')
```

Any update to supported extensions must be made in three places. This belongs in a single `constants.py` or `config.py`.

### 4.6 `VideoControls` Accesses Private State of `MainWindow`

```python
# main_window.py
self.video_controls._stop_playback()   # accesses a private method
...
self.video_controls._current_frame     # accesses a private attribute
```

Accessing `_` prefixed members of another class breaks encapsulation and creates tight coupling. `VideoControls` should expose a public `stop()` and `current_frame` property.

### 4.7 `bubble.py` — `_undo_stack()` Uses `hasattr` Scene Probe

```python
def _undo_stack(self):
    s = self.scene()
    return s.undo_stack if s and hasattr(s, 'undo_stack') else None
```

This returns `None` silently if the item is not in a scene or the scene has no undo stack. Resize operations silently lose their undo history in these edge cases.

### 4.8 Delayed Import Inside Loop in `canvas.py`

```python
# canvas.py — DualSeamItem.paint()
if self._feather > 0:
    from PyQt6.QtGui import QLinearGradient   # imported inside paint() — called every frame
```

`from PyQt6.QtGui import QLinearGradient` inside `paint()` means Python performs a module lookup on every paint call where feathering is active. This is minor but unnecessary; top-level imports are essentially free after the first load.

### 4.9 `export.py` Renders at Display Size, Not Source Resolution

```python
# export.py — _export_single_photo
W = int(photo_item.display_w)   # screen display dimensions!
H = int(photo_item.display_h)
```

The exported image resolution is tied to how large the photo is displayed on screen, not the source file's native resolution. A 4K video displayed in a 900px window would export at 900px. This is a correctness bug that silently degrades output quality. The export should render at the source media's native resolution.

### 4.10 MemeBarItem Font-Shrink Loop Runs in `paint()`

```python
# canvas.py — MemeBarItem.paint()
while font.pixelSize() > min_px:
    fm = QFontMetrics(font)
    if fm.boundingRect(text_rect.toRect(), flags, text).height() <= text_rect.height():
        break
    font.setPixelSize(font.pixelSize() - 2)
```

This O(n) font-shrinking loop runs inside `paint()`, which is called every time Qt needs to redraw that area (on any mouse move over it, any resize, any repaint). The computed result should be cached and invalidated only when the text or geometry changes.

---

## 5. UI/UX Analysis (v3 vs v4 Target)

### What v3 Looks Like Today

- Flat `QToolBar` at the top with text-only `QAction` labels ("Open", "Export", "Undo", "Redo", "＋ Bubble", "+ Layer", "Meme", "Dual")
- No icons in the toolbar — pure text, which looks unpolished
- `PropertiesPanel` is a **fixed-height 96px horizontal strip** pinned to the bottom, always visible, with everything crammed into one row
- No sidebar — no layers panel, no inspector panel
- Video controls occupy a full-width horizontal bar below the canvas
- No dark-mode theme (relies on OS theme passthrough with imperfect Fusion palette)
- No zoom controls visible until media is loaded

### What v4 Should Look Like (from Reference Image)

The reference UI shows a modern, professional dark-themed video editor interface:

| Area | v4 Design |
|---|---|
| **Left sidebar** | Vertical icon strip with labeled tools: Select, Move, Bubble, Caption, Text, Layers, Meme Mode, Dual Mode |
| **Top bar** | App logo + name, Open/Export buttons, Undo/Redo, Zoom indicator — all icon+label style with rounded pill buttons |
| **Canvas** | Full dark-background canvas taking ~75% of the window width |
| **Right panel** | Tabbed **Inspector** (properties) + **Layers** panel — collapsible sections for Text, Bubble, Colors, Typography, Tail, Stroke, Shadow, Alignment |
| **Bottom** | Video player strip with filmstrip thumbnail, scrubber, playback controls, time display, FPS indicator, Cut/Marker/Reverse buttons, zoom/fit timeline controls |
| **Status bar** | Project info (filename, resolution, FPS, duration), autosave indicator |

### Key Structural Changes Needed

1. **Replace `QToolBar` with a custom vertical `QToolBar` or `QWidget` sidebar** — the tool names and icons in the design are vertically arranged with icon above label.

2. **Replace `PropertiesPanel` (bottom strip) with a right-side inspector panel** — use `QDockWidget` or a custom panel. Organize by collapsible sections (accordion style): Text, Bubble, Colors, Typography, Tail, Stroke, Shadow, Alignment & Arrange.

3. **Add a Layers panel** (tabbed next to Inspector) — shows a list of all bubbles and overlays with thumbnail, eye icon for visibility, lock icon, z-order drag. This is a missing feature in v3.

4. **Redesign video controls** — the reference shows a filmstrip thumbnail strip above the scrubber, time-code displays, FPS indicator, and a "Fit Timeline" zoom control. The current `VideoScrubber` is a plain colored bar.

5. **Add a proper dark theme stylesheet** — the reference uses a consistent `#1a1a1a` / `#2a2a2a` / `#3a3a3a` dark palette with teal accent (`#00b4d8`). This should be a single QSS stylesheet file, not palette hacks in `main.py`.

6. **Add text input field in Inspector** — the reference shows a multi-line text box at the top of the inspector (character count `19/200`) instead of double-clicking on the canvas to type. This is more discoverable.

7. **Style picker as icon buttons** — the reference shows bubble style as small icon previews (oval, cloud, rect, spiky, text-only) rather than text labels.

8. **Color fields show hex value** — the reference shows `#FFFFFF` / `#000000` next to color swatches with an eyedropper icon. The current color buttons show only a colored square.

---

## 6. Proposed v4 Architecture

### 6.1 Introduce a Model Layer

The current architecture has **no separation between data and presentation**. In v4, introduce a thin model layer:

```
AppModel (plain Python, no Qt)
  ├── Project
  │     ├── media_path: str
  │     ├── bubbles: list[BubbleData]
  │     ├── trim_in / trim_out
  │     └── cuts: list[tuple]
  └── BubbleData
        ├── style, position, size
        ├── fill_color, border_color, border_width
        ├── text, font, text_color
        └── tail_position
```

Benefits: serializable to JSON (save/load projects), testable without Qt, clear ownership of state.

### 6.2 Introduce a Command Bus / Controller

Rather than `MainWindow` wiring 25 signals, use a thin controller:

```
EditorController
  ├── Holds AppModel reference
  ├── Processes actions: add_bubble(), delete_bubble(), set_style(), etc.
  ├── Pushes undo commands (ALL property changes, not just move/resize)
  └── Notifies views via signals
```

`PropertiesPanel` calls `controller.set_bubble_style(key)` instead of `bubble.set_style(key)`. The controller wraps it in an undo command.

### 6.3 Layout Structure for v4

```
MainWindow (QMainWindow)
  ├── MenuBar (native menus)
  ├── TopBar (custom QWidget — logo, file ops, undo/redo, zoom)
  ├── Central area (QSplitter — resizable)
  │     ├── Left: ToolSidebar (custom QWidget — vertical icon tool strip)
  │     ├── Center: CanvasArea
  │     │     ├── PhotoView (QGraphicsView)
  │     │     └── VideoStrip (custom QWidget — filmstrip + scrubber)
  │     └── Right: InspectorDock (QDockWidget)
  │           ├── [Inspector tab] PropertyAccordion (collapsible sections)
  │           └── [Layers tab] LayersPanel (list view of items)
  └── StatusBar (project info, autosave)
```

### 6.4 Fix the Export Resolution Bug

```python
# Correct: always export at source resolution
def export_photo(scene, photo_item):
    px = photo_item.pixmap()           # native resolution
    W, H = px.width(), px.height()     # source dimensions
    # ... render scene scaled to W×H
```

### 6.5 Stylesheet-Driven Dark Theme

Replace the in-code `QPalette` manipulation in `main.py` with a single `.qss` file:

```css
/* theme/dark.qss */
QMainWindow, QWidget { background: #1e1e1e; color: #e0e0e0; }
QToolButton { border: none; border-radius: 6px; padding: 4px 8px; }
QToolButton:hover { background: #2d2d2d; }
QToolButton:checked { background: #0097a7; color: white; }
QPushButton#pill { background: #0097a7; border-radius: 12px; color: white; padding: 6px 16px; }
...
```

Load at startup: `app.setStyleSheet(open("theme/dark.qss").read())`.

---

## 7. File-by-File Findings

### `main.py`

| # | Finding | Severity |
|---|---|---|
| M1 | Single-instance check happens AFTER MainWindow construction | Medium |
| M2 | Font loading blocks main thread before window shows | Low |
| M3 | `_apply_system_theme` hardcodes 14 color values — replace with QSS | Low |
| M4 | `_log` opens a file and flushes on every log call — use `logging` module | Low |

### `main_window.py`

| # | Finding | Severity |
|---|---|---|
| W1 | `_connect_signals` wires 25 signals — this is a maintenance trap | Medium |
| W2 | `self.scene._photo_item._source_path = path` — bypasses encapsulation (3 levels deep) | Medium |
| W3 | `self.video_controls._stop_playback()` — accesses private method | Medium |
| W4 | `VIDEO_EXTENSIONS` imported from `video_player` which forces `cv2` import at startup | High |
| W5 | `PropertiesPanel` is placed below the canvas in a `QVBoxLayout` — not a sidebar | Medium |

### `canvas.py`

| # | Finding | Severity |
|---|---|---|
| C1 | `PhotoScene` is a God Object (~500 lines of methods) | High |
| C2 | Font-shrink loop runs inside `MemeBarItem.paint()` every frame | Medium |
| C3 | `from PyQt6.QtGui import QLinearGradient` inside `paint()` | Low |
| C4 | Private attribute mutation across class boundaries (`bar._rect`, `ph._rect`) | Medium |
| C5 | `cv2`/`numpy` imported via `video_player` at module level — slows startup | High |
| C6 | `IMAGE_EXTENSIONS` duplicated from `toolbar.py` | Low |
| C7 | `ZoomBar` defined in `canvas.py` — should be its own file or part of a ui/ package | Low |

### `bubble.py`

| # | Finding | Severity |
|---|---|---|
| B1 | `_notify_changed` calls `scene.bubble_changed.emit()` — tight scene coupling | Low |
| B2 | `_undo_stack()` silently returns `None` — resize can lose undo history | Medium |
| B3 | `_reposition_text()` runs a font-shrink loop — same concern as MemeBarItem | Low |
| B4 | `ResizeHandle.mouseReleaseEvent` imports `ResizeBubbleCommand` inline | Low |

### `properties_panel.py`

| # | Finding | Severity |
|---|---|---|
| P1 | **All property changes bypass the undo stack** — no Ctrl+Z for style/color/font | High |
| P2 | Panel is fixed 96px — all v4 controls won't fit, inspector needs to be a sidebar | High |
| P3 | `QFontComboBox` initialized synchronously at startup | Medium |
| P4 | Page 3 (dual settings) rendered inside properties panel — should be inspector section | Low |

### `video_player.py`

| # | Finding | Severity |
|---|---|---|
| V1 | `import cv2` and `import numpy` at module top level — imported even for photo-only sessions | High |
| V2 | Frame cache evicts by count, not by memory pressure — 256MB budget computed once at load | Low |
| V3 | No background thread for frame decoding — scrubbing can hitch the UI thread | Medium |

### `video_controls.py`

| # | Finding | Severity |
|---|---|---|
| VC1 | `VideoScrubber.paintEvent` draws everything manually — filmstrip thumbnails missing | Medium |
| VC2 | Playback uses `QTimer` on UI thread — can cause jank on large videos | Medium |
| VC3 | `_current_frame` is a public attribute accessed directly from `MainWindow` | Medium |

### `export.py`

| # | Finding | Severity |
|---|---|---|
| E1 | **Exports at display size, not source resolution** | Critical |
| E2 | No progress cancellation support (dialog has no Cancel implementation) | Low |
| E3 | FFmpeg subprocess call has no timeout | Low |

### `undo_commands.py`

| # | Finding | Severity |
|---|---|---|
| U1 | `MoveBubbleCommand` and `MoveMediaCommand` share the same merge ID (`42`, `43`) — if both are on the stack, merges will never collide, but the magic numbers should be named constants | Low |
| U2 | Missing undo commands for: style change, color change, font change, text color, opacity | High |

---

## 8. Quick-Wins (Low Effort, High Impact)

These changes can be made to v3 immediately before a full v4 rewrite:

1. **Lazy-import cv2/numpy** in `VideoPlayer.load()` and `export.py` functions — fixes slow startup.
2. **Move single-instance check before `MainWindow()`** in `main.py` — fast fail for duplicate launches.
3. **Wrap all `PropertiesPanel` mutations in undo commands** — enables Ctrl+Z for style/color/font.
4. **Extract `IMAGE_EXTENSIONS` to a single `constants.py`** — removes three duplicate definitions.
5. **Add public `stop()` and `current_frame` property to `VideoControls`** — removes private attribute access.
6. **Cache font-shrink result in `MemeBarItem`** — avoids re-computation on every paint.
7. **Fix export resolution** in `_export_single_photo` to use native pixmap dimensions.
8. **Replace `bar._rect = ...` private mutation** with a `set_geometry()` method on `MemeBarItem` and `RightMediaPlaceholder`.

---

## 9. Summary Scorecard

| Dimension | v3 Score | Notes |
|---|---|---|
| **Startup performance** | 2/10 | cv2/numpy eagerly imported; QFontComboBox at init; single-instance check after full window build |
| **Architecture clarity** | 4/10 | Flat, no model layer, God Object scene |
| **Encapsulation** | 3/10 | Private attribute access across files, duck-typed scene probes |
| **Undo coverage** | 5/10 | Move/resize covered; style/color/font not |
| **Export quality** | 4/10 | Exports at display size, not source resolution |
| **UI modernity** | 3/10 | Text-only toolbar, fixed bottom panel, no icons, inconsistent theme |
| **Code maintainability** | 5/10 | Well-commented, reasonable file structure, but too much coupling |
| **v4 readiness** | 2/10 | Significant structural work needed to reach v4 design target |

### Recommended v4 Priority Order

1. **Fix startup performance** (lazy imports, move single-instance check) — ships immediate value
2. **Introduce `constants.py`** and clean up duplicate definitions
3. **Add right-side `InspectorPanel`** with collapsible sections replacing the bottom strip
4. **Wrap all property changes in undo commands**
5. **Add vertical `ToolSidebar`** matching v4 design
6. **Introduce `AppModel` / `BubbleData`** for project save/load
7. **Redesign `VideoControls`** with filmstrip thumbnails
8. **Apply QSS dark theme** matching v4 reference
9. **Fix export resolution bug**
10. **Add `LayersPanel`** (tabbed with Inspector)
