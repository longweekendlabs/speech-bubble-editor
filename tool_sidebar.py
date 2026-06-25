"""
tool_sidebar.py — ToolSidebar: vertical icon strip on the left edge (v4 redesign).

Each tool button shows a purpose-built SVG icon above its label.
Active tool gets an accent-coloured left-edge indicator bar via QSS.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QKeySequence

from icons import (
    make_icon, make_icon_pair, ACCENT, MUTED,
    ICON_SELECT, ICON_MOVE, ICON_BUBBLE,
    ICON_TEXT, ICON_LAYERS, ICON_MEME, ICON_DUAL,
)

# (id, label, normal_svg, shortcut_or_none, checkable, in_tool_group)
TOOL_DEFS = [
    ("select",  "Select",  ICON_SELECT,  "V",      True,  True),
    ("move",    "Move",    ICON_MOVE,    "M",      True,  True),
    ("bubble",  "Bubble",  ICON_BUBBLE,  "Ctrl+B", False, False),
    ("text",    "Text",    ICON_TEXT,    "T",      False, False),
    ("layers",  "Layers",  ICON_LAYERS,  "Ctrl+L", False, False),
    ("meme",    "Meme",    ICON_MEME,    None,     True,  False),
    ("dual",    "Dual",    ICON_DUAL,    None,     True,  False),
]

MEDIA_GATED = {"bubble", "text", "layers", "meme", "dual"}


class ToolSidebar(QWidget):

    add_bubble_requested = pyqtSignal()
    add_text_requested   = pyqtSignal()
    add_layer_requested  = pyqtSignal()
    meme_toggled         = pyqtSignal(bool)
    dual_toggled         = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(80)
        self.setObjectName("ToolSidebar")
        self._buttons: dict[str, QToolButton] = {}
        self._build_ui()

    # ------------------------------------------------------------------

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 14, 8, 10)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        for tool_id, label, svg, shortcut, checkable, in_group in TOOL_DEFS:
            btn = self._make_tool_btn(tool_id, label, svg, shortcut, checkable)
            self._buttons[tool_id] = btn

            if in_group:
                self._tool_group.addButton(btn)
            lay.addWidget(btn)

        # Wire non-group actions
        self._buttons["bubble"].clicked.connect(self.add_bubble_requested)
        self._buttons["text"].clicked.connect(self.add_text_requested)
        self._buttons["layers"].clicked.connect(self.add_layer_requested)
        self._buttons["meme"].toggled.connect(self.meme_toggled)
        self._buttons["dual"].toggled.connect(self.dual_toggled)

        # Default: Select checked
        self._buttons["select"].setChecked(True)

        lay.addStretch()

        # Collapse button
        collapse = QToolButton()
        collapse.setObjectName("SidebarCollapse")
        collapse.setText("«")
        collapse.setFixedSize(60, 28)
        collapse.setToolTip("Collapse sidebar")
        lay.addWidget(collapse)

    def _make_tool_btn(self, tool_id: str, label: str, svg: str,
                       shortcut: str | None, checkable: bool) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName(f"ToolBtn_{tool_id}")
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setText(label)
        btn.setFixedSize(64, 56)
        btn.setIconSize(QSize(20, 20))
        btn.setCheckable(checkable)

        # Normal and accent icons
        icon_normal, icon_accent = make_icon_pair(svg, 20)
        btn.setIcon(icon_normal)
        btn._icon_normal = icon_normal   # type: ignore[attr-defined]
        btn._icon_accent = icon_accent   # type: ignore[attr-defined]

        if shortcut:
            btn.setShortcut(QKeySequence(shortcut))

        # Tooltip with shortcut hint
        tip = label
        if shortcut:
            tip += f"  ({shortcut})"
        btn.setToolTip(tip)

        # Swap icon on check state change
        if checkable:
            btn.toggled.connect(
                lambda checked, b=btn: b.setIcon(
                    b._icon_accent if checked else b._icon_normal   # type: ignore[attr-defined]
                )
            )

        return btn

    # ------------------------------------------------------------------
    # Public API (mirrors v3 ToolSidebar)
    # ------------------------------------------------------------------

    def set_media_loaded(self, loaded: bool):
        for tool_id in MEDIA_GATED:
            btn = self._buttons.get(tool_id)
            if btn:
                btn.setEnabled(loaded)

    def set_meme_checked(self, checked: bool):
        btn = self._buttons["meme"]
        btn.blockSignals(True)
        btn.setChecked(checked)
        btn.setIcon(btn._icon_accent if checked else btn._icon_normal)   # type: ignore[attr-defined]
        btn.blockSignals(False)

    def set_dual_checked(self, checked: bool):
        btn = self._buttons["dual"]
        btn.blockSignals(True)
        btn.setChecked(checked)
        btn.setIcon(btn._icon_accent if checked else btn._icon_normal)   # type: ignore[attr-defined]
        btn.blockSignals(False)

    def set_meme_enabled(self, enabled: bool):
        self._buttons["meme"].setEnabled(enabled)

    def set_dual_enabled(self, enabled: bool):
        self._buttons["dual"].setEnabled(enabled)
