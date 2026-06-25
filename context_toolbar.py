"""
context_toolbar.py — ContextToolbar: dynamic bar shown when a bubble/item is selected.

Sits between TopBar and the canvas content area. Provides:
  - Alignment (left/hcenter/right/top/vcenter/bottom)
  - Layer order (bring to front/forward/backward/back)
  - Transform (flip H/V — UI only, handler is no-op until implemented)
  - Delete

Signal names match what main_window.py expects:
  align_requested(str)     — "left"|"hcenter"|"right"|"top"|"vcenter"|"bottom"
  z_requested(str)         — "front"|"forward"|"backward"|"back"
  flip_h_requested()
  flip_v_requested()
  delete_requested()

Visibility API:
  show_for_bubble()
  show_for_media()
  hide_toolbar()
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QColor

from icons import (
    make_icon, ACCENT, FG, MUTED, DANGER,
    ICON_ALIGN_LEFT, ICON_ALIGN_HCENTER, ICON_ALIGN_RIGHT,
    ICON_ALIGN_TOP, ICON_ALIGN_VCENTER, ICON_ALIGN_BOTTOM,
    ICON_TO_FRONT, ICON_BRING_FWD, ICON_SEND_BACK, ICON_TO_BACK,
    ICON_FLIP_H, ICON_FLIP_V, ICON_DELETE,
)


class ContextToolbar(QWidget):

    align_requested  = pyqtSignal(str)   # "left"|"hcenter"|"right"|"top"|"vcenter"|"bottom"
    z_requested      = pyqtSignal(str)   # "front"|"forward"|"backward"|"back"
    flip_h_requested = pyqtSignal()
    flip_v_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContextToolbar")
        self.setFixedHeight(38)
        self._action_widgets = []
        self._build_ui()
        self.hide_toolbar()

    # ------------------------------------------------------------------

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(2)

        # ── Selection chip ─────────────────────────────────────────────
        self._chip = QLabel("Bubble selected")
        self._chip.setObjectName("ContextChip")
        self._chip.setFixedHeight(24)
        lay.addWidget(self._chip)
        lay.addSpacing(10)

        # ── Alignment group ────────────────────────────────────────────
        ALIGN = [
            (ICON_ALIGN_LEFT,    "left",    "Align left edge to canvas"),
            (ICON_ALIGN_HCENTER, "hcenter", "Center horizontally on canvas"),
            (ICON_ALIGN_RIGHT,   "right",   "Align right edge to canvas"),
            (ICON_ALIGN_TOP,     "top",     "Align top edge to canvas"),
            (ICON_ALIGN_VCENTER, "vcenter", "Center vertically on canvas"),
            (ICON_ALIGN_BOTTOM,  "bottom",  "Align bottom edge to canvas"),
        ]
        for svg, mode, tip in ALIGN:
            btn = self._ctx_btn(svg, tip)
            btn.clicked.connect(lambda _, m=mode: self.align_requested.emit(m))
            self._action_widgets.append(btn)
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        # ── Layer order ────────────────────────────────────────────────
        ORDER = [
            (ICON_TO_FRONT,  "front",    "Bring to front — above all layers"),
            (ICON_BRING_FWD, "forward",  "Bring forward — one layer up"),
            (ICON_SEND_BACK, "backward", "Send backward — one layer down"),
            (ICON_TO_BACK,   "back",     "Send to back — behind all layers"),
        ]
        for svg, mode, tip in ORDER:
            btn = self._ctx_btn(svg, tip)
            btn.clicked.connect(lambda _, m=mode: self.z_requested.emit(m))
            self._action_widgets.append(btn)
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        # ── Transform ─────────────────────────────────────────────────
        flip_h_btn = self._ctx_btn(ICON_FLIP_H, "Flip horizontal")
        flip_h_btn.clicked.connect(self.flip_h_requested)
        self._action_widgets.append(flip_h_btn)
        lay.addWidget(flip_h_btn)

        flip_v_btn = self._ctx_btn(ICON_FLIP_V, "Flip vertical")
        flip_v_btn.clicked.connect(self.flip_v_requested)
        self._action_widgets.append(flip_v_btn)
        lay.addWidget(flip_v_btn)

        lay.addWidget(self._sep())

        # ── Delete ────────────────────────────────────────────────────
        del_btn = self._ctx_btn(ICON_DELETE, "Delete selected bubble  (Del)",
                                danger=True)
        del_btn.setObjectName("ContextDeleteBtn")
        del_btn.clicked.connect(self.delete_requested)
        self._action_widgets.append(del_btn)
        lay.addWidget(del_btn)

        lay.addStretch()

    # ------------------------------------------------------------------

    def _ctx_btn(self, svg: str, tip: str, danger: bool = False) -> QPushButton:
        color = DANGER if danger else FG
        btn = QPushButton()
        btn.setObjectName("ContextDeleteBtn" if danger else "ContextBtn")
        btn.setIcon(make_icon(svg, 20, color))
        btn.setIconSize(QSize(18, 18))
        btn.setFixedSize(30, 26)
        btn.setToolTip(tip)
        btn.setFlat(True)
        return btn

    def _sep(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("ContextSep")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedSize(1, 18)
        return sep

    # ------------------------------------------------------------------
    # Public visibility API (called by main_window.py)
    # ------------------------------------------------------------------

    def show_for_bubble(self):
        self._chip.setText("Bubble selected")
        self._set_actions_enabled(True)

    def show_for_media(self):
        self._chip.setText("Layer selected")
        self._set_actions_enabled(True)

    def hide_toolbar(self):
        self._chip.setText("No selection")
        self._set_actions_enabled(False)

    def _set_actions_enabled(self, enabled: bool):
        for widget in self._action_widgets:
            widget.setEnabled(enabled)
