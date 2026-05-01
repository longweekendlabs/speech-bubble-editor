"""
tool_sidebar.py — ToolSidebar: vertical icon strip on the left edge.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence


def _icon_btn(icon: str, label: str, tip: str, checkable: bool = False) -> QToolButton:
    btn = QToolButton()
    btn.setText(f"{icon}\n{label}")
    btn.setToolTip(tip)
    btn.setCheckable(checkable)
    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    btn.setFixedSize(76, 64)
    return btn


class ToolSidebar(QWidget):

    add_bubble_requested = pyqtSignal()
    add_layer_requested  = pyqtSignal()
    meme_toggled         = pyqtSignal(bool)
    dual_toggled         = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(96)
        self.setObjectName("ToolSidebar")
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 18, 10, 12)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        self._btn_select = _icon_btn("⌁", "Select", "Select  (V)", checkable=True)
        self._btn_select.setChecked(True)
        self._tool_group.addButton(self._btn_select)
        lay.addWidget(self._btn_select)

        self._btn_move = _icon_btn("✣", "Move", "Move selected item", checkable=True)
        self._tool_group.addButton(self._btn_move)
        lay.addWidget(self._btn_move)

        self._btn_bubble = _icon_btn("◯", "Bubble", "Add Speech Bubble  (Ctrl+B)")
        self._btn_bubble.setShortcut(QKeySequence("Ctrl+B"))
        self._btn_bubble.setEnabled(False)
        self._btn_bubble.clicked.connect(self.add_bubble_requested)
        lay.addWidget(self._btn_bubble)

        self._btn_caption = _icon_btn("▭", "Caption", "Caption style")
        self._btn_caption.setEnabled(False)
        lay.addWidget(self._btn_caption)

        self._btn_text = _icon_btn("T", "Text", "Text-only style")
        self._btn_text.setEnabled(False)
        lay.addWidget(self._btn_text)

        self._btn_layer = _icon_btn("▤", "Layers", "Add Overlay Layer  (Ctrl+L)")
        self._btn_layer.setShortcut(QKeySequence("Ctrl+L"))
        self._btn_layer.setEnabled(False)
        self._btn_layer.clicked.connect(self.add_layer_requested)
        lay.addWidget(self._btn_layer)

        self._btn_meme = _icon_btn("☺", "Meme Mode", "Meme Mode — caption bars", checkable=True)
        self._btn_meme.setEnabled(False)
        self._btn_meme.toggled.connect(self.meme_toggled)
        lay.addWidget(self._btn_meme)

        self._btn_dual = _icon_btn("▥", "Dual Mode", "Dual Mode — side-by-side", checkable=True)
        self._btn_dual.setEnabled(False)
        self._btn_dual.toggled.connect(self.dual_toggled)
        lay.addWidget(self._btn_dual)

        lay.addStretch()

        collapse = _icon_btn("≪", "", "Collapse sidebar")
        collapse.setFixedSize(76, 36)
        lay.addWidget(collapse)

    def set_media_loaded(self, loaded: bool):
        self._btn_bubble.setEnabled(loaded)
        self._btn_caption.setEnabled(loaded)
        self._btn_text.setEnabled(loaded)
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
