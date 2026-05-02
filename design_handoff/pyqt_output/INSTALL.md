# PyQt6 Output Files — Drop-in Replacements

These files are **ready to copy** into the root of `longweekendlabs/speech-bubble-editor`.
They replace the existing files of the same name.

## Files

| File | Replaces | What changed |
|---|---|---|
| `icons.py` | *(new file)* | SVG icon helper — `make_icon(svg_body, size, color)` returns QIcon |
| `top_bar.py` | `top_bar.py` | SVG icons for Open/Export/Undo/Redo, zoom dropdown with Fit Width/Window, about menu |
| `tool_sidebar.py` | `tool_sidebar.py` | Purpose-built SVG icons per tool, accent left-edge indicator on active tool |
| `context_toolbar.py` | `context_toolbar.py` | Alignment/arrange/delete bar — appears when bubble selected |
| `inspector_dock.py` | `inspector_dock.py` | Visible chevron expand/collapse, 7-style bubble picker, distinct text-align icons, tooltips everywhere, ALIGNMENT section removed (it's now in ContextToolbar) |
| `video_controls.py` | `video_controls.py` | SVG transport icons, play/pause icon swap, tooltips with keyboard shortcuts |

## Install steps

```bash
# From repo root
cp design_handoff/pyqt_output/icons.py .
cp design_handoff/pyqt_output/top_bar.py .
cp design_handoff/pyqt_output/tool_sidebar.py .
cp design_handoff/pyqt_output/context_toolbar.py .
cp design_handoff/pyqt_output/inspector_dock.py .
cp design_handoff/pyqt_output/video_controls.py .
```

## Dependencies

`icons.py` requires `PyQt6-Qt6` with SVG support. Add to `requirements.txt` if not present:
```
PyQt6>=6.4.0
PyQt6-Qt6>=6.4.0
```

`QSvgRenderer` is used in `icons.py` — import is from `PyQt6.QtSvg`. This is included
in the standard PyQt6 install on all platforms.

## QSS — no changes needed

`theme/dark.qss` already contains all required style rules for the new object names:
`#ContextToolbar`, `#ContextChip`, `#ContextBtn`, `#ContextDeleteBtn`, `#ContextSep`,
`#SectionChevron`, `#SectionChevron[open="true"]`, `#StyleButton`, `#AlignButton`.

## Signal compatibility

`main_window.py` (already in repo) connects these signals — all present in the new files:

| Signal | From |
|---|---|
| `ctx_toolbar.align_requested(str)` | `context_toolbar.py` |
| `ctx_toolbar.z_requested(str)` | `context_toolbar.py` |
| `ctx_toolbar.flip_h_requested()` | `context_toolbar.py` |
| `ctx_toolbar.flip_v_requested()` | `context_toolbar.py` |
| `ctx_toolbar.delete_requested()` | `context_toolbar.py` |
| `top_bar.zoom_changed(object)` | `top_bar.py` |
| `tool_sidebar.add_bubble_requested()` | `tool_sidebar.py` |
| `tool_sidebar.add_layer_requested()` | `tool_sidebar.py` |
| `tool_sidebar.meme_toggled(bool)` | `tool_sidebar.py` |
| `tool_sidebar.dual_toggled(bool)` | `tool_sidebar.py` |

## Notes

- `tool_sidebar.py` no longer has `add_caption_requested` or `add_text_requested` signals.
  If `main_window.py` connects these, either add them to `tool_sidebar.py` or remove the
  connections (caption/text tools launch a bubble with style override via double-click).
- `top_bar.py` emits `zoom_changed(object)` — value is `int` (percent) or `str`
  (`"fit-width"` / `"fit-window"`). Handle in `_on_zoom_level` in `main_window.py`.
- The `icons.py` SVG bodies use a `{color}` placeholder — always pass a hex color string
  to `make_icon()`, never `None`.
