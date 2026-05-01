"""
top_bar.py — TopBar: application header bar (v4 redesign).
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFileDialog, QToolButton,
    QFrame, QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QAction

from constants import ALL_EXTENSIONS


class TopBar(QWidget):

    open_media_requested = pyqtSignal(str)
    export_requested     = pyqtSignal()
    undo_requested       = pyqtSignal()
    redo_requested       = pyqtSignal()
    about_requested      = pyqtSignal()
    zoom_level_requested = pyqtSignal(str)  # "200"|"150"|"100"|"75"|"50"|"fit_width"|"fit_window"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setObjectName("TopBar")
        self._current_zoom = 100
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        # Logo area
        mark = QLabel("◔")
        mark.setObjectName("TopBarMark")
        mark.setFixedWidth(24)
        lay.addWidget(mark)

        logo = QLabel("Speech Bubble Editor")
        logo.setObjectName("TopBarLogo")
        lay.addWidget(logo)

        byline = QLabel("by Long Weekend Labs")
        byline.setObjectName("TopBarByline")
        lay.addWidget(byline)

        lay.addStretch(1)

        # Open
        self.btn_open = QPushButton("□  Open…")
        self.btn_open.setFixedHeight(32)
        self.btn_open.setShortcut(QKeySequence("Ctrl+O"))
        self.btn_open.setToolTip("Open photo or video  (Ctrl+O)")
        self.btn_open.clicked.connect(self._on_open)
        lay.addWidget(self.btn_open)

        # Export
        self.btn_export = QPushButton("⬆  Export…")
        self.btn_export.setFixedHeight(32)
        self.btn_export.setShortcut(QKeySequence("Ctrl+E"))
        self.btn_export.setToolTip("Export with speech bubbles  (Ctrl+E)")
        self.btn_export.setEnabled(False)
        self.btn_export.setObjectName("BtnExport")
        self.btn_export.clicked.connect(self.export_requested)
        lay.addWidget(self.btn_export)

        lay.addWidget(self._separator())

        # Undo
        self.btn_undo = QToolButton()
        self.btn_undo.setText("↶  Undo")
        self.btn_undo.setFixedHeight(32)
        self.btn_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.btn_undo.setToolTip("Undo  (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_requested)
        lay.addWidget(self.btn_undo)

        # Redo
        self.btn_redo = QToolButton()
        self.btn_redo.setText("↷  Redo")
        self.btn_redo.setFixedHeight(32)
        self.btn_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.btn_redo.setToolTip("Redo  (Ctrl+Y / Ctrl+Shift+Z)")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.redo_requested)
        lay.addWidget(self.btn_redo)

        lay.addWidget(self._separator())

        # Zoom picker — opens a dropdown menu
        self._zoom_btn = QPushButton("⊕  100%  ▾")
        self._zoom_btn.setFixedHeight(32)
        self._zoom_btn.setObjectName("ZoomBtn")
        self._zoom_btn.setToolTip("Zoom level — click to change")
        self._zoom_btn.clicked.connect(self._show_zoom_menu)
        lay.addWidget(self._zoom_btn)

        lay.addStretch(1)

        # Theme toggle
        theme_btn = QToolButton()
        theme_btn.setText("☼")
        theme_btn.setFixedSize(32, 32)
        theme_btn.setToolTip("Toggle light/dark theme")
        lay.addWidget(theme_btn)

        # Settings / Preferences
        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setToolTip(
            "Preferences — keyboard shortcuts, export defaults, canvas settings"
        )
        lay.addWidget(settings_btn)

        lay.addWidget(self._separator())

        # More menu (About etc.)
        more_btn = QToolButton()
        more_btn.setText("⋮")
        more_btn.setFixedSize(32, 32)
        more_btn.setToolTip(
            "About / Release Notes / Help & Documentation / Send Feedback / "
            "View on GitHub / Check for Updates"
        )
        more_btn.clicked.connect(self.about_requested)
        lay.addWidget(more_btn)

    # ------------------------------------------------------------------

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("TopBarSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedSize(1, 22)
        return sep

    def _show_zoom_menu(self):
        menu = QMenu(self)
        menu.setObjectName("ZoomMenu")
        for label, key in [
            ("200%", "200"),
            ("150%", "150"),
            ("100%", "100"),
            ("75%",  "75"),
            ("50%",  "50"),
        ]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(str(self._current_zoom) == key)
            act.triggered.connect(
                lambda _checked=False, k=key: self.zoom_level_requested.emit(k)
            )
            menu.addAction(act)
        menu.addSeparator()
        act_fw = QAction("Fit Width", self)
        act_fw.triggered.connect(lambda: self.zoom_level_requested.emit("fit_width"))
        menu.addAction(act_fw)
        act_win = QAction("Fit Window", self)
        act_win.triggered.connect(lambda: self.zoom_level_requested.emit("fit_window"))
        menu.addAction(act_win)
        pos = self._zoom_btn.mapToGlobal(self._zoom_btn.rect().bottomLeft())
        menu.exec(pos)

    # ------------------------------------------------------------------

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
        self._current_zoom = percent
        self._zoom_btn.setText(f"⊕  {percent}%  ▾")
