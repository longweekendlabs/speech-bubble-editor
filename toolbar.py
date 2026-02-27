"""
toolbar.py — Top toolbar: Open, Export, Undo, Redo, Meme, Dual, About.
"""

from PyQt6.QtWidgets import QToolBar, QFileDialog, QWidget, QSizePolicy
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import pyqtSignal, QSize

from video_player import VIDEO_EXTENSIONS

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')
ALL_EXTENSIONS   = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS


class MainToolbar(QToolBar):

    open_media_requested  = pyqtSignal(str)   # single signal for any media type
    export_requested      = pyqtSignal()
    undo_requested        = pyqtSignal()
    redo_requested        = pyqtSignal()
    add_bubble_requested  = pyqtSignal()
    meme_toggled          = pyqtSignal(bool)
    dual_toggled          = pyqtSignal(bool)
    about_requested       = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Main Toolbar", parent)
        self.setMovable(False)
        self.setIconSize(QSize(20, 20))
        self._build_actions()

    def _build_actions(self):
        # Open (universal — photos and videos)
        act = QAction("Open", self)
        act.setShortcut("Ctrl+O")
        ext_str = ", ".join(e.lstrip(".").upper() for e in ALL_EXTENSIONS[:8]) + "…"
        act.setToolTip(f"Open photo or video ({ext_str})  (Ctrl+O)")
        act.triggered.connect(self._on_open)
        self.addAction(act)

        self.addSeparator()

        # Export
        self.act_export = QAction("Export", self)
        self.act_export.setShortcut("Ctrl+E")
        self.act_export.setToolTip("Export with bubbles (Ctrl+E)")
        self.act_export.setEnabled(False)
        self.act_export.triggered.connect(self.export_requested)
        self.addAction(self.act_export)

        self.addSeparator()

        # Undo
        self.act_undo = QAction("Undo", self)
        self.act_undo.setShortcut("Ctrl+Z")
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self.undo_requested)
        self.addAction(self.act_undo)

        # Redo
        self.act_redo = QAction("Redo", self)
        self.act_redo.setShortcuts([QKeySequence("Ctrl+Y"),
                                    QKeySequence("Ctrl+Shift+Z")])
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self.redo_requested)
        self.addAction(self.act_redo)

        self.addSeparator()

        # Add Bubble
        self.act_add_bubble = QAction("＋ Bubble", self)
        self.act_add_bubble.setShortcut("Ctrl+B")
        self.act_add_bubble.setToolTip(
            "Add a speech bubble to the canvas (Ctrl+B)\n"
            "You can also double-click anywhere on the canvas"
        )
        self.act_add_bubble.setEnabled(False)
        self.act_add_bubble.triggered.connect(self.add_bubble_requested)
        self.addAction(self.act_add_bubble)

        self.addSeparator()

        # Meme
        self.act_meme = QAction("Meme", self)
        self.act_meme.setCheckable(True)
        self.act_meme.setToolTip("Add black caption bars above and below (meme style)")
        self.act_meme.setEnabled(False)
        self.act_meme.toggled.connect(self.meme_toggled)
        self.addAction(self.act_meme)

        self.addSeparator()

        # Dual
        self.act_dual = QAction("Dual", self)
        self.act_dual.setCheckable(True)
        self.act_dual.setToolTip("Side-by-side dual media mode (before / after)")
        self.act_dual.setEnabled(False)
        self.act_dual.toggled.connect(self.dual_toggled)
        self.addAction(self.act_dual)

        # About — right-aligned
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        act_about = QAction("About", self)
        act_about.setToolTip("About Speech Bubble Editor")
        act_about.triggered.connect(self.about_requested)
        self.addAction(act_about)

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
        self.act_export.setEnabled(loaded)
        self.act_add_bubble.setEnabled(loaded)
        self.act_meme.setEnabled(loaded)
        self.act_dual.setEnabled(loaded)

    def set_meme_checked(self, checked: bool):
        self.act_meme.blockSignals(True)
        self.act_meme.setChecked(checked)
        self.act_meme.blockSignals(False)

    def set_dual_checked(self, checked: bool):
        self.act_dual.blockSignals(True)
        self.act_dual.setChecked(checked)
        self.act_dual.blockSignals(False)

    def set_meme_enabled(self, enabled: bool):
        self.act_meme.setEnabled(enabled)

    def set_dual_enabled(self, enabled: bool):
        self.act_dual.setEnabled(enabled)

    def set_undo_enabled(self, enabled: bool):
        self.act_undo.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool):
        self.act_redo.setEnabled(enabled)
