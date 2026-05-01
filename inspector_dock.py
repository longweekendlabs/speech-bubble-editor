"""
inspector_dock.py — v4 right inspector with accordion sections and layers (v4 redesign).

Key changes from v3:
  - AccordionSection uses a visible 16×16 chevron QPushButton (#SectionChevron)
    that flips ▼/▶ and has QSS property "open" for accent highlighting
  - ALIGNMENT & ARRANGE section removed (promoted to ContextToolbar)
  - All 7 bubble styles shown in the picker: oval, cloud, rect, spiky, text, scrim, caption
  - Text alignment buttons have distinct L/C/R/J labels with tooltips
  - All interactive controls have setToolTip() calls
  - _color_row and _slider_row accept a tooltip= kwarg
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabBar, QStackedWidget,
    QLabel, QScrollArea, QFrame, QToolButton, QPushButton, QButtonGroup,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QColorDialog,
    QCheckBox, QListWidget, QListWidgetItem,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF

from bubble import BubbleItem
from media_item import MediaItem
from icons import (
    make_icon, FG, MUTED,
    ICON_STYLE_OVAL, ICON_STYLE_CLOUD, ICON_STYLE_RECT, ICON_STYLE_SPIKY,
    ICON_STYLE_TEXT, ICON_STYLE_SCRIM, ICON_STYLE_CAPTION,
)
from undo_commands import (
    TextChangeCommand, StyleChangeCommand, FontChangeCommand,
    FillColorChangeCommand, BorderColorChangeCommand,
    BorderWidthChangeCommand, TextColorChangeCommand,
    TextAlignmentChangeCommand, TailPositionChangeCommand,
    TailWidthChangeCommand, ShadowChangeCommand, MoveBubbleCommand,
    ZValueChangeCommand,
)


STYLE_LABELS = {
    "oval":    "Speech",
    "cloud":   "Cloud",
    "rect":    "Rectangle",
    "spiky":   "Starburst",
    "text":    "Text only",
    "scrim":   "Scrim",
    "caption": "Caption",
}

STYLE_ICONS = {
    "oval":    ICON_STYLE_OVAL,
    "cloud":   ICON_STYLE_CLOUD,
    "rect":    ICON_STYLE_RECT,
    "spiky":   ICON_STYLE_SPIKY,
    "text":    ICON_STYLE_TEXT,
    "scrim":   ICON_STYLE_SCRIM,
    "caption": ICON_STYLE_CAPTION,
}

TAIL_POSITIONS = (
    "Top Left", "Top Center", "Top Right", "Right",
    "Bottom Right", "Bottom Center", "Bottom Left", "Left",
)


def _set_btn_color(btn: QPushButton, color: QColor):
    btn.setStyleSheet(
        "QPushButton {"
        f"background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});"
        "border: 1px solid #2e3a50; border-radius: 4px;"
        "}"
    )


# ---------------------------------------------------------------------------
# CommitTextEdit
# ---------------------------------------------------------------------------

class CommitTextEdit(QTextEdit):
    editCommitted = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._start_text = ""

    def focusInEvent(self, event):
        self._start_text = self.toPlainText()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        end_text = self.toPlainText()
        if end_text != self._start_text:
            self.editCommitted.emit(self._start_text, end_text)
        super().focusOutEvent(event)


# ---------------------------------------------------------------------------
# AccordionSection — collapsible with visible chevron button
# ---------------------------------------------------------------------------

class AccordionSection(QWidget):
    def __init__(self, title: str, parent=None, checkable: bool = False):
        super().__init__(parent)
        self.setObjectName("InspectorSection")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header row
        header_w = QWidget()
        header_w.setObjectName("InspectorSectionHeader")
        header_w.setFixedHeight(32)
        hbox = QHBoxLayout(header_w)
        hbox.setContentsMargins(14, 0, 10, 0)
        hbox.setSpacing(6)

        # Chevron button — 16×16, styled by QSS property "open"
        self._chevron = QPushButton("▼")
        self._chevron.setObjectName("SectionChevron")
        self._chevron.setFixedSize(16, 16)
        self._chevron.setProperty("open", "true")
        self._chevron.setToolTip("Expand / collapse section")
        self._chevron.clicked.connect(self._toggle)
        hbox.addWidget(self._chevron)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setObjectName("InspectorSectionTitle")
        hbox.addWidget(title_lbl, stretch=1)

        if checkable:
            self.check = QCheckBox()
            self.check.setObjectName("InspectorSectionCheck")
            hbox.addWidget(self.check)
        else:
            self.check = None

        outer.addWidget(header_w)

        self.body = QWidget()
        self.body.setObjectName("InspectorSectionBody")
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(12, 6, 12, 10)
        self.body_lay.setSpacing(8)
        outer.addWidget(self.body)

        self._expanded = True

    def _toggle(self):
        self._expanded = not self._expanded
        self.body.setVisible(self._expanded)
        self._chevron.setText("▼" if self._expanded else "▶")
        self._chevron.setProperty("open", "true" if self._expanded else "false")
        # Force QSS re-evaluation
        self._chevron.style().unpolish(self._chevron)
        self._chevron.style().polish(self._chevron)


# ---------------------------------------------------------------------------
# InspectorDock
# ---------------------------------------------------------------------------

class InspectorDock(QWidget):
    dual_gap_changed    = pyqtSignal(int)
    dual_border_changed = pyqtSignal(QColor, float)
    dual_feather_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setMaximumWidth(380)
        self.setObjectName("InspectorDock")
        self._bubble     = None
        self._media      = None
        self._scene      = None
        self._undo_stack = None
        self._updating   = False
        self._font_combo = None
        self._layer_items = {}
        self._dual_border_color_val = QColor(90, 90, 90)
        self._build_ui()

    @property
    def props(self):
        return self

    def set_scene(self, scene):
        self._scene = scene
        scene.selectionChanged.connect(self._refresh_layers)
        scene.bubble_changed.connect(self._refresh_layers)
        scene.overlay_added.connect(lambda _item: self._refresh_layers())
        scene.overlay_removed.connect(lambda _item: self._refresh_layers())
        self._refresh_layers()

    def set_undo_stack(self, stack):
        self._undo_stack = stack

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._tabs = QTabBar()
        self._tabs.addTab("Inspector")
        self._tabs.addTab("Layers")
        self._tabs.setObjectName("InspectorTabBar")
        self._tabs.setExpanding(True)
        self._tabs.currentChanged.connect(self._stack_tab)
        lay.addWidget(self._tabs)

        self._stack = QStackedWidget()
        lay.addWidget(self._stack, stretch=1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inspector_page = QWidget()
        inspector_page.setObjectName("InspectorPage")
        self._inspector_lay = QVBoxLayout(inspector_page)
        self._inspector_lay.setContentsMargins(0, 0, 0, 0)
        self._inspector_lay.setSpacing(0)
        self._build_inspector_sections()
        scroll.setWidget(inspector_page)
        self._stack.addWidget(scroll)

        layers_page = QWidget()
        layers_lay = QVBoxLayout(layers_page)
        layers_lay.setContentsMargins(8, 10, 8, 8)
        layers_lay.setSpacing(8)
        self._layers_list = QListWidget()
        self._layers_list.setObjectName("LayersList")
        self._layers_list.itemChanged.connect(self._on_layer_item_changed)
        self._layers_list.itemSelectionChanged.connect(self._on_layer_selection)
        layers_lay.addWidget(self._layers_list)
        self._stack.addWidget(layers_page)

    def _build_inspector_sections(self):
        self._build_text_section()
        self._build_bubble_section()
        self._build_colors_section()
        self._build_typography_section()
        self._build_tail_section()
        self._build_stroke_section()
        self._build_shadow_section()
        self._build_dual_section()
        self._inspector_lay.addStretch()

    def _build_text_section(self):
        section = AccordionSection("TEXT")
        top = QHBoxLayout()
        top.addStretch()
        self._char_count = QLabel("0 / 200")
        self._char_count.setObjectName("InspectorHint")
        top.addWidget(self._char_count)
        section.body_lay.addLayout(top)
        self._text_edit = CommitTextEdit()
        self._text_edit.setObjectName("InspectorTextEdit")
        self._text_edit.setFixedHeight(80)
        self._text_edit.setAcceptRichText(False)
        self._text_edit.setPlaceholderText("Type bubble text here…")
        self._text_edit.setToolTip("Bubble text (max 200 characters)")
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.editCommitted.connect(self._on_text_committed)
        section.body_lay.addWidget(self._text_edit)
        self._text_section = section
        self._inspector_lay.addWidget(section)

    def _build_bubble_section(self):
        section = AccordionSection("BUBBLE")
        section.body_lay.addWidget(self._label("Style"))

        # 7 style buttons in a grid (max 5 per row)
        grid = QGridLayout()
        grid.setSpacing(6)
        self._style_group = QButtonGroup(self)
        self._style_group.setExclusive(True)
        self._style_btns = {}
        styles = list(STYLE_LABELS.keys())
        cols = 5
        from PyQt6.QtCore import QSize
        for idx, key in enumerate(styles):
            btn = QToolButton()
            btn.setObjectName("StyleButton")
            btn.setIcon(make_icon(STYLE_ICONS[key], 22, MUTED))
            btn.setIconSize(QSize(22, 22))
            btn.setToolTip(STYLE_LABELS[key])
            btn.setCheckable(True)
            btn.setFixedSize(46, 46)
            btn.clicked.connect(lambda _checked, k=key: self._on_style(k))
            self._style_group.addButton(btn)
            self._style_btns[key] = btn
            grid.addWidget(btn, idx // cols, idx % cols)
        section.body_lay.addLayout(grid)

        self._style_name_lbl = QLabel("Speech")
        self._style_name_lbl.setObjectName("InspectorHint")
        self._style_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section.body_lay.addWidget(self._style_name_lbl)

        self._inspector_lay.addWidget(section)

    def _build_colors_section(self):
        section = AccordionSection("COLORS")
        self._fill_btn, self._fill_hex = self._color_row(
            section.body_lay, "Fill", QColor(255, 255, 255), self._on_fill_color,
            tooltip="Bubble fill color — click to pick"
        )
        self._stroke_btn, self._stroke_hex = self._color_row(
            section.body_lay, "Stroke", QColor(0, 0, 0), self._on_border_color,
            tooltip="Bubble outline/stroke color"
        )
        self._inspector_lay.addWidget(section)

    def _build_typography_section(self):
        section = AccordionSection("TYPOGRAPHY")

        row = QHBoxLayout()
        self._font_row_layout = row
        self._font_combo_placeholder = QWidget()
        self._font_combo_placeholder.setFixedHeight(32)
        self._font_combo_placeholder.setToolTip("Font family")
        row.addWidget(self._font_combo_placeholder, stretch=1)
        QTimer.singleShot(0, self._create_font_combo)

        self._weight_combo = QComboBox()
        self._weight_combo.addItems(("Regular", "Bold", "Italic", "Bold Italic"))
        self._weight_combo.setFixedWidth(90)
        self._weight_combo.setToolTip("Font weight")
        self._weight_combo.currentIndexChanged.connect(self._on_font_weight)
        row.addWidget(self._weight_combo)
        section.body_lay.addLayout(row)

        row2 = QHBoxLayout()
        self._font_size = QSpinBox()
        self._font_size.setRange(6, 96)
        self._font_size.setSuffix(" px")
        self._font_size.setFixedWidth(72)
        self._font_size.setToolTip("Font size in pixels")
        self._font_size.valueChanged.connect(self._on_font_size)
        row2.addWidget(self._font_size)

        self._text_color_btn = QPushButton()
        self._text_color_btn.setFixedSize(28, 28)
        self._text_color_btn.setToolTip("Text color — click to pick")
        self._text_color_btn.clicked.connect(self._on_text_color)
        row2.addWidget(self._text_color_btn)

        # Text alignment buttons — distinct labels + tooltips
        self._align_group = QButtonGroup(self)
        self._align_group.setExclusive(True)
        self._align_btns = {}
        ALIGN_OPTIONS = (
            ("L", int(Qt.AlignmentFlag.AlignLeft),    "Align text left"),
            ("C", int(Qt.AlignmentFlag.AlignCenter),  "Center text"),
            ("R", int(Qt.AlignmentFlag.AlignRight),   "Align text right"),
            ("J", int(Qt.AlignmentFlag.AlignJustify), "Justify text"),
        )
        for label, alignment, tip in ALIGN_OPTIONS:
            btn = QToolButton()
            btn.setObjectName("AlignButton")
            btn.setText(label)
            btn.setCheckable(True)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _checked, a=alignment: self._on_alignment(a))
            self._align_group.addButton(btn)
            self._align_btns[alignment] = btn
            row2.addWidget(btn)

        row2.addStretch()
        section.body_lay.addLayout(row2)
        self._inspector_lay.addWidget(section)

    def _build_tail_section(self):
        section = AccordionSection("TAIL")
        row = QHBoxLayout()
        row.addWidget(self._label("Position"))
        self._tail_position = QComboBox()
        self._tail_position.addItems(TAIL_POSITIONS)
        self._tail_position.setToolTip("Tail attachment position on the bubble")
        self._tail_position.currentTextChanged.connect(self._on_tail_position)
        row.addWidget(self._tail_position, stretch=1)
        section.body_lay.addLayout(row)
        self._tail_width = self._slider_row(
            section.body_lay, "Width", 6, 80, 26, " px", self._on_tail_width,
            tooltip="Width of the tail at its base in pixels"
        )
        self._inspector_lay.addWidget(section)

    def _build_stroke_section(self):
        section = AccordionSection("STROKE")
        self._border_width = QDoubleSpinBox()
        self._border_width.setRange(0.0, 12.0)
        self._border_width.setSingleStep(0.5)
        self._border_width.setSuffix(" px")
        self._border_width.setToolTip("Bubble outline stroke width in pixels")
        self._border_width.valueChanged.connect(self._on_border_width)
        row = QHBoxLayout()
        row.addWidget(self._label("Width"))
        row.addWidget(self._border_width)
        row.addStretch()
        section.body_lay.addLayout(row)
        self._inspector_lay.addWidget(section)

    def _build_shadow_section(self):
        section = AccordionSection("SHADOW", checkable=True)
        section.check.setToolTip("Enable drop shadow")
        section.check.toggled.connect(self._on_shadow_enabled)
        self._shadow_check = section.check

        self._shadow_color_btn, _ = self._color_row(
            section.body_lay, "Color", QColor(0, 0, 0), self._on_shadow_color,
            tooltip="Shadow color"
        )
        self._shadow_blur = self._slider_row(
            section.body_lay, "Blur", 0, 40, 12, " px", self._on_shadow_blur,
            tooltip="Shadow blur radius in pixels"
        )
        offset = QHBoxLayout()
        offset.addWidget(self._label("Offset"))
        self._shadow_x = QSpinBox()
        self._shadow_x.setRange(-80, 80)
        self._shadow_x.setPrefix("X ")
        self._shadow_x.setSuffix(" px")
        self._shadow_x.setToolTip("Shadow horizontal offset")
        self._shadow_x.valueChanged.connect(self._on_shadow_offset)
        self._shadow_y = QSpinBox()
        self._shadow_y.setRange(-80, 80)
        self._shadow_y.setPrefix("Y ")
        self._shadow_y.setSuffix(" px")
        self._shadow_y.setToolTip("Shadow vertical offset")
        self._shadow_y.valueChanged.connect(self._on_shadow_offset)
        offset.addWidget(self._shadow_x)
        offset.addWidget(self._shadow_y)
        section.body_lay.addLayout(offset)
        self._shadow_opacity = self._slider_row(
            section.body_lay, "Opacity", 0, 100, 80, " %", self._on_shadow_opacity,
            tooltip="Shadow opacity (0 = invisible, 100 = fully opaque)"
        )
        self._inspector_lay.addWidget(section)

    def _build_dual_section(self):
        section = AccordionSection("DUAL MODE")
        self._dual_section = section
        self._dual_gap_slider = self._slider_row(
            section.body_lay, "Gap", 0, 60, 4, " px", self._on_dual_gap,
            tooltip="Gap between left and right panels in pixels"
        )
        self._dual_feather_slider = self._slider_row(
            section.body_lay, "Feather", 0, 40, 0, " px", self._on_dual_feather,
            tooltip="Feather/blend amount at the divider edge"
        )
        row = QHBoxLayout()
        self._chk_dual_border = QCheckBox("Divider")
        self._chk_dual_border.setToolTip("Show a divider line between panels")
        self._chk_dual_border.toggled.connect(self._on_dual_border_toggle)
        row.addWidget(self._chk_dual_border)
        self._btn_dual_border_color = QPushButton()
        self._btn_dual_border_color.setFixedSize(34, 28)
        self._btn_dual_border_color.setToolTip("Divider color")
        _set_btn_color(self._btn_dual_border_color, self._dual_border_color_val)
        self._btn_dual_border_color.clicked.connect(self._on_dual_border_color)
        row.addWidget(self._btn_dual_border_color)
        self._dual_border_width = QDoubleSpinBox()
        self._dual_border_width.setRange(0.0, 8.0)
        self._dual_border_width.setSingleStep(0.5)
        self._dual_border_width.setSuffix(" px")
        self._dual_border_width.setToolTip("Divider width in pixels")
        self._dual_border_width.valueChanged.connect(self._on_dual_border_width)
        row.addWidget(self._dual_border_width)
        section.body_lay.addLayout(row)
        section.setVisible(False)
        self._inspector_lay.addWidget(section)

    # ------------------------------------------------------------------
    # Deferred font combo
    # ------------------------------------------------------------------

    def _create_font_combo(self):
        from PyQt6.QtWidgets import QFontComboBox
        self._font_combo = QFontComboBox()
        self._font_combo.setFixedHeight(32)
        self._font_combo.setToolTip("Font family")
        self._font_combo.currentFontChanged.connect(self._on_font_family)
        idx = self._font_row_layout.indexOf(self._font_combo_placeholder)
        if idx >= 0:
            self._font_row_layout.removeWidget(self._font_combo_placeholder)
            self._font_combo_placeholder.deleteLater()
            self._font_row_layout.insertWidget(idx, self._font_combo, 1)
        self._font_combo_placeholder = None
        if self._bubble is not None:
            self._font_combo.setCurrentFont(self._bubble.get_font())
        self._font_combo.setEnabled(self._bubble is not None)

    # ------------------------------------------------------------------
    # Helper widgets
    # ------------------------------------------------------------------

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("InspectorLabel")
        return label

    def _color_row(self, layout, label_text, color, callback, tooltip=""):
        row = QHBoxLayout()
        row.addWidget(self._label(label_text))
        btn = QPushButton()
        btn.setFixedSize(30, 24)
        btn.setToolTip(tooltip)
        _set_btn_color(btn, color)
        btn.clicked.connect(callback)
        row.addWidget(btn)
        hex_label = QLabel(color.name().upper())
        hex_label.setObjectName("InspectorHint")
        row.addWidget(hex_label, stretch=1)
        layout.addLayout(row)
        return btn, hex_label

    def _slider_row(self, layout, label_text, low, high, value, suffix,
                    callback, tooltip=""):
        row = QHBoxLayout()
        row.addWidget(self._label(label_text))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(value)
        slider.setToolTip(tooltip)
        row.addWidget(slider, stretch=1)
        value_box = QSpinBox()
        value_box.setRange(low, high)
        value_box.setValue(value)
        value_box.setSuffix(suffix)
        value_box.setFixedWidth(70)
        value_box.setToolTip(tooltip)
        row.addWidget(value_box)
        slider.valueChanged.connect(value_box.setValue)
        value_box.valueChanged.connect(slider.setValue)
        value_box.valueChanged.connect(callback)
        layout.addLayout(row)
        return value_box

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _stack_tab(self, index: int):
        self._stack.setCurrentIndex(index)
        if index == 1:
            self._refresh_layers()

    # ------------------------------------------------------------------
    # Public update API
    # ------------------------------------------------------------------

    def update_for_bubble(self, bubble):
        self._bubble = bubble
        self._media  = None
        self._dual_section.setVisible(False)
        self._set_controls_enabled(True)
        self._updating = True
        try:
            self._text_edit.setPlainText(bubble.get_text())
            self._update_char_count()
            style = bubble.get_style()
            for key, btn in self._style_btns.items():
                btn.setChecked(key == style)
            self._style_name_lbl.setText(STYLE_LABELS.get(style, style))
            self._set_color(self._fill_btn, self._fill_hex, bubble.get_fill_color())
            self._set_color(self._stroke_btn, self._stroke_hex, bubble.get_border_color())
            font = bubble.get_font()
            if self._font_combo is not None:
                self._font_combo.setCurrentFont(font)
            self._font_size.setValue(max(6, font.pointSize()))
            if font.bold() and font.italic():
                self._weight_combo.setCurrentText("Bold Italic")
            elif font.bold():
                self._weight_combo.setCurrentText("Bold")
            elif font.italic():
                self._weight_combo.setCurrentText("Italic")
            else:
                self._weight_combo.setCurrentText("Regular")
            self._set_color(self._text_color_btn, None, bubble.get_text_color())
            alignment = bubble.get_text_alignment()
            if alignment in self._align_btns:
                self._align_btns[alignment].setChecked(True)
            self._tail_position.setCurrentText(bubble.get_tail_position())
            self._tail_width.setValue(bubble.get_tail_width())
            self._border_width.setValue(bubble.get_border_width())
            self._set_shadow_controls(bubble.get_shadow())
        finally:
            self._updating = False
        self._refresh_layers()

    def update_for_media(self, media_item):
        self._bubble = None
        self._media  = media_item
        self._dual_section.setVisible(False)
        self._set_controls_enabled(False)
        self._refresh_layers()

    def show_dual_settings(self):
        self._bubble = None
        self._media  = None
        self._set_controls_enabled(False)
        self._dual_section.setVisible(True)

    def clear(self):
        self._bubble = None
        self._media  = None
        self._dual_section.setVisible(False)
        self._set_controls_enabled(False)
        self._refresh_layers()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_controls_enabled(self, enabled: bool):
        for widget in (
            self._text_section, self._fill_btn, self._stroke_btn,
            self._font_size, self._weight_combo, self._text_color_btn,
            self._tail_position, self._tail_width, self._border_width,
            self._shadow_check,
        ):
            if hasattr(widget, "setEnabled"):
                widget.setEnabled(enabled)
        for btn in self._style_btns.values():
            btn.setEnabled(enabled)
        for btn in self._align_btns.values():
            btn.setEnabled(enabled)
        if self._font_combo is not None:
            self._font_combo.setEnabled(enabled)

    def _set_color(self, btn, label, color):
        _set_btn_color(btn, color)
        if label is not None:
            label.setText(color.name().upper())

    def _on_text_changed(self):
        if self._updating:
            return
        text = self._text_edit.toPlainText()
        if len(text) > 200:
            self._text_edit.blockSignals(True)
            self._text_edit.setPlainText(text[:200])
            cursor = self._text_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._text_edit.setTextCursor(cursor)
            self._text_edit.blockSignals(False)
        self._update_char_count()

    def _update_char_count(self):
        self._char_count.setText(f"{len(self._text_edit.toPlainText())} / 200")

    def _on_text_committed(self, old: str, new: str):
        if self._bubble and self._undo_stack and old != new:
            self._undo_stack.push(TextChangeCommand(self._bubble, old, new))

    def _on_style(self, style: str):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_style()
            if old != style:
                self._undo_stack.push(StyleChangeCommand(self._bubble, old, style))
                self._style_name_lbl.setText(STYLE_LABELS.get(style, style))

    def _on_font_family(self, font: QFont):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_font()
            new = QFont(old)
            new.setFamily(font.family())
            self._undo_stack.push(FontChangeCommand(self._bubble, old, new))

    def _on_font_size(self, size: int):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_font()
            new = QFont(old)
            new.setPointSize(size)
            self._undo_stack.push(FontChangeCommand(self._bubble, old, new))

    def _on_font_weight(self):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_font()
            new = QFont(old)
            value = self._weight_combo.currentText()
            new.setBold("Bold" in value)
            new.setItalic("Italic" in value)
            self._undo_stack.push(FontChangeCommand(self._bubble, old, new))

    def _on_text_color(self):
        if not self._bubble or not self._undo_stack:
            return
        old   = self._bubble.get_text_color()
        color = QColorDialog.getColor(old, self, "Text Color")
        if color.isValid():
            self._undo_stack.push(TextColorChangeCommand(self._bubble, old, color))
            self._set_color(self._text_color_btn, None, color)

    def _on_alignment(self, alignment: int):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_text_alignment()
            if old != alignment:
                self._undo_stack.push(
                    TextAlignmentChangeCommand(self._bubble, old, alignment)
                )

    def _on_fill_color(self):
        if not self._bubble or not self._undo_stack:
            return
        old = self._bubble.get_fill_color()
        color = QColorDialog.getColor(
            old, self, "Fill Color", QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self._undo_stack.push(FillColorChangeCommand(self._bubble, old, color))
            self._set_color(self._fill_btn, self._fill_hex, color)

    def _on_border_color(self):
        if not self._bubble or not self._undo_stack:
            return
        old = self._bubble.get_border_color()
        color = QColorDialog.getColor(old, self, "Stroke Color")
        if color.isValid():
            self._undo_stack.push(BorderColorChangeCommand(self._bubble, old, color))
            self._set_color(self._stroke_btn, self._stroke_hex, color)

    def _on_border_width(self, value: float):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_border_width()
            if old != value:
                self._undo_stack.push(BorderWidthChangeCommand(self._bubble, old, value))

    def _on_tail_position(self, position: str):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_tail_position()
            if old != position:
                self._undo_stack.push(
                    TailPositionChangeCommand(self._bubble, old, position)
                )

    def _on_tail_width(self, width: int):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_tail_width()
            if old != width:
                self._undo_stack.push(TailWidthChangeCommand(self._bubble, old, width))

    def _set_shadow_controls(self, shadow: dict):
        self._shadow_check.setChecked(bool(shadow["enabled"]))
        self._set_color(self._shadow_color_btn, None, shadow["color"])
        self._shadow_blur.setValue(int(shadow["blur"]))
        self._shadow_x.setValue(int(shadow["offset_x"]))
        self._shadow_y.setValue(int(shadow["offset_y"]))
        self._shadow_opacity.setValue(int(shadow["opacity"]))

    def _shadow_update(self, **changes):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_shadow()
            new = dict(old)
            new.update(changes)
            self._undo_stack.push(ShadowChangeCommand(self._bubble, old, new))

    def _on_shadow_enabled(self, checked: bool):
        self._shadow_update(enabled=checked)

    def _on_shadow_color(self):
        if not self._bubble:
            return
        old   = self._bubble.get_shadow()
        color = QColorDialog.getColor(old["color"], self, "Shadow Color")
        if color.isValid():
            self._shadow_update(color=color)
            self._set_color(self._shadow_color_btn, None, color)

    def _on_shadow_blur(self, value: int):
        self._shadow_update(blur=value)

    def _on_shadow_offset(self):
        self._shadow_update(
            offset_x=self._shadow_x.value(),
            offset_y=self._shadow_y.value()
        )

    def _on_shadow_opacity(self, value: int):
        self._shadow_update(opacity=value)

    # ------------------------------------------------------------------
    # Layers tab
    # ------------------------------------------------------------------

    def _refresh_layers(self):
        if self._scene is None or not hasattr(self, "_layers_list"):
            return
        self._layers_list.blockSignals(True)
        self._layers_list.clear()
        self._layer_items = {}
        items = []
        for item in self._scene.items():
            if isinstance(item, BubbleItem):
                label = item.get_text().splitlines()[0][:28] or "Bubble"
                items.append((item.zValue(), item, f"Bubble: {label}"))
            elif isinstance(item, MediaItem) and getattr(item, "_is_overlay", False):
                items.append((item.zValue(), item, "Overlay layer"))
        for _z, item, label in sorted(items, key=lambda row: row[0], reverse=True):
            list_item = QListWidgetItem(label)
            list_item.setFlags(
                list_item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            list_item.setCheckState(
                Qt.CheckState.Checked if item.isVisible() else Qt.CheckState.Unchecked
            )
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._layers_list.addItem(list_item)
            self._layer_items[item] = list_item
            if item.isSelected():
                list_item.setSelected(True)
        self._layers_list.blockSignals(False)

    def _on_layer_item_changed(self, list_item):
        item = list_item.data(Qt.ItemDataRole.UserRole)
        if item is not None:
            item.setVisible(list_item.checkState() == Qt.CheckState.Checked)

    def _on_layer_selection(self):
        if self._scene is None or self._layers_list.signalsBlocked():
            return
        selected = self._layers_list.selectedItems()
        if not selected:
            return
        item = selected[0].data(Qt.ItemDataRole.UserRole)
        if item is not None:
            self._scene.clearSelection()
            item.setSelected(True)

    # ------------------------------------------------------------------
    # Dual mode
    # ------------------------------------------------------------------

    def _on_dual_gap(self, value: int):
        if not self._updating:
            self.dual_gap_changed.emit(value)

    def _on_dual_border_toggle(self, checked: bool):
        if not self._updating:
            width = self._dual_border_width.value() if checked else 0.0
            self.dual_border_changed.emit(self._dual_border_color_val, width)

    def _on_dual_border_color(self):
        color = QColorDialog.getColor(
            self._dual_border_color_val, self, "Divider Color"
        )
        if color.isValid():
            self._dual_border_color_val = color
            _set_btn_color(self._btn_dual_border_color, color)
            if self._chk_dual_border.isChecked():
                self.dual_border_changed.emit(color, self._dual_border_width.value())

    def _on_dual_border_width(self, value: float):
        if not self._updating and self._chk_dual_border.isChecked():
            self.dual_border_changed.emit(self._dual_border_color_val, value)

    def _on_dual_feather(self, value: int):
        if not self._updating:
            self.dual_feather_changed.emit(value)
