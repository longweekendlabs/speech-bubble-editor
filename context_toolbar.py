"""
context_toolbar.py — ContextToolbar: selection-sensitive action strip.
Shown below TopBar when a BubbleItem or MediaItem is selected.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import pyqtSignal


class ContextToolbar(QWidget):
    align_requested  = pyqtSignal(str)   # left | hcenter | right | top | vcenter | bottom
    z_requested      = pyqtSignal(str)   # front | forward | backward | back
    flip_h_requested = pyqtSignal()
    flip_v_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContextToolbar")
        self.setFixedHeight(38)
        self._build_ui()
        self.setVisible(False)

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(2)

        # Selection chip
        self._chip = QLabel("◉  Bubble selected")
        self._chip.setObjectName("ContextChip")
        lay.addWidget(self._chip)
        lay.addSpacing(8)

        # Alignment group (6 buttons)
        for icon, arg, tip in [
            ("⊢", "left",    "Align left edge to canvas"),
            ("↔", "hcenter", "Center horizontally on canvas"),
            ("⊣", "right",   "Align right edge to canvas"),
            ("⊤", "top",     "Align top edge to canvas"),
            ("↕", "vcenter", "Center vertically on canvas"),
            ("⊥", "bottom",  "Align bottom edge to canvas"),
        ]:
            btn = self._ctx_btn(icon, tip)
            btn.clicked.connect(lambda _c=False, a=arg: self.align_requested.emit(a))
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        # Z-order group (4 buttons)
        for icon, arg, tip in [
            ("▲▲", "front",    "Bring to front — above all layers"),
            ("▲",       "forward",  "Bring forward — one layer up"),
            ("▼",       "backward", "Send backward — one layer down"),
            ("▼▼", "back",     "Send to back — behind all layers"),
        ]:
            btn = self._ctx_btn(icon, tip)
            btn.clicked.connect(lambda _c=False, a=arg: self.z_requested.emit(a))
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        # Flip group (2 buttons)
        btn_fh = self._ctx_btn("⇔", "Flip horizontal")
        btn_fh.clicked.connect(self.flip_h_requested)
        lay.addWidget(btn_fh)

        btn_fv = self._ctx_btn("⇕", "Flip vertical")
        btn_fv.clicked.connect(self.flip_v_requested)
        lay.addWidget(btn_fv)

        lay.addWidget(self._sep())

        # Delete button
        btn_del = self._ctx_btn("✕", "Delete selected item  (Del)")
        btn_del.setObjectName("ContextDeleteBtn")
        btn_del.clicked.connect(self.delete_requested)
        lay.addWidget(btn_del)

        lay.addStretch()

    def _ctx_btn(self, text: str, tip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("ContextBtn")
        btn.setFixedSize(28, 26)
        btn.setToolTip(tip)
        return btn

    def _sep(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("ContextSep")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedSize(1, 18)
        return sep

    def show_for_bubble(self):
        self._chip.setText("◉  Bubble selected")
        self.setVisible(True)

    def show_for_media(self):
        self._chip.setText("◉  Layer selected")
        self.setVisible(True)

    def hide_toolbar(self):
        self.setVisible(False)
