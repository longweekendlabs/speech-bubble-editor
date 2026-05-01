"""
tool_sidebar.py — ToolSidebar: vertical icon strip on the left edge.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QFrame
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence


def _icon_btn(text: str, tip: str, checkable: bool = False) -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tip)
    btn.setCheckable(checkable)
    btn.setFixedSize(44, 44)
    return btn


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    f.setFixedHeight(1)
    return f


class ToolSidebar(QWidget):

    add_bubble_requested = pyqtSignal()
    add_layer_requested  = pyqtSignal()
    meme_toggled         = pyqtSignal(bool)
    dual_toggled         = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(52)
        self.setObjectName("ToolSidebar")
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._btn_select = _icon_btn("↖", "Select  (V)", checkable=True)
        self._btn_select.setChecked(True)
        lay.addWidget(self._btn_select)

        lay.addWidget(_sep())

        self._btn_bubble = _icon_btn("💬", "Add Speech Bubble  (Ctrl+B)")
        self._btn_bubble.setShortcut(QKeySequence("Ctrl+B"))
        self._btn_bubble.setEnabled(False)
        self._btn_bubble.clicked.connect(self.add_bubble_requested)
        lay.addWidget(self._btn_bubble)

        self._btn_layer = _icon_btn("⊕", "Add Overlay Layer  (Ctrl+L)")
        self._btn_layer.setShortcut(QKeySequence("Ctrl+L"))
        self._btn_layer.setEnabled(False)
        self._btn_layer.clicked.connect(self.add_layer_requested)
        lay.addWidget(self._btn_layer)

        lay.addWidget(_sep())

        self._btn_meme = _icon_btn("M", "Meme Mode — caption bars", checkable=True)
        self._btn_meme.setEnabled(False)
        self._btn_meme.toggled.connect(self.meme_toggled)
        lay.addWidget(self._btn_meme)

        self._btn_dual = _icon_btn("⊞", "Dual Mode — side-by-side", checkable=True)
        self._btn_dual.setEnabled(False)
        self._btn_dual.toggled.connect(self.dual_toggled)
        lay.addWidget(self._btn_dual)

        lay.addStretch()

    def set_media_loaded(self, loaded: bool):
        self._btn_bubble.setEnabled(loaded)
        self._btn_layer.setEnabled(loaded)
        self._btn_meme.setEnabled(loaded)
        self._btn_dual.setEnabled(loaded)

    def set_meme_checked(self, checked: bool):
        self._btn_meme.blockSignals(True)
        self._btn_meme.setChecked(checked)
        self._btn_meme.blockSignals(False)

    def set_dual_checked(self, checked: bool):
        self._btn_dual.blockSignals(True)
        self._btn_dual.setChecked(checked)
        self._btn_dual.blockSignals(False)

    def set_meme_enabled(self, enabled: bool):
        self._btn_meme.setEnabled(enabled)

    def set_dual_enabled(self, enabled: bool):
        self._btn_dual.setEnabled(enabled)
