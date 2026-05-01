"""
top_bar.py — TopBar: application header bar (v4 redesign).

Layout (left → right):
  Logo icon · App name · Byline  ···  Open  Export  | Undo  Redo  | Zoom ▾  ···  Sun  Gear  | ⋮
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QToolButton,
    QFileDialog, QFrame, QMenu, QSizePolicy, QWidgetAction,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QKeySequence, QAction, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray

from constants import ALL_EXTENSIONS
from icons import (
    make_icon, ACCENT, FG, MUTED,
    ICON_OPEN, ICON_EXPORT, ICON_UNDO, ICON_REDO,
    ICON_ZOOM, ICON_SUN, ICON_GEAR, ICON_MORE,
)


class TopBar(QWidget):

    open_media_requested = pyqtSignal(str)
    export_requested     = pyqtSignal()
    undo_requested       = pyqtSignal()
    redo_requested       = pyqtSignal()
    about_requested      = pyqtSignal()
    zoom_changed         = pyqtSignal(object)   # int (percent) or str ("fit-width"/"fit-window")
    theme_change_requested = pyqtSignal(str)    # "dark" | "oled" | "blue"

    _THEMES = ["dark", "oled", "blue"]
    _THEME_TIPS = {
        "dark": "Theme: Dark — click for OLED Black",
        "oled": "Theme: OLED Black — click for Blue Slate",
        "blue": "Theme: Blue Slate — click for Dark",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setObjectName("TopBar")
        self._current_theme = "dark"
        self._build_ui()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(6)

        # ── Logo ──────────────────────────────────────────────────────
        logo_icon = QLabel()
        logo_icon.setFixedSize(22, 22)
        logo_pix = self._make_logo_pixmap(22)
        logo_icon.setPixmap(logo_pix)
        lay.addWidget(logo_icon)

        app_name = QLabel("Speech Bubble Editor")
        app_name.setObjectName("TopBarLogo")
        lay.addWidget(app_name)

        byline = QLabel("by Long Weekend Labs")
        byline.setObjectName("TopBarByline")
        lay.addWidget(byline)

        lay.addStretch(1)

        # ── Open ──────────────────────────────────────────────────────
        self.btn_open = self._action_btn(
            icon=make_icon(ICON_OPEN, 14, FG),
            label="Open…",
            tooltip="Open photo or video  (Ctrl+O)",
            shortcut="Ctrl+O",
        )
        self.btn_open.clicked.connect(self._on_open)
        lay.addWidget(self.btn_open)

        # ── Export ────────────────────────────────────────────────────
        self.btn_export = self._action_btn(
            icon=make_icon(ICON_EXPORT, 14, "#ffffff"),
            label="Export…",
            tooltip="Export with bubbles  (Ctrl+E)",
            shortcut="Ctrl+E",
            accent=True,
        )
        self.btn_export.setObjectName("BtnExport")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_requested)
        lay.addWidget(self.btn_export)

        lay.addWidget(self._separator())

        # ── Undo / Redo ───────────────────────────────────────────────
        self.btn_undo = self._action_btn(
            icon=make_icon(ICON_UNDO, 14, MUTED),
            label="Undo",
            tooltip="Undo  (Ctrl+Z)",
            shortcut="Ctrl+Z",
        )
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_requested)
        lay.addWidget(self.btn_undo)

        self.btn_redo = self._action_btn(
            icon=make_icon(ICON_REDO, 14, MUTED),
            label="Redo",
            tooltip="Redo  (Ctrl+Y / Ctrl+Shift+Z)",
            shortcut="Ctrl+Y",
        )
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.redo_requested)
        lay.addWidget(self.btn_redo)

        lay.addWidget(self._separator())

        # ── Zoom picker ───────────────────────────────────────────────
        self._zoom_level = 100
        self.btn_zoom = QPushButton()
        self.btn_zoom.setObjectName("ZoomBtn")
        self.btn_zoom.setFixedHeight(32)
        self.btn_zoom.setMinimumWidth(110)
        self.btn_zoom.setIcon(make_icon(ICON_ZOOM, 13, MUTED))
        self.btn_zoom.setIconSize(QSize(13, 13))
        self.btn_zoom.setToolTip("Zoom level — click to change")
        self.btn_zoom.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._update_zoom_label()
        self.btn_zoom.clicked.connect(self._show_zoom_menu)
        lay.addWidget(self.btn_zoom)

        lay.addStretch(1)

        # ── Right icon buttons ─────────────────────────────────────────
        self.btn_theme = self._icon_btn(
            make_icon(ICON_SUN, 15, MUTED),
            self._THEME_TIPS["dark"],
        )
        self.btn_theme.clicked.connect(self._cycle_theme)
        lay.addWidget(self.btn_theme)

        self.btn_prefs = self._icon_btn(
            make_icon(ICON_GEAR, 15, MUTED),
            "Preferences — keyboard shortcuts, export defaults, canvas settings",
        )
        lay.addWidget(self.btn_prefs)

        lay.addWidget(self._separator())

        # ── ⋮ More menu ───────────────────────────────────────────────
        self.btn_more = self._icon_btn(
            make_icon(ICON_MORE, 15, MUTED),
            "More options — about, help, feedback",
        )
        self.btn_more.clicked.connect(self._show_more_menu)
        lay.addWidget(self.btn_more)

    # ------------------------------------------------------------------
    # Widget factories
    # ------------------------------------------------------------------

    def _action_btn(self, icon: QIcon, label: str, tooltip: str,
                    shortcut: str = "", accent: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setIcon(icon)
        btn.setIconSize(QSize(14, 14))
        btn.setFixedHeight(32)
        btn.setToolTip(tooltip)
        if shortcut:
            btn.setShortcut(QKeySequence(shortcut))
        return btn

    def _icon_btn(self, icon: QIcon, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(icon)
        btn.setIconSize(QSize(15, 15))
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        return btn

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("TopBarSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedSize(1, 22)
        return sep

    def _make_logo_pixmap(self, size: int) -> QPixmap:
        """Speech-bubble logo mark in accent color."""
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="{ACCENT}" opacity="0.15"/>
            <path d="M8 12h8M8 8h8M8 16h5" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="12" r="10" stroke="{ACCENT}" stroke-width="1.5" fill="none"/>
        </svg>'''
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        renderer.render(p)
        p.end()
        return pix

    # ------------------------------------------------------------------
    # Zoom menu
    # ------------------------------------------------------------------

    def _show_zoom_menu(self):
        menu = QMenu(self)
        menu.setObjectName("ZoomMenu")

        LEVELS = [
            ("200%",       200),
            ("150%",       150),
            ("100%",       100),
            ("75%",        75),
            ("50%",        50),
            None,
            ("Fit Width",  "fit-width"),
            ("Fit Window", "fit-window"),
        ]
        for item in LEVELS:
            if item is None:
                menu.addSeparator()
                continue
            label, value = item
            act = QAction(label, menu)
            if value == self._zoom_level:
                act.setCheckable(True)
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, v=value: self._on_zoom(v))
            menu.addAction(act)

        # Show below the zoom button
        pos = self.btn_zoom.mapToGlobal(
            self.btn_zoom.rect().bottomLeft()
        )
        menu.exec(pos)

    def _on_zoom(self, value):
        self._zoom_level = value
        self._update_zoom_label()
        self.zoom_changed.emit(value)

    def _update_zoom_label(self):
        z = self._zoom_level
        if isinstance(z, int):
            label = f"  {z}%  "
        elif z == "fit-width":
            label = "  Fit Width  "
        else:
            label = "  Fit Window  "
        self.btn_zoom.setText(label)

    # ------------------------------------------------------------------
    # More menu
    # ------------------------------------------------------------------

    def _show_more_menu(self):
        menu = QMenu(self)

        ITEMS = [
            ("About Speech Bubble Editor",  self.about_requested.emit),
            ("Release Notes",               None),
            ("Help & Documentation",        None),
            None,
            ("Send Feedback",               None),
            ("View on GitHub",              None),
            None,
            ("Check for Updates",           None),
        ]
        for item in ITEMS:
            if item is None:
                menu.addSeparator()
                continue
            label, callback = item
            act = QAction(label, menu)
            if callback:
                act.triggered.connect(callback)
            else:
                act.setEnabled(False)
            menu.addAction(act)

        pos = self.btn_more.mapToGlobal(
            self.btn_more.rect().bottomRight()
        )
        # align right edge of menu to button right edge
        menu.exec(pos)

    # ------------------------------------------------------------------
    # Open dialog
    # ------------------------------------------------------------------

    def _on_open(self):
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            f"All supported media ({ext_list})"
        )
        if path:
            self.open_media_requested.emit(path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _cycle_theme(self):
        idx = self._THEMES.index(self._current_theme)
        self._current_theme = self._THEMES[(idx + 1) % len(self._THEMES)]
        self.btn_theme.setToolTip(self._THEME_TIPS[self._current_theme])
        self.theme_change_requested.emit(self._current_theme)

    def set_media_loaded(self, loaded: bool):
        self.btn_export.setEnabled(loaded)

    def set_undo_enabled(self, enabled: bool):
        self.btn_undo.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool):
        self.btn_redo.setEnabled(enabled)

    def update_zoom(self, percent: int):
        """Called by PhotoView.zoom_changed signal."""
        self._zoom_level = percent
        self._update_zoom_label()
