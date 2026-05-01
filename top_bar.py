"""
top_bar.py — TopBar: application header bar (replaces v3 MainToolbar).
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFileDialog, QToolButton,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence

from constants import ALL_EXTENSIONS


class TopBar(QWidget):

    open_media_requested = pyqtSignal(str)
    export_requested     = pyqtSignal()
    undo_requested       = pyqtSignal()
    redo_requested       = pyqtSignal()
    about_requested      = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setObjectName("TopBar")
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 18, 0)
        lay.setSpacing(10)

        mark = QLabel("◔")
        mark.setObjectName("TopBarMark")
        mark.setFixedWidth(22)
        lay.addWidget(mark)

        logo = QLabel("Speech Bubble Editor")
        logo.setObjectName("TopBarLogo")
        lay.addWidget(logo)

        byline = QLabel("by Long Weekend Labs")
        byline.setObjectName("TopBarByline")
        lay.addWidget(byline)

        lay.addStretch(1)

        self.btn_open = QPushButton("□  Open...")
        self.btn_open.setFixedSize(112, 38)
        self.btn_open.setShortcut(QKeySequence("Ctrl+O"))
        self.btn_open.setToolTip("Open photo or video  (Ctrl+O)")
        self.btn_open.clicked.connect(self._on_open)
        lay.addWidget(self.btn_open)

        self.btn_export = QPushButton("⇧  Export...")
        self.btn_export.setFixedSize(118, 38)
        self.btn_export.setShortcut(QKeySequence("Ctrl+E"))
        self.btn_export.setToolTip("Export with bubbles  (Ctrl+E)")
        self.btn_export.setEnabled(False)
        self.btn_export.setObjectName("BtnExport")
        self.btn_export.clicked.connect(self.export_requested)
        lay.addWidget(self.btn_export)

        lay.addWidget(self._separator())

        self.btn_undo = QToolButton()
        self.btn_undo.setText("↶  Undo")
        self.btn_undo.setFixedSize(92, 38)
        self.btn_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.btn_undo.setToolTip("Undo  (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_requested)
        lay.addWidget(self.btn_undo)

        self.btn_redo = QToolButton()
        self.btn_redo.setText("↷  Redo")
        self.btn_redo.setFixedSize(88, 38)
        self.btn_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.btn_redo.setToolTip("Redo  (Ctrl+Y / Ctrl+Shift+Z)")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.redo_requested)
        lay.addWidget(self.btn_redo)

        lay.addWidget(self._separator())

        self._zoom_label = QLabel("⊕  100%  ⌄")
        self._zoom_label.setFixedSize(128, 38)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setObjectName("ZoomLabel")
        self._zoom_label.setToolTip("Current zoom level")
        lay.addWidget(self._zoom_label)

        lay.addStretch(1)

        theme = QToolButton()
        theme.setText("☼")
        theme.setFixedSize(36, 38)
        theme.setToolTip("Display settings")
        lay.addWidget(theme)

        settings = QToolButton()
        settings.setText("⚙")
        settings.setFixedSize(36, 38)
        settings.setToolTip("Settings")
        lay.addWidget(settings)

        lay.addWidget(self._separator())

        btn_about = QToolButton()
        btn_about.setText("⋯")
        btn_about.setFixedSize(36, 38)
        btn_about.setToolTip("About Speech Bubble Editor")
        btn_about.clicked.connect(self.about_requested)
        lay.addWidget(btn_about)

    def _separator(self):
        sep = QFrame()
        sep.setObjectName("TopBarSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedSize(1, 28)
        return sep

    def _on_open(self):
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            f"All supported media ({ext_list})"
        )
        if path:
            self.open_media_requested.emit(path)

    def set_media_loaded(self, loaded: bool):
        self.btn_export.setEnabled(loaded)

    def set_undo_enabled(self, enabled: bool):
        self.btn_undo.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool):
        self.btn_redo.setEnabled(enabled)

    def update_zoom(self, percent: int):
        self._zoom_label.setText(f"⊕  {percent}%  ⌄")
