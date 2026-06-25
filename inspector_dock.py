"""
inspector_dock.py — v4 right inspector with accordion sections and layers (v4 redesign).

Key changes from v3:
  - AccordionSection uses clean text headers without decorative chevron buttons
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
    QCheckBox, QListWidget, QListWidgetItem, QSizePolicy,
)
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF, QRectF

from bubble import BubbleItem
from media_item import MediaItem
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
# StylePreviewButton
# ---------------------------------------------------------------------------

class StylePreviewButton(QToolButton):
    """Paints a real bubble preview instead of using tiny text/SVG glyphs."""

    def __init__(self, style: str, parent=None):
        super().__init__(parent)
        self._style = style
        self.setObjectName("StyleButton")
        self.setCheckable(True)
        self.setFixedSize(46, 42)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.isEnabled():
            bg = QColor("#1a1f2e")
            border = QColor("#252d3d")
            stroke = QColor("#4e5a6e")
        elif self.isChecked():
            bg = QColor(70, 221, 203, 32)
            border = QColor("#46ddcb")
            stroke = QColor("#46ddcb")
        elif self.underMouse():
            bg = QColor("#2a3347")
            border = QColor("#3a4d66")
            stroke = QColor("#e8ecf4")
        else:
            bg = QColor("#252d3d")
            border = QColor("#2e3a50")
            stroke = QColor("#e8ecf4")

        outer = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(border, 1.4))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(outer, 7, 7)

        painter.setPen(QPen(stroke, 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self._paint_preview(painter, stroke)

    def _paint_preview(self, painter: QPainter, stroke: QColor):
        r = QRectF(10, 9, 25, 17)
        if self._style == "oval":
            p = QPainterPath()
            p.moveTo(r.left() + 10, r.top())
            p.cubicTo(r.right() - 5, r.top() - 2, r.right() + 1, r.top() + 7,
                      r.right() - 1, r.center().y())
            p.cubicTo(r.right() - 1, r.bottom() + 2, r.left() + 9, r.bottom() + 3,
                      r.left() + 3, r.center().y() + 4)
            p.cubicTo(r.left() - 2, r.center().y() - 2, r.left() + 2, r.top() + 2,
                      r.left() + 10, r.top())
            p.closeSubpath()
            tail = QPainterPath()
            tail.moveTo(r.left() + 17, r.bottom() - 1)
            tail.cubicTo(r.left() + 23, r.bottom() + 8, r.left() + 27, r.bottom() + 9,
                         r.left() + 21, r.bottom() - 2)
            painter.drawPath(p.united(tail))
        elif self._style == "cloud":
            p = QPainterPath()
            for x, y, rad in ((11, 19, 7), (17, 15, 8), (25, 15, 8),
                              (32, 19, 7), (25, 23, 7), (17, 23, 7)):
                p = p.united(QPainterPath())
                c = QPainterPath()
                c.addEllipse(QPointF(x, y), rad, rad)
                p = p.united(c)
            painter.drawPath(p)
            painter.setBrush(QBrush(stroke))
            painter.drawEllipse(QPointF(14, 31), 2.2, 2.2)
            painter.drawEllipse(QPointF(10, 35), 1.4, 1.4)
            painter.setBrush(Qt.BrushStyle.NoBrush)
        elif self._style == "rect":
            p = QPainterPath()
            p.addRoundedRect(QRectF(9, 10, 28, 18), 2, 2)
            tail = QPainterPath()
            tail.moveTo(17, 27)
            tail.lineTo(13, 34)
            tail.lineTo(23, 27)
            tail.closeSubpath()
            painter.drawPath(p.united(tail))
        elif self._style == "spiky":
            points = [
                QPointF(23, 7), QPointF(26, 13), QPointF(34, 11),
                QPointF(31, 18), QPointF(38, 22), QPointF(30, 24),
                QPointF(32, 32), QPointF(25, 28), QPointF(21, 35),
                QPointF(18, 28), QPointF(10, 31), QPointF(13, 24),
                QPointF(7, 20), QPointF(14, 17), QPointF(12, 10),
                QPointF(19, 13),
            ]
            p = QPainterPath(points[0])
            for pt in points[1:]:
                p.lineTo(pt)
            p.closeSubpath()
            painter.drawPath(p)
        elif self._style == "text":
            f = QFont()
            f.setPixelSize(22)
            painter.setFont(f)
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), "T")
        elif self._style == "scrim":
            painter.drawRoundedRect(QRectF(8, 15, 30, 11), 2, 2)
            painter.drawLine(QPointF(14, 20.5), QPointF(32, 20.5))
        elif self._style == "caption":
            f = QFont()
            f.setPixelSize(8)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(QRectF(5, 11, 36, 10), int(Qt.AlignmentFlag.AlignCenter), "CAP")
            painter.drawLine(QPointF(11, 25), QPointF(35, 25))
            painter.drawLine(QPointF(15, 30), QPointF(31, 30))


# ---------------------------------------------------------------------------
# AccordionSection
# ---------------------------------------------------------------------------

class AccordionSection(QWidget):
    def __init__(self, title: str, parent=None, checkable: bool = False):
        super().__init__(parent)
        self.setObjectName("InspectorSection")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header row
        header_w = QWidget()
        header_w.setObjectName("InspectorSectionHeader")
        header_w.setFixedHeight(24)
        hbox = QHBoxLayout(header_w)
        hbox.setContentsMargins(14, 0, 10, 0)
        hbox.setSpacing(6)

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
        self.body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(10, 3, 10, 5)
        self.body_lay.setSpacing(4)
        outer.addWidget(self.body)

# ---------------------------------------------------------------------------
# InspectorDock
# ---------------------------------------------------------------------------

class InspectorDock(QWidget):
    dual_gap_changed    = pyqtSignal(int)
    dual_border_changed = pyqtSignal(QColor, float)
    dual_feather_changed = pyqtSignal(int)
    add_bubble_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(320)
        self.setMaximumWidth(380)
        self.setObjectName("InspectorDock")
        self._bubble     = None
        self._media      = None
        self._scene      = None
        self._undo_stack = None
        self._updating   = False
        self._font_combo = None
        self._layer_items = {}
        self._refreshing_layers = False
        self._dual_border_color_val = QColor("#3a4d66")
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
        inspector_page.setMinimumWidth(0)
        inspector_page.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._inspector_lay = QVBoxLayout(inspector_page)
        self._inspector_lay.setContentsMargins(0, 0, 0, 0)
        self._inspector_lay.setSpacing(0)
        self._build_inspector_sections()
        scroll.setWidget(inspector_page)
        self._stack.addWidget(scroll)

        layers_page = QWidget()
        layers_lay = QVBoxLayout(layers_page)
        layers_lay.setContentsMargins(8, 10, 8, 12)
        layers_lay.setSpacing(8)
        self._layers_list = QListWidget()
        self._layers_list.setObjectName("LayersList")
        self._layers_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._layers_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._layers_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._layers_list.itemChanged.connect(self._on_layer_item_changed)
        self._layers_list.itemSelectionChanged.connect(self._on_layer_selection)
        self._layers_list.model().rowsMoved.connect(self._on_layers_reordered)
        layers_lay.addWidget(self._layers_list)
        layer_actions = QHBoxLayout()
        for label, delta, tip in (
            ("Up", -1, "Move selected layer up"),
            ("Down", 1, "Move selected layer down"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("LayerActionButton")
            btn.setMinimumHeight(32)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _checked=False, d=delta: self._move_selected_layer(d))
            layer_actions.addWidget(btn)
        layers_lay.addLayout(layer_actions)
        self._stack.addWidget(layers_page)

    def _build_inspector_sections(self):
        self._build_text_section()
        self._build_bubble_section()
        self._build_colors_section()
        self._build_layer_section()
        self._build_typography_section()
        self._build_tail_section()
        self._build_stroke_section()
        self._build_shadow_section()
        self._build_dual_section()
        self._bubble_sections = (
            self._text_section, self._bubble_section, self._colors_section,
            self._typography_section, self._tail_section,
            self._shadow_section,
        )
        self._layer_section.setVisible(False)
        self._layer_section.setEnabled(False)
        self._set_bubble_sections_visible(True)
        self._set_controls_enabled(False)
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
        self._text_edit.setFixedHeight(50)
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

        # 7 style buttons in a grid that fits the fixed inspector width.
        grid = QGridLayout()
        grid.setSpacing(4)
        self._style_group = QButtonGroup(self)
        self._style_group.setExclusive(True)
        self._style_btns = {}
        styles = list(STYLE_LABELS.keys())
        cols = 4
        for idx, key in enumerate(styles):
            btn = StylePreviewButton(key)
            btn.setToolTip(STYLE_LABELS[key])
            btn.clicked.connect(lambda _checked, k=key: self._on_style(k))
            self._style_group.addButton(btn)
            self._style_btns[key] = btn
            grid.addWidget(btn, idx // cols, idx % cols)
        section.body_lay.addLayout(grid)

        self._bubble_section = section
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
        self._bubble_opacity = self._compact_slider_row(
            section.body_lay, "Opacity", 0, 100, 94, " %", self._on_bubble_opacity,
            tooltip="Bubble fill opacity"
        )
        self._colors_section = section
        self._inspector_lay.addWidget(section)

    def _build_layer_section(self):
        section = AccordionSection("LAYER")
        self._layer_opacity = self._compact_slider_row(
            section.body_lay, "Opacity", 0, 100, 100, " %", self._on_layer_opacity,
            tooltip="Selected image layer opacity"
        )
        self._layer_section = section
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
        self._weight_combo.setFixedWidth(86)
        self._weight_combo.setToolTip("Font weight")
        self._weight_combo.currentIndexChanged.connect(self._on_font_weight)
        row.addWidget(self._weight_combo)
        section.body_lay.addLayout(row)

        row2 = QHBoxLayout()
        self._font_size = QSpinBox()
        self._font_size.setRange(6, 96)
        self._font_size.setSuffix(" px")
        self._font_size.setFixedWidth(64)
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
        self._typography_section = section
        self._inspector_lay.addWidget(section)

    def _build_tail_section(self):
        section = AccordionSection("SHAPE")
        row = QHBoxLayout()
        row.addWidget(self._label("Tail"))
        self._tail_position = QComboBox()
        self._tail_position.addItems(TAIL_POSITIONS)
        self._tail_position.setToolTip("Tail attachment position on the bubble")
        self._tail_position.currentTextChanged.connect(self._on_tail_position)
        row.addWidget(self._tail_position, stretch=1)
        section.body_lay.addLayout(row)
        self._tail_width = self._spin_row(
            section.body_lay, "Width", 6, 80, 26, " px", self._on_tail_width,
            tooltip="Width of the tail at its base in pixels"
        )
        self._border_width = QDoubleSpinBox()
        self._border_width.setRange(0.0, 12.0)
        self._border_width.setSingleStep(0.5)
        self._border_width.setSuffix(" px")
        self._border_width.setFixedWidth(76)
        self._border_width.setToolTip("Bubble outline stroke width in pixels")
        self._border_width.valueChanged.connect(self._on_border_width)
        stroke_row = QHBoxLayout()
        stroke_row.addWidget(self._label("Stroke"))
        stroke_row.addStretch()
        stroke_row.addWidget(self._border_width)
        section.body_lay.addLayout(stroke_row)
        self._tail_section = section
        self._stroke_section = section
        self._inspector_lay.addWidget(section)

    def _build_stroke_section(self):
        return

    def _build_shadow_section(self):
        section = AccordionSection("SHADOW", checkable=True)
        section.check.setToolTip("Enable drop shadow")
        section.check.toggled.connect(self._on_shadow_enabled)
        self._shadow_check = section.check

        self._shadow_color_btn, _ = self._color_row(
            section.body_lay, "Color", QColor(0, 0, 0), self._on_shadow_color,
            tooltip="Shadow color"
        )
        self._shadow_blur = self._spin_row(
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
        self._shadow_opacity = self._compact_slider_row(
            section.body_lay, "Opacity", 0, 100, 80, " %", self._on_shadow_opacity,
            tooltip="Shadow opacity (0 = invisible, 100 = fully opaque)"
        )
        section.body.setVisible(False)
        self._shadow_section = section
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
        self._font_combo = QComboBox()
        self._font_combo.setEditable(True)
        self._font_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._font_combo.setFixedHeight(32)
        self._font_combo.setToolTip("Font family")
        families = sorted(QFontDatabase.families(), key=str.casefold)
        self._font_combo.addItems(families)
        self._font_combo.currentTextChanged.connect(self._on_font_family_name)
        idx = self._font_row_layout.indexOf(self._font_combo_placeholder)
        if idx >= 0:
            self._font_row_layout.removeWidget(self._font_combo_placeholder)
            self._font_combo_placeholder.deleteLater()
            self._font_row_layout.insertWidget(idx, self._font_combo, 1)
        self._font_combo_placeholder = None
        if self._bubble is not None:
            self._font_combo.blockSignals(True)
            self._set_font_combo_family(self._bubble.get_font().family())
            self._font_combo.blockSignals(False)
        self._font_combo.setEnabled(self._bubble is not None)
        self._font_combo.setMinimumContentsLength(8)

    def _set_font_combo_family(self, family: str):
        if self._font_combo is None:
            return
        idx = self._font_combo.findText(family, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self._font_combo.setCurrentIndex(idx)
        else:
            self._font_combo.setEditText(family)

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

    def _spin_row(self, layout, label_text, low, high, value, suffix,
                  callback, tooltip=""):
        row = QHBoxLayout()
        row.addWidget(self._label(label_text))
        row.addStretch()
        value_box = QSpinBox()
        value_box.setRange(low, high)
        value_box.setValue(value)
        value_box.setSuffix(suffix)
        value_box.setFixedWidth(76)
        value_box.setToolTip(tooltip)
        value_box.valueChanged.connect(callback)
        row.addWidget(value_box)
        layout.addLayout(row)
        return value_box

    def _compact_slider_row(self, layout, label_text, low, high, value, suffix,
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
        value_box.setFixedWidth(66)
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
        self._layer_section.setVisible(False)
        self._set_bubble_sections_visible(True)
        self._set_controls_enabled(True)
        self._updating = True
        try:
            self._text_edit.setPlainText(bubble.get_text())
            self._update_char_count()
            style = bubble.get_style()
            for key, btn in self._style_btns.items():
                btn.setChecked(key == style)
                btn.setToolTip(f"Change selected bubble to {STYLE_LABELS[key]}")
            self._set_color(self._fill_btn, self._fill_hex, bubble.get_fill_color())
            self._set_color(self._stroke_btn, self._stroke_hex, bubble.get_border_color())
            self._bubble_opacity.setValue(round(bubble.get_fill_color().alpha() * 100 / 255))
            font = bubble.get_font()
            if self._font_combo is not None:
                self._font_combo.setEnabled(True)
                self._font_combo.blockSignals(True)
                self._set_font_combo_family(font.family())
                self._font_combo.blockSignals(False)
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
        self._layer_section.setVisible(True)
        self._set_controls_enabled(False)
        self._enable_style_add_mode()
        self._layer_section.setEnabled(True)
        self._layer_opacity.setValue(round(media_item.opacity() * 100))
        self._refresh_layers()

    def show_dual_settings(self):
        self._bubble = None
        self._media  = None
        self._set_controls_enabled(False)
        self._layer_section.setEnabled(False)
        self._layer_section.setVisible(False)
        self._dual_section.setVisible(True)

    def clear(self):
        self._bubble = None
        self._media  = None
        self._dual_section.setVisible(False)
        self._set_controls_enabled(False)
        self._enable_style_add_mode()
        self._layer_section.setEnabled(False)
        self._layer_section.setVisible(False)
        self._refresh_layers()

    def clear_selection(self):
        self._bubble = None
        self._media = None
        self._dual_section.setVisible(False)
        self._set_controls_enabled(False)
        self._enable_style_add_mode()
        self._layer_section.setEnabled(False)
        self._layer_section.setVisible(False)
        self._refresh_layers()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_controls_enabled(self, enabled: bool):
        for widget in (
            self._text_section, self._fill_btn, self._stroke_btn,
            self._font_size, self._weight_combo, self._text_color_btn,
            self._tail_position, self._tail_width, self._border_width,
            self._shadow_check, self._shadow_color_btn, self._shadow_blur,
            self._shadow_x, self._shadow_y, self._shadow_opacity,
            self._bubble_opacity,
        ):
            if hasattr(widget, "setEnabled"):
                widget.setEnabled(enabled)
        for btn in self._style_btns.values():
            btn.setEnabled(enabled)
        for btn in self._align_btns.values():
            btn.setEnabled(enabled)

    def _enable_style_add_mode(self):
        can_add = (
            self._scene is not None
            and hasattr(self._scene, "has_photo")
            and self._scene.has_photo()
        )
        self._bubble_section.setEnabled(can_add)
        for btn in self._style_btns.values():
            btn.setEnabled(can_add)
            btn.setChecked(False)
        for key, btn in self._style_btns.items():
            btn.setToolTip(f"Add {STYLE_LABELS[key]}")
        if self._font_combo is not None:
            self._font_combo.setEnabled(False)
        self._layer_section.setEnabled(False)

    def _set_bubble_sections_visible(self, visible: bool):
        for section in getattr(self, "_bubble_sections", ()):
            section.setVisible(visible)

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
        elif (
            not self._updating
            and self._scene is not None
            and hasattr(self._scene, "has_photo")
            and self._scene.has_photo()
        ):
            self.add_bubble_requested.emit(style)

    def _on_font_family(self, font: QFont):
        if (
            self._bubble
            and not self._updating
            and self._undo_stack
            and (self._font_combo is None or self._font_combo.isEnabled())
        ):
            old = self._bubble.get_font()
            new = QFont(old)
            new.setFamily(font.family())
            self._undo_stack.push(FontChangeCommand(self._bubble, old, new))

    def _on_font_family_name(self, family: str):
        family = family.strip()
        if family:
            self._on_font_family(QFont(family))

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

    def _on_bubble_opacity(self, value: int):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_fill_color()
            new = QColor(old)
            new.setAlpha(round(max(0, min(100, value)) * 255 / 100))
            if old.alpha() != new.alpha():
                self._undo_stack.push(FillColorChangeCommand(self._bubble, old, new))
                self._set_color(self._fill_btn, self._fill_hex, new)

    def _on_layer_opacity(self, value: int):
        if self._media and not self._updating:
            self._media.setOpacity(max(0.0, min(1.0, value / 100.0)))

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
        self._shadow_section.body.setVisible(bool(shadow["enabled"]))
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
        self._shadow_section.body.setVisible(checked)
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
        self._refreshing_layers = True
        self._layers_list.blockSignals(True)
        self._layers_list.clear()
        self._layer_items = {}
        items = []
        try:
            scene_items = self._scene.items()
        except RuntimeError:
            self._layers_list.blockSignals(False)
            self._refreshing_layers = False
            return
        for item in scene_items:
            if isinstance(item, BubbleItem):
                label = item.get_text().splitlines()[0][:28] or "Bubble"
                items.append((item.zValue(), item, f"☰  Bubble  ·  {label}"))
            elif isinstance(item, MediaItem) and getattr(item, "_is_overlay", False):
                items.append((item.zValue(), item, "☰  Image layer"))
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
        self._refreshing_layers = False

    def _normalize_layer_z_values(self):
        if self._scene is None:
            return
        items = []
        for item in self._scene.items():
            if isinstance(item, BubbleItem):
                items.append(item)
            elif isinstance(item, MediaItem) and getattr(item, "_is_overlay", False):
                items.append(item)
        for idx, item in enumerate(sorted(items, key=lambda i: i.zValue())):
            item.setZValue(float(10 + idx * 10))

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

    def _on_layers_reordered(self, *_args):
        if self._scene is None or self._refreshing_layers:
            return
        count = self._layers_list.count()
        selected_item = None
        for row in range(count):
            item = self._layers_list.item(row).data(Qt.ItemDataRole.UserRole)
            if item is not None:
                item.setZValue(float(10 + (count - row - 1) * 10))
                if self._layers_list.item(row).isSelected():
                    selected_item = item
        self._scene.update()
        self._refresh_layers()
        if selected_item is not None:
            selected_item.setSelected(True)

    def _move_selected_layer(self, delta: int):
        target = None
        if self._scene is not None:
            selected_scene_items = [
                item for item in self._scene.selectedItems()
                if isinstance(item, BubbleItem)
                or (isinstance(item, MediaItem) and getattr(item, "_is_overlay", False))
            ]
            if selected_scene_items:
                target = selected_scene_items[0]
        if target is None and self._layers_list.currentItem() is not None:
            target = self._layers_list.currentItem().data(Qt.ItemDataRole.UserRole)
        if target is None:
            return
        for i in range(self._layers_list.count()):
            if self._layers_list.item(i).data(Qt.ItemDataRole.UserRole) is target:
                self._layers_list.blockSignals(True)
                self._layers_list.setCurrentRow(i)
                self._layers_list.blockSignals(False)
                break
        row = self._layers_list.currentRow()
        if row < 0:
            return
        new_row = max(0, min(self._layers_list.count() - 1, row + delta))
        if new_row == row:
            return
        self._refreshing_layers = True
        self._layers_list.blockSignals(True)
        item = self._layers_list.takeItem(row)
        self._layers_list.insertItem(new_row, item)
        self._layers_list.setCurrentRow(new_row)
        self._layers_list.blockSignals(False)
        self._refreshing_layers = False
        self._on_layers_reordered()

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
