"""
bubble_defaults.py — Persistent "Default Balloon Settings" (Balloon+ style).

Stores the user's preferred look for NEW bubbles in QSettings and applies it
when a BubbleItem is created. The defaults never touch existing bubbles.

Keys are plain Python values (colors stored as #AARRGGBB strings) so the
settings file stays human-readable and portable across platforms.
"""

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor

ORG = "Long Weekend Labs"
APP = "Speech Bubble Editor"

# Factory defaults — must mirror the hardcoded values in BubbleItem.__init__
FACTORY = {
    "style":            "oval",
    "fill":             "#f0ffffff",   # AARRGGBB (alpha 240 white)
    "border":           "#ff141414",
    "border_width":     2.0,
    "text_color":       "#ff0f0f0f",
    "font_family":      "Comic Neue",
    "font_size":        20,
    "font_bold":        True,
    "font_italic":      True,
    "tail_shape":       "wedge",
    "tail_count":       1,
    "tail_width":       40,
    "text_outline_width": 0.0,
    "text_outline_color": "#ff000000",
    "shadow_enabled":   False,
    "shadow_blur":      12,
    "shadow_x":         4,
    "shadow_y":         4,
    "shadow_opacity":   80,
}


def _settings() -> QSettings:
    return QSettings(ORG, APP)


def load() -> dict:
    """Current defaults: factory values overlaid with anything the user saved."""
    s = _settings()
    s.beginGroup("bubble_defaults")
    out = dict(FACTORY)
    for key, factory_val in FACTORY.items():
        if s.contains(key):
            raw = s.value(key)
            if isinstance(factory_val, bool):
                out[key] = raw in (True, "true", "True", 1, "1")
            elif isinstance(factory_val, int):
                out[key] = int(raw)
            elif isinstance(factory_val, float):
                out[key] = float(raw)
            else:
                out[key] = str(raw)
    s.endGroup()
    return out


def save_from_bubble(bubble) -> dict:
    """Capture the given bubble's current look as the new defaults."""
    font = bubble.get_font()
    shadow = bubble.get_shadow()
    values = {
        "style":            bubble.get_style(),
        "fill":             bubble.get_fill_color().name(QColor.NameFormat.HexArgb),
        "border":           bubble.get_border_color().name(QColor.NameFormat.HexArgb),
        "border_width":     float(bubble.get_border_width()),
        "text_color":       bubble.get_text_color().name(QColor.NameFormat.HexArgb),
        "font_family":      font.family(),
        "font_size":        max(6, font.pointSize()),
        "font_bold":        font.bold(),
        "font_italic":      font.italic(),
        "tail_shape":       bubble.get_tail_shape(),
        "tail_count":       bubble.get_tail_count(),
        "tail_width":       bubble.get_tail_width(),
        "text_outline_width": float(bubble.get_text_outline_width()),
        "text_outline_color": bubble.get_text_outline_color().name(QColor.NameFormat.HexArgb),
        "shadow_enabled":   bool(shadow.get("enabled", False)),
        "shadow_blur":      int(shadow.get("blur", 12)),
        "shadow_x":         int(shadow.get("offset_x", 4)),
        "shadow_y":         int(shadow.get("offset_y", 4)),
        "shadow_opacity":   int(shadow.get("opacity", 80)),
    }
    s = _settings()
    s.beginGroup("bubble_defaults")
    for key, val in values.items():
        s.setValue(key, val)
    s.endGroup()
    s.sync()
    return values


def reset():
    """Forget the saved defaults and return to factory values."""
    s = _settings()
    s.remove("bubble_defaults")
    s.sync()


def default_style() -> str:
    return load().get("style", "oval")


def apply_to_bubble(bubble):
    """Apply saved defaults to a freshly created bubble (appearance only).

    Called from BubbleItem.__init__ BEFORE any style-specific overrides, and
    only when the saved defaults differ from factory (cheap no-op otherwise).
    """
    d = load()
    if d == FACTORY:
        return

    from PyQt6.QtGui import QFont

    bubble._fill_color   = QColor(d["fill"])
    bubble._border_color = QColor(d["border"])
    bubble._border_width = float(d["border_width"])
    bubble._tail_shape   = d["tail_shape"]
    bubble._tail_count   = max(0, min(3, int(d["tail_count"])))
    bubble._tail_width   = max(6, int(d["tail_width"]))
    bubble._text_outline_width = float(d["text_outline_width"])
    bubble._text_outline_color = QColor(d["text_outline_color"])
    bubble._shadow.update({
        "enabled":  bool(d["shadow_enabled"]),
        "blur":     int(d["shadow_blur"]),
        "offset_x": int(d["shadow_x"]),
        "offset_y": int(d["shadow_y"]),
        "opacity":  int(d["shadow_opacity"]),
    })
    font = QFont(d["font_family"], int(d["font_size"]))
    font.setBold(bool(d["font_bold"]))
    font.setItalic(bool(d["font_italic"]))
    bubble._font_pt = int(d["font_size"])
    bubble._text_item.setFont(font)
    bubble._text_item.setDefaultTextColor(QColor(d["text_color"]))
