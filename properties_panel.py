"""
properties_panel.py — Bottom panel: style, font, and bubble appearance controls.

Shows context-sensitive controls for the currently selected bubble.
When no bubble is selected, shows a hint label.
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton,
    QSpinBox, QDoubleSpinBox, QSlider, QColorDialog, QFrame,
    QButtonGroup, QFontComboBox, QSizePolicy, QStackedWidget, QCheckBox
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _color_btn(color: QColor, tooltip: str) -> QPushButton:
    """Small square colour-preview button."""
    btn = QPushButton()
    btn.setFixedSize(26, 26)
    btn.setToolTip(tooltip)
    _set_btn_color(btn, color)
    return btn


def _set_btn_color(btn: QPushButton, color: QColor):
    r, g, b = color.red(), color.green(), color.blue()
    btn.setStyleSheet(
        f"QPushButton {{"
        f"  background-color: rgb({r},{g},{b});"
        f"  border: 1.5px solid #777;"
        f"  border-radius: 4px;"
        f"}}"
        f"QPushButton:hover {{ border: 2px solid #aaa; }}"
    )


def _sep() -> QFrame:
    """Vertical separator line."""
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    f.setFixedWidth(10)
    return f


STYLE_LABELS = {
    "oval":    "Oval",
    "cloud":   "Cloud",
    "rect":    "Rect",
    "spiky":   "Spiky",
    "text":    "Text",
    "scrim":   "Scrim",
    "caption": "Caption",
}


# ---------------------------------------------------------------------------
# PropertiesPanel
# ---------------------------------------------------------------------------

class PropertiesPanel(QWidget):
    """
    Bottom strip showing controls for the selected item.
    Page 0 = hint, Page 1 = bubble controls, Page 2 = media item controls.
    Directly writes to the item — no signal indirection needed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bubble = None      # currently selected BubbleItem
        self._media  = None      # currently selected MediaItem
        self._updating = False   # guard against recursive updates
        self.setFixedHeight(96)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(0)

        # Stacked: index 0 = hint, index 1 = controls
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        # --- Page 0: no-selection hint ---
        hint_page = QWidget()
        hint_layout = QHBoxLayout(hint_page)
        hint_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("Double-click on the photo to add a speech bubble  |  "
                       "Click a bubble to select and edit it")
        hint.setStyleSheet("color: #888; font-size: 12px;")
        hint_layout.addWidget(hint)
        self._stack.addWidget(hint_page)    # index 0

        # --- Page 1: controls ---
        ctrl_page = QWidget()
        row = QHBoxLayout(ctrl_page)
        row.setContentsMargins(6, 2, 6, 2)
        row.setSpacing(6)

        # ---- Style buttons -------------------------------------------
        style_box = QWidget()
        style_col = QVBoxLayout(style_box)
        style_col.setContentsMargins(0, 0, 0, 0)
        style_col.setSpacing(2)
        style_col.addWidget(QLabel("Style"))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(3)
        self._style_group = QButtonGroup(self)
        self._style_btns: dict[str, QToolButton] = {}
        for key, label in STYLE_LABELS.items():
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setToolTip(f"Change to {label} style")
            btn.setStyleSheet(
                "QToolButton { border: 1px solid #888; border-radius: 4px; padding: 2px 6px; }"
                "QToolButton:checked { background: #3a7bd5; color: white; border: 1px solid #2a5fa0; }"
                "QToolButton:hover { background: #e0e8f8; }"
            )
            self._style_group.addButton(btn)
            self._style_btns[key] = btn
            btn_row.addWidget(btn)
            btn.clicked.connect(lambda checked, k=key: self._on_style(k))

        style_col.addLayout(btn_row)
        row.addWidget(style_box)
        row.addWidget(_sep())

        # ---- Font controls -------------------------------------------
        font_box = QWidget()
        font_col = QVBoxLayout(font_box)
        font_col.setContentsMargins(0, 0, 0, 0)
        font_col.setSpacing(2)
        font_col.addWidget(QLabel("Font"))

        font_row = QHBoxLayout()
        font_row.setSpacing(4)

        self._font_combo = QFontComboBox()
        self._font_combo.setFixedWidth(150)
        self._font_combo.setFixedHeight(28)
        self._font_combo.setToolTip("Font family")
        self._font_combo.currentFontChanged.connect(self._on_font_family)
        font_row.addWidget(self._font_combo)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 96)
        self._font_size.setValue(20)
        self._font_size.setFixedWidth(55)
        self._font_size.setFixedHeight(28)
        self._font_size.setSuffix(" pt")
        self._font_size.setToolTip("Font size")
        self._font_size.valueChanged.connect(self._on_font_size)
        font_row.addWidget(self._font_size)

        self._btn_bold = QToolButton()
        self._btn_bold.setText("B")
        self._btn_bold.setCheckable(True)
        self._btn_bold.setFixedSize(28, 28)
        self._btn_bold.setToolTip("Bold")
        self._btn_bold.setStyleSheet(
            "QToolButton { font-weight: bold; border: 1px solid #888; border-radius: 4px; }"
            "QToolButton:checked { background: #3a7bd5; color: white; }"
        )
        self._btn_bold.clicked.connect(self._on_bold)
        font_row.addWidget(self._btn_bold)

        self._btn_italic = QToolButton()
        self._btn_italic.setText("I")
        self._btn_italic.setCheckable(True)
        self._btn_italic.setFixedSize(28, 28)
        self._btn_italic.setToolTip("Italic")
        self._btn_italic.setStyleSheet(
            "QToolButton { font-style: italic; border: 1px solid #888; border-radius: 4px; }"
            "QToolButton:checked { background: #3a7bd5; color: white; }"
        )
        self._btn_italic.clicked.connect(self._on_italic)
        font_row.addWidget(self._btn_italic)

        self._btn_text_color = _color_btn(QColor(15, 15, 15), "Text colour")
        self._btn_text_color.clicked.connect(self._on_text_color)
        font_row.addWidget(self._btn_text_color)

        font_col.addLayout(font_row)
        row.addWidget(font_box)
        row.addWidget(_sep())

        # ---- Bubble appearance controls ------------------------------
        bub_box = QWidget()
        bub_col = QVBoxLayout(bub_box)
        bub_col.setContentsMargins(0, 0, 0, 0)
        bub_col.setSpacing(2)
        bub_col.addWidget(QLabel("Bubble"))

        bub_row = QHBoxLayout()
        bub_row.setSpacing(6)

        # Fill colour
        bub_row.addWidget(QLabel("Fill:"))
        self._btn_fill = _color_btn(QColor(255, 255, 255), "Fill colour")
        self._btn_fill.clicked.connect(self._on_fill_color)
        bub_row.addWidget(self._btn_fill)

        # Opacity slider
        bub_row.addWidget(QLabel("Opacity:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(94)
        self._opacity_slider.setFixedWidth(80)
        self._opacity_slider.setToolTip("Fill opacity")
        self._opacity_slider.valueChanged.connect(self._on_opacity)
        bub_row.addWidget(self._opacity_slider)
        self._opacity_label = QLabel("94%")
        self._opacity_label.setFixedWidth(32)
        bub_row.addWidget(self._opacity_label)

        # Border colour
        bub_row.addWidget(QLabel("Border:"))
        self._btn_border_color = _color_btn(QColor(20, 20, 20), "Border colour")
        self._btn_border_color.clicked.connect(self._on_border_color)
        bub_row.addWidget(self._btn_border_color)

        # Border width
        self._border_width = QDoubleSpinBox()
        self._border_width.setRange(0.0, 12.0)
        self._border_width.setSingleStep(0.5)
        self._border_width.setValue(2.0)
        self._border_width.setFixedWidth(58)
        self._border_width.setFixedHeight(28)
        self._border_width.setSuffix(" px")
        self._border_width.setToolTip("Border thickness")
        self._border_width.valueChanged.connect(self._on_border_width)
        bub_row.addWidget(self._border_width)

        bub_col.addLayout(bub_row)
        row.addWidget(bub_box)
        row.addStretch()

        self._stack.addWidget(ctrl_page)   # index 1

        # --- Page 2: media item controls ---
        media_page = QWidget()
        media_row = QHBoxLayout(media_page)
        media_row.setContentsMargins(12, 2, 12, 2)
        media_row.setSpacing(16)

        media_row.addWidget(QLabel("Media:"))

        self._chk_lock_ratio = QCheckBox("Lock Aspect Ratio")
        self._chk_lock_ratio.setToolTip(
            "Keep width/height proportional while resizing\n"
            "Checking this will also restore the original proportions.\n"
            "Tip: hold Shift while dragging a corner for a temporary lock.")
        self._chk_lock_ratio.toggled.connect(self._on_lock_ratio)
        media_row.addWidget(self._chk_lock_ratio)

        self._btn_reset_size = QPushButton("Reset to Original Size")
        self._btn_reset_size.setToolTip("Restore the media to its native pixel dimensions")
        self._btn_reset_size.setFixedHeight(28)
        self._btn_reset_size.clicked.connect(self._on_reset_media_size)
        media_row.addWidget(self._btn_reset_size)

        media_row.addStretch()
        self._stack.addWidget(media_page)  # index 2

        self._stack.setCurrentIndex(0)     # start with hint

    # ------------------------------------------------------------------
    # Public API — called from MainWindow on selection change
    # ------------------------------------------------------------------

    def update_for_bubble(self, bubble):
        """Populate all controls from the bubble's current state."""
        self._bubble = bubble
        self._updating = True
        try:
            # Style buttons
            s = bubble.get_style()
            for key, btn in self._style_btns.items():
                btn.setChecked(key == s)

            # Font
            font = bubble.get_font()
            self._font_combo.setCurrentFont(font)
            self._font_size.setValue(max(6, font.pointSize()))
            self._btn_bold.setChecked(font.bold())
            self._btn_italic.setChecked(font.italic())
            _set_btn_color(self._btn_text_color, bubble.get_text_color())

            # Bubble appearance
            fill = bubble.get_fill_color()
            _set_btn_color(self._btn_fill, fill)
            opacity_pct = round(fill.alpha() * 100 / 255)
            self._opacity_slider.setValue(opacity_pct)
            self._opacity_label.setText(f"{opacity_pct}%")
            _set_btn_color(self._btn_border_color, bubble.get_border_color())
            self._border_width.setValue(bubble.get_border_width())
        finally:
            self._updating = False

        self._stack.setCurrentIndex(1)

    def update_for_media(self, media_item):
        """Populate media controls from the media item's current state."""
        self._media  = media_item
        self._bubble = None
        self._updating = True
        try:
            self._chk_lock_ratio.setChecked(media_item._lock_ratio)
        finally:
            self._updating = False
        self._stack.setCurrentIndex(2)

    def clear(self):
        """No item selected — show the hint page."""
        self._bubble = None
        self._media  = None
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Control callbacks — each directly updates the selected bubble
    # ------------------------------------------------------------------

    def _on_style(self, style: str):
        if self._bubble and not self._updating:
            self._bubble.set_style(style)

    def _on_font_family(self, font: QFont):
        if self._bubble and not self._updating:
            f = QFont(self._bubble.get_font())
            f.setFamily(font.family())
            self._bubble.set_font(f)

    def _on_font_size(self, size: int):
        if self._bubble and not self._updating:
            f = QFont(self._bubble.get_font())
            f.setPointSize(size)
            self._bubble.set_font(f)

    def _on_bold(self, checked: bool):
        if self._bubble and not self._updating:
            f = QFont(self._bubble.get_font())
            f.setBold(checked)
            self._bubble.set_font(f)

    def _on_italic(self, checked: bool):
        if self._bubble and not self._updating:
            f = QFont(self._bubble.get_font())
            f.setItalic(checked)
            self._bubble.set_font(f)

    def _on_text_color(self):
        if not self._bubble:
            return
        color = QColorDialog.getColor(
            self._bubble.get_text_color(), self, "Text Colour")
        if color.isValid():
            self._bubble.set_text_color(color)
            _set_btn_color(self._btn_text_color, color)

    def _on_fill_color(self):
        if not self._bubble:
            return
        current = self._bubble.get_fill_color()
        color = QColorDialog.getColor(
            current, self, "Fill Colour",
            QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._bubble.set_fill_color(color)
            _set_btn_color(self._btn_fill, color)
            pct = round(color.alpha() * 100 / 255)
            self._opacity_slider.blockSignals(True)
            self._opacity_slider.setValue(pct)
            self._opacity_slider.blockSignals(False)
            self._opacity_label.setText(f"{pct}%")

    def _on_opacity(self, value: int):
        self._opacity_label.setText(f"{value}%")
        if self._bubble and not self._updating:
            color = QColor(self._bubble.get_fill_color())
            color.setAlpha(round(value * 255 / 100))
            self._bubble.set_fill_color(color)
            _set_btn_color(self._btn_fill, color)

    def _on_border_color(self):
        if not self._bubble:
            return
        color = QColorDialog.getColor(
            self._bubble.get_border_color(), self, "Border Colour")
        if color.isValid():
            self._bubble.set_border_color(color)
            _set_btn_color(self._btn_border_color, color)

    def _on_border_width(self, value: float):
        if self._bubble and not self._updating:
            self._bubble.set_border_width(value)

    # ------------------------------------------------------------------
    # Media item callbacks
    # ------------------------------------------------------------------

    def _on_lock_ratio(self, checked: bool):
        if self._media and not self._updating:
            if checked:
                # Save current position, restore native proportions, keep position
                pos = self._media.pos()
                self._media.restore_native_size()
                self._media.setPos(pos)
                sc = self._media.scene()
                if sc and hasattr(sc, 'fit_scene_to_media'):
                    sc.fit_scene_to_media()
            self._media._lock_ratio = checked

    def _on_reset_media_size(self):
        if self._media:
            pos = self._media.pos()
            self._media.restore_native_size()
            self._media.setPos(pos)
            sc = self._media.scene()
            if sc and hasattr(sc, 'fit_scene_to_media'):
                sc.fit_scene_to_media()
