# Speech Bubble Editor v4 — Complete Design Handoff

**Repo:** `longweekendlabs/speech-bubble-editor`  
**Stack:** Python 3 + PyQt6 + QSS (`theme/dark.qss`)  
**Design reference:** Open `Speech Bubble Editor.html` in a browser — fully interactive prototype.

---

## How to use this package

1. Open `Speech Bubble Editor.html` in Chrome/Firefox — interact with the full UI
2. Read this README for every spec value — copy-paste SVG paths directly
3. Drop the files in `pyqt_output/` directly into the repo root
4. Run the app — it should match the prototype visually

**Do not guess. Every icon path, every color, every pixel dimension is specified here.**

---

## Table of Contents

1. [Themes](#1-themes)
2. [Layout & Dimensions](#2-layout--dimensions)
3. [TopBar](#3-topbar)
4. [ContextToolbar](#4-contexttoolbar)
5. [ToolSidebar](#5-toolsidebar)
6. [Inspector — Section Chrome](#6-inspector--section-chrome)
7. [Inspector — Bubble Style Picker](#7-inspector--bubble-style-picker)
8. [Inspector — Typography Alignment Buttons](#8-inspector--typography-alignment-buttons)
9. [Inspector — All Other Sections](#9-inspector--all-other-sections)
10. [Timeline / VideoControls](#10-timeline--videocontrols)
11. [Canvas & Selection Handles](#11-canvas--selection-handles)
12. [StatusBar](#12-statusbar)
13. [QSS Rules](#13-qss-rules)

---

## 1. Themes

Three themes. All values are exact hex strings from the prototype.  
The accent color is **user-configurable** (default `#46ddcb`). Every place that uses `accent` below means the current user-chosen accent.

### Theme: `dark` (default)

| Token | Hex |
|---|---|
| `appBg` | `#141820` |
| `topBarBg` | `#1a1f2e` |
| `sidebarBg` | `#1a1f2e` |
| `canvasBg` | `#0f1319` |
| `inspectorBg` | `#1a1f2e` |
| `panelBorder` | `#252d3d` |
| `sectionBg` | `#1e2535` |
| `inputBg` | `#252d3d` |
| `inputBorder` | `#2e3a50` |
| `textPrimary` | `#e8ecf4` |
| `textSecondary` | `#8a95aa` |
| `textMuted` | `#4e5a6e` |
| `btnHover` | `#2a3347` |
| `btnActive` | `#2e3d5a` |
| `timelineBg` | `#131820` |
| `filmBg` | `#0d1117` |
| `scrubberTrack` | `#252d3d` |
| `playhead` | accent color |
| `export` (CTA bg) | `#00c4a0` |
| `exportHover` | `#00ddb5` |
| `danger` | `#f87171` |
| `autosaveDot` | `#22c55e` |

### Theme: `oled` (AMOLED Black)

| Token | Hex |
|---|---|
| `appBg` | `#000000` |
| `topBarBg` | `#0a0a0a` |
| `sidebarBg` | `#0a0a0a` |
| `canvasBg` | `#000000` |
| `inspectorBg` | `#0a0a0a` |
| `panelBorder` | `#1a1a1a` |
| `sectionBg` | `#111111` |
| `inputBg` | `#1a1a1a` |
| `inputBorder` | `#222222` |
| `textPrimary` | `#f0f0f0` |
| `textSecondary` | `#777777` |
| `textMuted` | `#444444` |
| `btnHover` | `#1a1a1a` |
| `btnActive` | `#222222` |
| `timelineBg` | `#050505` |
| `filmBg` | `#000000` |
| `scrubberTrack` | `#1a1a1a` |
| `playhead` | accent color |
| `export` | `#00c4a0` |
| `exportHover` | `#00ddb5` |

### Theme: `slate` (Blue Slate)

| Token | Hex |
|---|---|
| `appBg` | `#0f1623` |
| `topBarBg` | `#131c2e` |
| `sidebarBg` | `#131c2e` |
| `canvasBg` | `#0a1020` |
| `inspectorBg` | `#131c2e` |
| `panelBorder` | `#1e2d47` |
| `sectionBg` | `#172038` |
| `inputBg` | `#1e2d47` |
| `inputBorder` | `#253659` |
| `textPrimary` | `#ccd6f6` |
| `textSecondary` | `#7a8caa` |
| `textMuted` | `#3d4f69` |
| `btnHover` | `#1e2d47` |
| `btnActive` | `#253659` |
| `timelineBg` | `#0c1525` |
| `filmBg` | `#08101e` |
| `scrubberTrack` | `#1e2d47` |
| `playhead` | `#7c83ff` (overrides user accent in slate) |
| `export` | `#5865f2` |
| `exportHover` | `#6b74ff` |

### QSS implementation

In `theme/dark.qss`, represent themes as named `QWidget` property selectors. The simplest approach for PyQt6 is to read the theme name from a config and call `app.setStyleSheet()` with the full QSS string for that theme. Alternatively, use CSS variables via a template string.

**Do not hardcode colors in Python files.** All colors come from the QSS file.

---

## 2. Layout & Dimensions

```
MainWindow (min: 1180×720, default: 1440×900)
  ┌─ TopBar                    height: 52px
  ├─ ContextToolbar            height: 38px  (hidden when nothing selected)
  ├─ Content row (flex row)
  │   ├─ ToolSidebar           width: 80px fixed
  │   └─ QSplitter (horizontal)
  │       ├─ Canvas area       flex: 1
  │       │   ├─ PhotoView     flex: 1
  │       │   ├─ ZoomBar       thin strip
  │       │   └─ VideoControls collapsible
  │       └─ InspectorDock     width: 320px (min 280, max 380)
  └─ StatusBar                 height: 26px
```

**Gaps:** All panel gaps are 0. Borders separate panels (1px `panelBorder`).

**Font:** Inter (Google Fonts), weights 300/400/500/600/700. Base size 12px.

---

## 3. TopBar

**Height:** 52px | **Background:** `topBarBg` | **Border-bottom:** 1px `panelBorder`

### Logo area (left, gap 8px)

- **App icon SVG** (22×22px):
  ```svg
  <svg viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" fill="{accent}" opacity="0.15"/>
    <path d="M8 12h8M8 8h8M8 16h5" stroke="{accent}" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="10" stroke="{accent}" stroke-width="1.5"/>
  </svg>
  ```
- **"Speech Bubble Editor"** — 13px, weight 700, `textPrimary`, letter-spacing -0.02em
- **"by Long Weekend Labs"** — 11px, weight 400, `textMuted`

### Center buttons (flex row, gap 6px, padding 0 16px)

All buttons: height 32px, border-radius 6px, font 12px Inter, display flex+center+gap 5px.

#### Open button
- Border: 1px `inputBorder` | Color: `textSecondary` | Hover bg: `btnHover`
- **Icon SVG** (14×14, viewBox 0 0 24 24, stroke, no fill):
  ```svg
  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
    stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  ```
- Label: "Open…" | Shortcut: Ctrl+O

#### Export button
- **Background: `export` color** (NOT border style) | Text: white | Font-weight: 600
- Hover bg: `exportHover` | Disabled: opacity 0.4
- **Icon SVG** (14×14, viewBox 0 0 24 24, stroke white):
  ```svg
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <polyline points="17 8 12 3 7 8" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <line x1="12" y1="3" x2="12" y2="15" stroke="white" stroke-width="2" stroke-linecap="round"/>
  ```
- Label: "Export…" | Shortcut: Ctrl+E

#### Separator
- 1px wide × 22px tall | Color: `panelBorder` | Margin: 0 4px

#### Undo button
- Border: 1px `inputBorder` | Color: `textSecondary` | Disabled: `textMuted`, opacity 0.4
- **Icon SVG** (14×14, viewBox 0 0 24 24):
  ```svg
  <path d="M3 7v6h6" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M3 13C5 7 10 4 16 5.5a9 9 0 0 1 5 7.5" stroke="{color}" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  ```
- Label: "Undo" | Shortcut: Ctrl+Z

#### Redo button
- **Icon SVG** (14×14, viewBox 0 0 24 24):
  ```svg
  <path d="M21 7v6h-6" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M21 13C19 7 14 4 8 5.5A9 9 0 0 0 3 13" stroke="{color}" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  ```
- Label: "Redo" | Shortcut: Ctrl+Y

#### Zoom picker button
- Background: `inputBg` | Border: 1px `inputBorder` | Min-width: 110px
- Shows current zoom: e.g. "100%" or "Fit Width"
- **Magnifier icon SVG** (13×13, viewBox 0 0 24 24):
  ```svg
  <circle cx="11" cy="11" r="8" stroke="{color}" stroke-width="2" fill="none"/>
  <path d="M21 21l-4.35-4.35" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  ```
- **Chevron SVG** (10×10): `<path d="M6 9l6 6 6-6" stroke="{color}" stroke-width="2.5" stroke-linecap="round" fill="none"/>`
- **Dropdown options:** 200% / 150% / 100% ✓ / 75% / 50% / --- / Fit Width / Fit Window
- Checkmark shown next to current selection

### Right icon buttons (32×32px each, border-radius 6px)

Hover: bg `btnHover` + border 1px `inputBorder`. Default: transparent bg, no border.

#### Sun / Theme button
- Tooltip: "Toggle light/dark theme"
- **Icon SVG** (15×15, viewBox 0 0 24 24, stroke, no fill):
  ```svg
  <circle cx="12" cy="12" r="5" stroke="{color}" stroke-width="1.8" fill="none"/>
  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42
           M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
    stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
  ```

#### Gear / Preferences button
- Tooltip: "Preferences — keyboard shortcuts, export defaults, canvas settings"
- **Icon SVG** (15×15, viewBox 0 0 24 24):
  ```svg
  <circle cx="12" cy="12" r="3" stroke="{color}" stroke-width="1.8" fill="none"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33
           1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33
           l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4
           h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06
           A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51
           1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9
           a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
    stroke="{color}" stroke-width="1.8" fill="none"/>
  ```

#### Separator (1px × 22px)

#### More (⋮) menu button
- Tooltip: "More options — about, help, feedback"
- **Icon SVG** (15×15, viewBox 0 0 24 24, fill currentColor):
  ```svg
  <circle cx="12" cy="5" r="1.5" fill="{color}"/>
  <circle cx="12" cy="12" r="1.5" fill="{color}"/>
  <circle cx="12" cy="19" r="1.5" fill="{color}"/>
  ```
- Opens dropdown menu (260px wide, border-radius 10px, bg `topBarBg`):
  - About Speech Bubble Editor (desc: "v3 · Long Weekend Labs")
  - Release Notes (desc: "What's new in this version")
  - Help & Documentation (desc: "Keyboard shortcuts, tutorials")
  - --- separator ---
  - Send Feedback (desc: "Report a bug or request a feature")
  - View on GitHub (desc: "longweekendlabs/speech-bubble-editor")
  - --- separator ---
  - Check for Updates (desc: "You are on the latest version")

---

## 4. ContextToolbar

**Height:** 38px | **Background:** `sectionBg` | **Border-bottom:** 1px `{accent}50`  
**Visibility:** Hidden by default. Show when any BubbleItem or MediaItem is selected. Animate: slide down 150ms ease.

### Selection chip (leftmost, margin-right 10px)
- Padding: 3px 10px | Border-radius: 5px
- Background: `{accent}20` | Border: 1px `{accent}60`
- Mini bubble SVG (12×12):
  ```svg
  <svg viewBox="0 0 12 12" fill="none">
    <ellipse cx="6" cy="5" rx="5" ry="3" fill="{accent}" fill-opacity="0.4" stroke="{accent}" stroke-width="1.2"/>
    <path d="M4.5 7.5L3 10 5.5 8.5" fill="{accent}" stroke="{accent}" stroke-width="0.9" stroke-linejoin="round"/>
  </svg>
  ```
- Text: "Bubble selected" — 11px, weight 600, color: accent
- When media layer selected: "Layer selected"

### Icon buttons (28×26px each, border-radius 5px)
- Default: transparent bg, no border
- Hover: bg `btnHover` + border 1px `inputBorder`
- Danger (delete): hover bg `#f8717122` + border `#f8717160`

All icons below are 14×14px, viewBox `0 0 14 14`.

#### Align Left
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="0" y="2" width="2" height="10" rx="1"/>
  <rect x="2" y="3" width="7" height="3.5" rx="1"/>
  <rect x="2" y="7.5" width="10" height="3.5" rx="1"/>
</svg>
```
Tooltip: "Align left edge to canvas"

#### Align Center Horizontal
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="6" y="2" width="2" height="10" rx="1"/>
  <rect x="2" y="3" width="10" height="3.5" rx="1"/>
  <rect x="3" y="7.5" width="8" height="3.5" rx="1"/>
</svg>
```
Tooltip: "Center horizontally on canvas"

#### Align Right
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="12" y="2" width="2" height="10" rx="1"/>
  <rect x="5" y="3" width="7" height="3.5" rx="1"/>
  <rect x="2" y="7.5" width="10" height="3.5" rx="1"/>
</svg>
```
Tooltip: "Align right edge to canvas"

#### Align Top
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="2" y="0" width="10" height="2" rx="1"/>
  <rect x="3" y="2" width="3.5" height="7" rx="1"/>
  <rect x="7.5" y="2" width="3.5" height="10" rx="1"/>
</svg>
```
Tooltip: "Align top edge to canvas"

#### Align Center Vertical
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="2" y="6" width="10" height="2" rx="1"/>
  <rect x="3" y="2" width="3.5" height="10" rx="1"/>
  <rect x="7.5" y="1" width="3.5" height="12" rx="1"/>
</svg>
```
Tooltip: "Center vertically on canvas"

#### Align Bottom
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="2" y="12" width="10" height="2" rx="1"/>
  <rect x="3" y="5" width="3.5" height="7" rx="1"/>
  <rect x="7.5" y="2" width="3.5" height="10" rx="1"/>
</svg>
```
Tooltip: "Align bottom edge to canvas"

#### Separator (1px × 18px, color `panelBorder`, margin 0 4px)

#### Bring to Front
```svg
<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
  <rect x="1" y="4" width="7" height="7" rx="1" stroke-dasharray="2 1.5"/>
  <rect x="5" y="1" width="8" height="8" rx="1" fill="currentColor" fill-opacity="0.25"/>
  <path d="M11 0v3M11 0L9.5 2M11 0l1.5 2"/>
</svg>
```
Tooltip: "Bring to front — above all layers"

#### Bring Forward
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="1" y="4" width="7" height="7" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/>
  <rect x="5" y="1" width="7" height="7" rx="1" fill-opacity="0.35"/>
  <path d="M11.5 0l-1.5 2.5 1.5 2.5V0z" fill-opacity="0.8"/>
</svg>
```
Tooltip: "Bring forward — one layer up"

#### Send Backward
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="5" y="1" width="7" height="7" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/>
  <rect x="1" y="4" width="7" height="7" rx="1" fill-opacity="0.35"/>
  <path d="M2.5 14l1.5-2.5L2.5 9v5z" fill-opacity="0.8"/>
</svg>
```
Tooltip: "Send backward — one layer down"

#### Send to Back
```svg
<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
  <rect x="5" y="1" width="8" height="8" rx="1" stroke-dasharray="2 1.5"/>
  <rect x="1" y="4" width="7" height="7" rx="1" fill="currentColor" fill-opacity="0.25"/>
</svg>
```
Tooltip: "Send to back — behind all layers"

#### Separator

#### Flip Horizontal
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="6.5" y="1" width="1" height="12" rx="0.5"/>
  <path d="M5.5 4L1 7l4.5 3V4z" fill-opacity="0.9"/>
  <path d="M8.5 4L13 7l-4.5 3V4z" fill-opacity="0.5"/>
</svg>
```
Tooltip: "Flip horizontal"

#### Flip Vertical
```svg
<svg viewBox="0 0 14 14" fill="currentColor">
  <rect x="1" y="6.5" width="12" height="1" rx="0.5"/>
  <path d="M4 5.5L7 1l3 4.5H4z" fill-opacity="0.9"/>
  <path d="M4 8.5L7 13l3-4.5H4z" fill-opacity="0.5"/>
</svg>
```
Tooltip: "Flip vertical"

#### Separator

#### Delete (danger — color `#f87171`)
```svg
<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 3.5h12M5 3.5V2h4v1.5M2.5 3.5L3.5 12h7l1-8.5M5.5 6v4M8.5 6v4"/>
</svg>
```
Tooltip: "Delete selected bubble  (Del)"

---

## 5. ToolSidebar

**Width:** 80px fixed | **Background:** `sidebarBg` | **Border-right:** 1px `panelBorder`  
**Padding:** 12px top, 8px bottom | **Gap between tools:** 2px

### Tool button specs
- Size: (sidebarWidth - 14)px × 56px = **66 × 56px**
- Border-radius: 8px
- Layout: column, center, gap 5px
- Default: transparent bg, transparent border
- Hover: bg `btnHover`
- Active/checked: bg `btnActive`, border 1px `inputBorder`, color accent
- **Active indicator:** 3px wide bar on left edge, height 60% of button, border-radius 0 2px 2px 0, color accent
- Disabled: opacity 0.3

### Icon size: 20×20px | Label: 9.5px, weight 500 (active: 600)

All icons below viewBox `0 0 20 20`.

---

### Select tool
Tooltip: "Select items  (V)" | Shortcut: V
```svg
<svg viewBox="0 0 20 20" fill="none">
  <path d="M4 2L4 14L7.5 11L9.5 17L11.5 16.2L9.5 10.2L14 10L4 2Z"
    fill="{color}" stroke="{color}" stroke-width="0.5" stroke-linejoin="round"/>
</svg>
```
> Arrow cursor shape pointing top-left. Solid filled triangle with notch for arrow tip.

---

### Move tool
Tooltip: "Move selected item  (M)" | Shortcut: M
```svg
<svg viewBox="0 0 20 20" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10 2v16M2 10h16"/>
  <path d="M10 2L8 5M10 2L12 5"/>
  <path d="M10 18L8 15M10 18L12 15"/>
  <path d="M2 10L5 8M2 10L5 12"/>
  <path d="M18 10L15 8M18 10L15 12"/>
</svg>
```
> Plus/cross shape with arrowheads on all 4 ends.

---

### Bubble tool
Tooltip: "Add Speech Bubble  (Ctrl+B)" | Shortcut: Ctrl+B
```svg
<svg viewBox="0 0 20 20" fill="none">
  <ellipse cx="10" cy="8.5" rx="8" ry="5.5"
    fill="{color}" opacity="0.15" stroke="{color}" stroke-width="1.5"/>
  <path d="M7 13.5L5 17.5L9.5 14"
    fill="{color}" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
</svg>
```
> Oval bubble with a pointed tail coming off the bottom-left. Fill is 15% opacity of the icon color.

---

### Caption tool
Tooltip: "Add Caption Bar  (C)" | Shortcut: C
```svg
<svg viewBox="0 0 20 20" fill="none">
  <rect x="1.5" y="5" width="17" height="10" rx="3"
    fill="{color}" opacity="0.12" stroke="{color}" stroke-width="1.5"/>
  <line x1="5" y1="8.5" x2="15" y2="8.5" stroke="{color}" stroke-width="1.3" stroke-linecap="round"/>
  <line x1="5" y1="11.5" x2="12" y2="11.5" stroke="{color}" stroke-width="1.3" stroke-linecap="round"/>
</svg>
```
> Rounded rectangle with two text lines inside. Second line is shorter (paragraph indent implied).

---

### Text tool
Tooltip: "Add Text Overlay  (T)" | Shortcut: T
```svg
<svg viewBox="0 0 20 20" fill="none">
  <path d="M3 4.5H17M10 4.5V16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <line x1="7" y1="16" x2="13" y2="16" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
</svg>
```
> Horizontal bar (crossbar of T), vertical stem, short baseline at bottom.

---

### Layers tool
Tooltip: "Add Overlay Layer  (Ctrl+L)" | Shortcut: Ctrl+L
```svg
<svg viewBox="0 0 20 20" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 14l8 4 8-4"/>
  <path d="M2 10l8 4 8-4"/>
  <path d="M2 6l8-4 8 4-8 4-8-4z"/>
</svg>
```
> Three stacked diamond/chevron shapes — classic layers icon.

---

### Meme Mode tool
Tooltip: "Meme Mode — top/bottom caption bars"
```svg
<svg viewBox="0 0 20 20" fill="none">
  <rect x="2" y="2" width="16" height="16" rx="1.5"
    fill="{color}" opacity="0.1" stroke="{color}" stroke-width="1.5"/>
  <line x1="5" y1="5.5" x2="15" y2="5.5" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
  <line x1="6.5" y1="8" x2="13.5" y2="8" stroke="{color}" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>
  <line x1="5" y1="14.5" x2="15" y2="14.5" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>
  <line x1="6.5" y1="12" x2="13.5" y2="12" stroke="{color}" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>
</svg>
```
> Photo frame with 2 bold text lines near top and 2 near bottom. Thicker primary line, thinner secondary line = "TOP TEXT / BOTTOM TEXT" meme format.

---

### Dual Mode tool
Tooltip: "Dual Mode — side-by-side media"
```svg
<svg viewBox="0 0 20 20" fill="none">
  <rect x="1.5" y="3.5" width="7" height="13" rx="1"
    fill="{color}" opacity="0.12" stroke="{color}" stroke-width="1.5"/>
  <rect x="11.5" y="3.5" width="7" height="13" rx="1"
    fill="{color}" opacity="0.12" stroke="{color}" stroke-width="1.5"/>
</svg>
```
> Two plain side-by-side portrait rectangles. Nothing inside. Simple and clear.

### Collapse sidebar button (bottom)
- Size: 64×28px | Border: 1px `inputBorder` | Border-radius: 6px
- Text: "«" | Color: `textMuted`

---

## 6. Inspector — Section Chrome

### Tab bar
- Two tabs: "Inspector" and "Layers"
- Height: 40px | Background: `topBarBg`
- Active tab: border-bottom 2px accent, font-weight 600, color `textPrimary`
- Inactive tab: color `textSecondary`, border-bottom 2px transparent

### Section header (height 32px each)
Layout: flex row, padding 0 10px 0 14px, gap 6px

**Chevron button** (16×16px, object name `SectionChevron`):
- Border-radius: 4px
- **Open state:** bg `{accent}18`, border 1px `{accent}40`
- **Closed state:** bg `inputBg`, border 1px `inputBorder`
- Arrow SVG (8×8, viewBox 0 0 8 8):
  - **Open (pointing down):** `<path d="M1 3l3 3 3-3" stroke="{accent}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`
  - **Closed (pointing right):** `<path d="M3 1l3 3-3 3" stroke="{textMuted}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`

**Section title:** 9.5px, weight 700, letter-spacing 0.1em
- Open: color `textPrimary`
- Closed: color `textSecondary`

**Section body:** padding 4px 14px 12px, spacing 8px

---

## 7. Inspector — Bubble Style Picker

**Location:** BUBBLE section body  
**Layout:** Flex wrap row, gap 5px, then label beneath

7 buttons total, each 46×46px, border-radius 8px.  
**Active:** bg `{accent}18`, border 2px accent, stroke color = accent  
**Inactive:** bg `inputBg`, border 2px `inputBorder`, stroke color = `textSecondary`  
**Style name label** below row: 10px, color `textMuted`, centered

All preview SVGs below use `viewBox="0 0 48 48"`, rendered at 36×36px inside the button.  
`{color}` = accent when active, `textSecondary` when inactive.  
`{color}33` = that color at ~20% opacity. `{color}25` = ~15% opacity. `{color}44` = ~27% opacity.

---

### 1. Oval — "Speech"
```svg
<svg viewBox="0 0 48 48">
  <!-- Organic oval body — bezier approximation of bubble.py _organic_oval_path() -->
  <path d="M24,6 C34.5,6 42,12 42,20 C42,28 34.5,34 24,34 C13.5,34 6,28 6,20 C6,12 13.5,6 24,6 Z"
    fill="{color}33" stroke="{color}" stroke-width="2"/>
  <!-- Tail — triangular wedge pointing bottom-left, matches _triangle_tail_path() -->
  <path d="M16,32 L10,44 L22,30"
    fill="{color}33" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
</svg>
```

---

### 2. Cloud — "Cloud"
```svg
<svg viewBox="0 0 48 48">
  <!-- Cloud bumps united into one silhouette — matches _cloud_path() with 9 bumps -->
  <path d="M8,28 C5,28 4,24 7,22 C5,18 9,15 12,17 C13,13 17,11 20,14
            C21,10 26,9 28,13 C31,11 35,13 34,17 C37,17 40,20 38,23
            C40,25 39,29 36,29 C35,32 32,33 30,31 C28,34 23,34 22,31
            C19,33 15,32 14,29 C11,30 8,29 8,28 Z"
    fill="{color}33" stroke="{color}" stroke-width="2"/>
  <!-- Thought dots — 3 circles descending toward bottom-left, matches _thought_dots_path() -->
  <circle cx="16" cy="36" r="2.5" fill="{color}"/>
  <circle cx="12" cy="41" r="1.8" fill="{color}"/>
  <circle cx="9"  cy="45" r="1.2" fill="{color}"/>
</svg>
```

---

### 3. Rectangle — "Rectangle"
```svg
<svg viewBox="0 0 48 48">
  <!-- Rounded rect — matches addRoundedRect(r, 16, 16), rx=6 at this scale -->
  <rect x="4" y="10" width="40" height="24" rx="6" ry="6"
    fill="{color}33" stroke="{color}" stroke-width="2"/>
  <!-- Tail bottom-left -->
  <path d="M12,34 L7,44 L20,34"
    fill="{color}33" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
</svg>
```

---

### 4. Starburst — "Starburst" (MANGA ACTION BUBBLE)
```svg
<svg viewBox="0 0 48 48">
  <!--
    12-spike manga action burst.
    Generated via: 12 spikes, outer radii [23,19,22,18,23,20,23,19,22,18,23,20],
    inner radius 12, center (24,24). stroke-linejoin="miter" for sharp spike tips.
    DO NOT USE a uniform star polygon — it looks like SPQR/gear. Use these exact points.
  -->
  <path d="M24.0,1.0 L27.1,12.4 L33.5,7.5 L32.5,15.5 L43.1,13.0 L35.6,20.9
           L42.0,24.0 L35.6,27.1 L43.9,35.5 L32.5,32.5 L34.0,41.3 L27.1,35.6
           L24.0,47.0 L20.9,35.6 L14.5,40.5 L15.5,32.5 L4.9,35.0 L12.4,27.1
           L6.0,24.0 L12.4,20.9 L4.1,12.5 L15.5,15.5 L14.0,6.7 L20.9,12.4 Z"
    fill="{color}25" stroke="{color}" stroke-width="1.5" stroke-linejoin="miter"/>
</svg>
```

---

### 5. Text only — "Text only"
```svg
<svg viewBox="0 0 48 48">
  <!-- Large bold T — serif font renders better at small sizes -->
  <text x="24" y="32" text-anchor="middle" font-size="28" font-weight="bold"
    fill="{color}" font-family="serif">T</text>
  <!-- Dashed bounding box — indicates "no visible bubble shell" -->
  <rect x="7" y="8" width="34" height="32" rx="2"
    fill="none" stroke="{color}" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.5"/>
</svg>
```

---

### 6. Scrim — "Scrim"
```svg
<svg viewBox="0 0 48 48">
  <!-- Full-width dark strip — sharp corners (not rounded), matches addRect() in scrim style -->
  <rect x="2" y="16" width="44" height="16"
    fill="{color}44" stroke="{color}" stroke-width="2"/>
  <!-- Text line hints inside strip -->
  <line x1="9"  y1="22" x2="39" y2="22" stroke="{color}" stroke-width="1.5" opacity="0.5"/>
  <line x1="14" y1="27" x2="34" y2="27" stroke="{color}" stroke-width="1"   opacity="0.3"/>
</svg>
```

---

### 7. Caption — "Caption"
```svg
<svg viewBox="0 0 48 48">
  <!--
    Stroke-text overlay style. "Aa" with outline effect = paint-order: stroke then fill.
    In SVG: draw stroke version first (thicker, in border color), then fill on top.
  -->
  <text x="24" y="30" text-anchor="middle" font-size="20" font-weight="bold"
    font-family="sans-serif"
    stroke="{color}" stroke-width="3" fill="white" paint-order="stroke"
    letter-spacing="1">Aa</text>
  <!-- Subtle dashed bounding hint -->
  <rect x="4" y="12" width="40" height="24" rx="2"
    fill="none" stroke="{color}" stroke-width="1" opacity="0.3" stroke-dasharray="2,3"/>
</svg>
```

---

## 8. Inspector — Typography Alignment Buttons

4 buttons, each 28×28px, border-radius 4px, object name `AlignButton`.  
**Active:** bg `{accent}22`, border 1px accent, color accent  
**Inactive:** bg `inputBg`, border 1px `inputBorder`, color `textSecondary`

All icons: 13×13px, viewBox `0 0 16 16`, stroke only.

#### Align Left — tooltip "Align text left"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
  <line x1="1" y1="4"   x2="15" y2="4"/>
  <line x1="1" y1="7.5" x2="10" y2="7.5"/>
  <line x1="1" y1="11"  x2="13" y2="11"/>
</svg>
```
> Three lines all anchored to the LEFT. Short middle line makes left-align obvious.

#### Align Center — tooltip "Center text"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
  <line x1="1"   y1="4"   x2="15"   y2="4"/>
  <line x1="3.5" y1="7.5" x2="12.5" y2="7.5"/>
  <line x1="1.5" y1="11"  x2="14.5" y2="11"/>
</svg>
```
> Three lines centered. Middle line is shortest and visibly centered.

#### Align Right — tooltip "Align text right"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
  <line x1="1"  y1="4"   x2="15" y2="4"/>
  <line x1="6"  y1="7.5" x2="15" y2="7.5"/>
  <line x1="3"  y1="11"  x2="15" y2="11"/>
</svg>
```
> Three lines all anchored to the RIGHT. Short middle line starts further right.

#### Justify — tooltip "Justify text"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
  <line x1="1" y1="4"   x2="15" y2="4"/>
  <line x1="1" y1="7.5" x2="15" y2="7.5"/>
  <line x1="1" y1="11"  x2="15" y2="11"/>
</svg>
```
> All three lines span full width — justified.

---

## 9. Inspector — All Other Sections

### TEXT section
- Char counter: top-right, `{n} / 200`, 10px, `textMuted`
- QTextEdit: height 80px, bg `inputBg`, border `inputBorder`, border-radius 6px, padding 8px 10px, font 13px
- Placeholder: "Type bubble text here…"
- Max 200 chars — enforce in textChanged handler

### COLORS section
Each color row: `Label (54px min-width)` + `color swatch QPushButton (30×24px)` + `hex label`
- Fill: tooltip "Bubble fill color — click to pick"
- Stroke: tooltip "Bubble outline/stroke color"

### TYPOGRAPHY section
Row 1: Font family QFontComboBox (flex 1, height 32px, tooltip "Font family") + Weight QComboBox (90px, options: Regular/Bold/Italic/Bold Italic, tooltip "Font weight")

Row 2: Font size QSpinBox (range 6–96, suffix " px", width 72px, tooltip "Font size in pixels") + Text color QPushButton (28×28px, tooltip "Text color — click to pick") + 4 alignment buttons (see §8)

### TAIL section
- Position: QComboBox full-width, tooltip "Tail attachment position on the bubble"
  Options: Top Left / Top Center / Top Right / Right / Bottom Right / Bottom Center / Bottom Left / Left
- Width: slider row, range 6–80, suffix " px", tooltip "Width of the tail at its base in pixels"

### STROKE section
- Width: QDoubleSpinBox, range 0–12, step 0.5, suffix " px", tooltip "Bubble outline stroke width in pixels"

### SHADOW section (checkable header)
- Checkbox tooltip: "Enable drop shadow"
- Color row: tooltip "Shadow color"
- Blur slider: range 0–40, suffix " px", tooltip "Shadow blur radius in pixels"
- Offset: X spinbox + Y spinbox, range -80–80, prefix "X "/"Y ", suffix " px", tooltips "Shadow horizontal/vertical offset"
- Opacity slider: range 0–100, suffix " %", tooltip "Shadow opacity (0 = invisible, 100 = fully opaque)"

### Slider row layout
`Label (min-width 54px)` + `QSlider (flex 1, accentColor)` + `QSpinBox (width 70px)`
Slider and spinbox stay in sync (bidirectional connect).

---

## 10. Timeline / VideoControls

**Background:** `timelineBg` | **Border-top:** 1px `panelBorder`  
**Visible:** only when video loaded

### Transport row (height 40px, border-bottom 1px `panelBorder`)

All transport buttons: border 1px `inputBorder`, border-radius 5px, bg transparent, hover bg `btnHover`.  
Small buttons: 26×26px. Play/Pause: 34×28px with accent highlight when playing.

#### To Start (26×26) — tooltip "Go to first frame  (Home)"
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <rect x="1" y="2" width="2" height="12" rx="1"/>
  <path d="M14 2.5L5 8l9 5.5V2.5z"/>
</svg>
```

#### Step Back (26×26) — tooltip "Step back one frame  (←)"
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <path d="M11 2.5L2 8l9 5.5V2.5z"/>
  <path d="M10.5 8L7 5.5v5L10.5 8z" opacity="0.4"/>
</svg>
```

#### Play (34×28) — tooltip "Play  (Space)"
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <path d="M3 2.5l10 5.5-10 5.5V2.5z"/>
</svg>
```
When playing: show Pause icon instead, button gets accent border + bg `{accent}22`:
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <rect x="3" y="2" width="3.5" height="12" rx="1"/>
  <rect x="9.5" y="2" width="3.5" height="12" rx="1"/>
</svg>
```

#### Step Forward (26×26) — tooltip "Step forward one frame  (→)"
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <path d="M5 2.5L14 8 5 13.5V2.5z"/>
  <path d="M5.5 8L9 5.5v5L5.5 8z" opacity="0.4"/>
</svg>
```

#### To End (26×26) — tooltip "Go to last frame  (End)"
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <rect x="13" y="2" width="2" height="12" rx="1"/>
  <path d="M2 2.5L11 8 2 13.5V2.5z"/>
</svg>
```

#### Separator (1px × 18px, margin 0 2px)

#### Volume (26×26) — tooltip "Volume"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
  <path d="M3 5.5H1.5v5H3l4 3V2.5L3 5.5z" fill="currentColor" stroke="none"/>
  <path d="M9.5 4.5c1 1 1.5 2.2 1.5 3.5s-.5 2.5-1.5 3.5"/>
  <path d="M12 2.5c1.7 1.5 2.5 3.4 2.5 5.5s-.8 4-2.5 5.5"/>
</svg>
```

#### Timecode display (right of volume slider)
- Font: monospace, 13px, weight 600, color accent, letter-spacing 0.05em
- Format: `MM:SS:FF / MM:SS:FF` (minutes:seconds:frames)

#### Fullscreen (26×26, right-aligned) — tooltip "Toggle fullscreen canvas  (F)"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
  <path d="M1 5V1h4M11 1h4v4M15 11v4h-4M5 15H1v-4"/>
</svg>
```

### Edit bar (height 34px, border-top 1px `panelBorder`)
Buttons: height 24px, padding 0 8px, border 1px `inputBorder`, border-radius 5px, gap 5px between icon and label.

#### Set In — tooltip "Set trim in-point to current frame  ([)"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
  <rect x="1" y="2" width="2" height="12" rx="1" fill="currentColor" stroke="none"/>
  <path d="M3 8h10"/>
  <path d="M10 5l3 3-3 3"/>
</svg>
```

#### Set Out — tooltip "Set trim out-point to current frame  (])"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
  <rect x="13" y="2" width="2" height="12" rx="1" fill="currentColor" stroke="none"/>
  <path d="M13 8H3"/>
  <path d="M6 5L3 8l3 3"/>
</svg>
```

#### Separator (1px × 18px)

#### Cut — tooltip "Cut selected trim range from clip"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
  <circle cx="4" cy="4" r="2"/>
  <circle cx="4" cy="12" r="2"/>
  <path d="M6 5.5L14 9M6 10.5L14 7"/>
</svg>
```

#### Marker — tooltip "Add marker at current frame  (M)"
```svg
<svg viewBox="0 0 16 16" fill="currentColor">
  <path d="M8 1l1.8 5.5H16l-5 3.6 1.9 5.9L8 12.5l-4.9 3.5 1.9-5.9-5-3.6h6.2z" opacity="0.9"/>
</svg>
```

#### Reverse — tooltip "Toggle playback direction (reverse on export)"
```svg
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 8h12"/>
  <path d="M4 4L1 8l3 4"/>
  <path d="M10 4l4 4-4 4" opacity="0.5"/>
</svg>
```

### Scrubber strip (height 28px)
- Background: `scrubberTrack`
- Time ruler marks: 8 divisions, 1px `panelBorder` vertical lines, timestamp labels 9px monospace `textMuted`
- Trim range fill: accent at 15% opacity
- Playhead: 2px wide vertical line, color = `playhead` token (accent or `#7c83ff` in slate)
  - Triangle at top: 10px wide, 8px tall, same color, pointing down
- Clip regions on filmstrip: accent at 30% fill + 1px accent border, timecode label inside

---

## 11. Canvas & Selection Handles

When a bubble is selected:
- Dashed blue outline (1.5px, `rgba(80,130,230,1)`, DashLine) around bubble body rect
- 8 resize handles at corners and edge midpoints (TL/TC/TR/ML/MR/BL/BC/BR):
  - 8×8px squares, white fill, accent border 1px, border-radius 2px
- Red tail handle: circle r=9px, red fill `#dc2828`, white border 2px — drag to repoint tail
- Selection bounding box: 2px solid accent, border-radius 4px, inset -6px from bubble bounds
- In the prototype the handles render as: 8 small accent-colored squares at each resize point

---

## 12. StatusBar

**Height:** 26px | **Background:** `topBarBg` | **Border-top:** 1px `panelBorder`  
**Font:** 11px, color `textMuted`

Left to right (gap 16px):
- "Project:" label + project filename (`textSecondary`)
- Resolution e.g. "1920 × 1080"
- Frame rate e.g. "24 fps"
- Duration e.g. "Duration: 00:00:06:20"
- [flex spacer]
- Autosave indicator: 7×7px circle (`#22c55e`) + "Autosaved just now"

---

## 13. QSS Rules

All rules already exist in `theme/dark.qss`. Key ones for new components:

```css
/* ── ContextToolbar ───────────────────────────────────── */
#ContextToolbar {
    background-color: #1e2535;
    border-bottom: 1px solid rgba(70,221,203,0.3);
}
#ContextChip {
    background-color: rgba(70,221,203,0.15);
    border: 1px solid rgba(70,221,203,0.5);
    border-radius: 5px;
    color: #46ddcb;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
}
#ContextBtn {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    color: #e8ecf4;
    min-width: 0;
    padding: 0;
}
#ContextBtn:hover { background-color: #2a3347; border-color: #2e3a50; }
#ContextDeleteBtn { color: #f87171; }
#ContextDeleteBtn:hover {
    background-color: rgba(248,113,113,0.15);
    border-color: rgba(248,113,113,0.5);
}
#ContextSep { background-color: #252d3d; border: none; }

/* ── Section chevron ──────────────────────────────────── */
#SectionChevron {
    background-color: #252d3d;
    border: 1px solid #2e3a50;
    border-radius: 4px;
    color: #4e5a6e;
    font-size: 8px;
    padding: 0;
    min-width: 0;
}
#SectionChevron[open="true"] {
    background-color: rgba(70,221,203,0.1);
    border-color: rgba(70,221,203,0.25);
    color: #46ddcb;
}

/* ── Style picker ─────────────────────────────────────── */
#StyleButton {
    background-color: #252d3d;
    border: 2px solid #2e3a50;
    border-radius: 8px;
    padding: 0;
    min-width: 0;
}
#StyleButton:checked {
    background-color: rgba(70,221,203,0.12);
    border: 2px solid #46ddcb;
    color: #46ddcb;
}
#StyleButton:hover:!checked { background-color: #2a3347; border-color: #3a4d66; }

/* ── Text align buttons ───────────────────────────────── */
#AlignButton {
    background-color: #252d3d;
    border: 1px solid #2e3a50;
    border-radius: 4px;
    padding: 0; min-width: 0;
}
#AlignButton:checked {
    background-color: rgba(70,221,203,0.15);
    border-color: #46ddcb;
    color: #46ddcb;
}

/* ── Tool sidebar active tool ─────────────────────────── */
#ToolSidebar QToolButton:checked {
    background-color: #2e3d5a;
    border-left: 3px solid #46ddcb;
    border-top: 1px solid #2e3a50;
    border-right: 1px solid #2e3a50;
    border-bottom: 1px solid #2e3a50;
    color: #46ddcb;
}

/* ── Timeline timecode ────────────────────────────────── */
#TimecodeLabel {
    color: #46ddcb;
    font-family: monospace;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.05em;
}
```

For the `oled` and `slate` themes, swap the color values in a second stylesheet string applied at runtime when the user changes theme. All object names (`#ContextToolbar`, `#SectionChevron`, etc.) stay the same — only the color values change.

---

## Files in `pyqt_output/`

| File | Purpose |
|---|---|
| `icons.py` | `make_icon(svg_body, size, color)` → QIcon via QSvgRenderer. All SVG bodies as constants. |
| `top_bar.py` | Full TopBar with SVG icons, zoom dropdown, about menu |
| `tool_sidebar.py` | Tool buttons with SVG icons, accent indicator bar |
| `context_toolbar.py` | Alignment/arrange/delete bar, show/hide API |
| `inspector_dock.py` | Full inspector with chevron sections, 7-style picker, align icons, tooltips |
| `video_controls.py` | Full VideoControls with SVG transport icons |
| `INSTALL.md` | Copy commands and compatibility notes |
