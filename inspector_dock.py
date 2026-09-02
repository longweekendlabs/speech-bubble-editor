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

import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabBar, QStackedWidget,
    QLabel, QScrollArea, QFrame, QToolButton, QPushButton, QButtonGroup,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QColorDialog,
    QCheckBox, QListWidget, QListWidgetItem, QSizePolicy, QMenu, QApplication,
    QWidgetAction, QInputDialog, QMessageBox,
)
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QPainter, QPainterPath,
                         QPen, QBrush, QPixmap)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF, QRectF

import bubble_defaults
from bubble import BubbleItem, TEXT_PRESETS, TAIL_SHAPES
from media_item import MediaItem
from redaction import RedactionItem
from speedlines import SpeedLinesItem
from undo_commands import (
    TextChangeCommand, StyleChangeCommand, FontChangeCommand,
    FillColorChangeCommand, BorderColorChangeCommand,
    BorderWidthChangeCommand, TextColorChangeCommand,
    TextAlignmentChangeCommand, TailPositionChangeCommand,
    TailWidthChangeCommand, ShadowChangeCommand, MoveBubbleCommand,
    ZValueChangeCommand, TailShapeChangeCommand, TailCountChangeCommand,
    TextOutlineChangeCommand, InsetPhotoCommand,
)


STYLE_LABELS = {
    # Authored SVG shapes first — these are the good ones.
    "oval":    "Speech",
    "round":   "Round",
    "blob":    "Blob",
    "softbox": "Soft box",
    "wobble":  "Shaky",
    "puffy":   "Puffy",
    "explode": "Explode",
    "panel":   "Panel",
    "twin":    "Twin",
    "triple":  "Triple",
    # Procedural shapes.
    "cloud":   "Cloud",
    "spiky":   "Starburst",
    "burst":   "Burst",
    "scallop": "Scallop",
    "rect":    "Rectangle",
    "wobbly":  "Hand-drawn",
    # Text-only styles (no balloon body).
    "text":    "Text only",
    "scrim":   "Scrim",
    "caption": "Caption",
}

TAIL_SHAPE_LABELS = {
    "wedge":  "Wedge tail",
    "curved": "Curved swoosh tail",
    "line":   "Thin line tail",
    "dots":   "Thought dots",
    "none":   "No tail",
}


class OptionButtonGrid(QWidget):
    """Compact exclusive choices that keep every option visible."""

    currentTextChanged = pyqtSignal(str)

    def __init__(self, choices, columns=3, tooltips=None, parent=None):
        super().__init__(parent)
        self._value = ""
        self._buttons = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(5)
        grid.setVerticalSpacing(5)
        tooltips = tuple(tooltips or ())
        for index, choice in enumerate(choices):
            value, label = choice if isinstance(choice, tuple) else (choice, choice)
            btn = QToolButton()
            btn.setObjectName("PageOptionButton")
            btn.setText(str(label))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding,
                              QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(30)
            if index < len(tooltips):
                btn.setToolTip(tooltips[index])
            self._group.addButton(btn)
            self._buttons[str(value)] = btn
            btn.clicked.connect(
                lambda checked, selected=str(value):
                checked and self._select_from_user(selected))
            grid.addWidget(btn, index // columns, index % columns)
        if self._buttons:
            self.setCurrentText(next(iter(self._buttons)))

    def _select_from_user(self, value: str):
        self._value = value
        self.currentTextChanged.emit(value)

    def currentText(self) -> str:
        return self._value

    def setCurrentText(self, value: str):
        value = str(value)
        btn = self._buttons.get(value)
        if btn is None:
            return
        self._value = value
        btn.setChecked(True)

    def clearSelection(self):
        self._group.setExclusive(False)
        for btn in self._buttons.values():
            btn.setChecked(False)
        self._group.setExclusive(True)
        self._value = ""

    def option_button(self, value: str):
        return self._buttons.get(str(value))


class PhotoCountStepper(QWidget):
    """Google-Photos-style add/remove control for collage slots."""

    valueChanged = pyqtSignal(int)

    def __init__(self, value=4, parent=None):
        super().__init__(parent)
        self._value = max(2, min(9, int(value)))
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self._remove = QPushButton("−")
        self._add = QPushButton("+")
        for btn in (self._remove, self._add):
            btn.setObjectName("PhotoCountButton")
            btn.setFixedSize(34, 30)
        self._remove.setToolTip("Remove one empty photo slot")
        self._add.setToolTip("Add one photo slot")
        self._label = QLabel()
        self._label.setObjectName("PhotoCountLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._remove)
        row.addWidget(self._label, stretch=1)
        row.addWidget(self._add)
        self._remove.clicked.connect(lambda: self.setValue(self._value - 1))
        self._add.clicked.connect(lambda: self.setValue(self._value + 1))
        self._sync()

    def value(self):
        return self._value

    def setValue(self, value):
        value = max(2, min(9, int(value)))
        if value == self._value:
            self._sync()
            return
        self._value = value
        self._sync()
        self.valueChanged.emit(value)

    def _sync(self):
        self._label.setText(f"{self._value} photos")
        self._remove.setEnabled(self._value > 2)
        self._add.setEnabled(self._value < 9)


class CollageTemplateButton(QToolButton):
    """A template thumbnail that communicates geometry without terminology."""

    def __init__(self, layout_type: str, label: str, parent=None):
        super().__init__(parent)
        self.layout_type = layout_type
        self.label = label
        self._vertical = True
        self.setCheckable(True)
        self.setFixedSize(62, 70)
        self.setToolTip(f"Use the {label.lower()} layout")

    def set_vertical(self, vertical: bool):
        self._vertical = bool(vertical)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isChecked()
        hovered = self.underMouse()
        border = QColor("#ff7a45") if selected else QColor(
            "#5d7898" if hovered else "#35475c")
        painter.setPen(QPen(border, 1.5))
        painter.setBrush(QColor(255, 122, 69, 28) if selected else QColor("#1c2938"))
        painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 6, 6)

        if self._vertical:
            page = QRectF(18, 7, 26, 42)
        else:
            page = QRectF(9, 12, 44, 32)
        painter.setPen(QPen(QColor("#65758b"), 1))
        painter.setBrush(QColor("#0b1119"))
        painter.drawRect(page)
        gap = 2.0
        fill = QColor("#dbe5f0") if selected else QColor("#8190a4")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        x, y, w, h = page.x() + 2, page.y() + 2, page.width() - 4, page.height() - 4
        if self.layout_type == "Grid":
            painter.drawRect(QRectF(x, y, (w-gap)/2, (h-gap)/2))
            painter.drawRect(QRectF(x+(w+gap)/2, y, (w-gap)/2, (h-gap)/2))
            painter.drawRect(QRectF(x, y+(h+gap)/2, (w-gap)/2, (h-gap)/2))
            painter.drawRect(QRectF(x+(w+gap)/2, y+(h+gap)/2, (w-gap)/2, (h-gap)/2))
        elif self.layout_type == "Mosaic":
            painter.drawRect(QRectF(x, y, w*0.58-gap/2, h))
            painter.drawRect(QRectF(x+w*0.58+gap/2, y, w*0.42-gap/2, (h-gap)/2))
            painter.drawRect(QRectF(x+w*0.58+gap/2, y+(h+gap)/2,
                                    w*0.42-gap/2, (h-gap)/2))
        elif self.layout_type == "Hero":
            painter.drawRect(QRectF(x, y, w, h*0.58-gap/2))
            third = (w-gap*2)/3
            for index in range(3):
                painter.drawRect(QRectF(x+index*(third+gap), y+h*0.58+gap/2,
                                        third, h*0.42-gap/2))
        else:
            if self._vertical:
                cell = (h-gap*2)/3
                for index in range(3):
                    painter.drawRect(QRectF(x, y+index*(cell+gap), w, cell))
            else:
                cell = (w-gap*2)/3
                for index in range(3):
                    painter.drawRect(QRectF(x+index*(cell+gap), y, cell, h))

        painter.setPen(QColor("#ff9a70") if selected else QColor("#acb9c8"))
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(selected)
        painter.setFont(font)
        painter.drawText(QRectF(2, 51, self.width()-4, 16),
                         int(Qt.AlignmentFlag.AlignCenter), self.label)


class CollageTemplateStrip(QWidget):
    currentTextChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = ""
        self._buttons = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        for layout_type, label in (("Grid", "Grid"), ("Mosaic", "Mosaic"),
                                   ("Hero", "Hero"), ("Filmstrip", "Strip")):
            btn = CollageTemplateButton(layout_type, label)
            self._buttons[layout_type] = btn
            self._group.addButton(btn)
            row.addWidget(btn)
            btn.clicked.connect(
                lambda checked, value=layout_type:
                checked and self._select(value))
        self.setCurrentText("Mosaic")

    def _select(self, value):
        self._value = value
        self.currentTextChanged.emit(value)

    def currentText(self):
        return self._value

    def setCurrentText(self, value):
        btn = self._buttons.get(str(value))
        if btn is None:
            return
        self._value = str(value)
        btn.setChecked(True)

    def set_vertical(self, vertical):
        for btn in self._buttons.values():
            btn.set_vertical(vertical)

    def option_button(self, value):
        return self._buttons.get(str(value))

# Balloon+-style swatch palette: vivid / dark / muted / pale / extras.
# The first entry of the last row is fully transparent.
PALETTE = [
    ["#000000", "#e02020", "#108030", "#2040d0", "#f0d000", "#f08000", "#b830b8"],
    ["#505050", "#801010", "#104818", "#101870", "#909010", "#904810", "#581078"],
    ["#a0a0a0", "#b08cba", "#8cb094", "#7ca8b0", "#a8a87c", "#b09878", "#9c8cc4"],
    ["#ffffff", "#ffd9f7", "#d9ffd9", "#d2ffff", "#ffffd2", "#ffe9d2", "#ead9ff"],
    [None,      "#ff00ff", "#00e020", "#00e0e0", "#828200", "#b07830", "#7010c0"],
]


class SwatchButton(QPushButton):
    """Flat colour swatch; transparent swatches show a checkerboard."""

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Transparent" if color.alpha() == 0
                        else color.name().upper())

    def color(self) -> QColor:
        return QColor(self._color)

    def paintEvent(self, event):
        p = QPainter(self)
        r = self.rect().adjusted(1, 1, -2, -2)
        if self._color.alpha() < 255:
            p.fillRect(r, QColor("#c8c8c8"))
            sq = 6
            for y in range(r.top(), r.bottom(), sq):
                for x in range(r.left(), r.right(), sq):
                    if ((x - r.left()) // sq + (y - r.top()) // sq) % 2 == 0:
                        p.fillRect(x, y, min(sq, r.right() - x + 1),
                                   min(sq, r.bottom() - y + 1), QColor("#8a8a8a"))
        p.fillRect(r, self._color)
        p.setPen(QPen(QColor("#ff7a45") if self.underMouse()
                      else QColor("#35475c"), 1))
        p.drawRect(r)


def pick_color(anchor: QWidget, initial: QColor, parent: QWidget,
               allow_alpha: bool = True) -> QColor | None:
    """Balloon+-style palette popup under `anchor`.

    Returns the picked colour, or None if dismissed. "Custom…" falls through
    to the full QColorDialog (with alpha when allowed).
    """
    menu = QMenu(parent)
    container = QWidget()
    lay = QVBoxLayout(container)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(6)
    grid = QGridLayout()
    grid.setSpacing(4)
    result: dict = {}

    for row, colors in enumerate(PALETTE):
        for col, hexv in enumerate(colors):
            color = QColor(0, 0, 0, 0) if hexv is None else QColor(hexv)
            if hexv is None and not allow_alpha:
                continue
            btn = SwatchButton(color)

            def choose(_checked=False, c=QColor(color)):
                result["color"] = c
                menu.close()

            btn.clicked.connect(choose)
            grid.addWidget(btn, row, col)
    lay.addLayout(grid)

    custom = QPushButton("Custom…")
    custom.setObjectName("LayerActionButton")
    custom.setMinimumHeight(26)

    def choose_custom(_checked=False):
        result["custom"] = True
        menu.close()

    custom.clicked.connect(choose_custom)
    lay.addWidget(custom)

    act = QWidgetAction(menu)
    act.setDefaultWidget(container)
    menu.addAction(act)
    menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    if result.get("custom"):
        opts = (QColorDialog.ColorDialogOption.ShowAlphaChannel
                if allow_alpha else QColorDialog.ColorDialogOption(0))
        color = QColorDialog.getColor(initial, parent, "Pick Color", opts)
        return color if color.isValid() else None
    return result.get("color")

TAIL_POSITIONS = (
    "Top Left", "Top Center", "Top Right", "Right",
    "Bottom Right", "Bottom Center", "Bottom Left", "Left",
)


def _set_btn_color(btn: QPushButton, color: QColor):
    btn.setStyleSheet(
        "QPushButton {"
        f"background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});"
        "border: 1px solid #35475c; border-radius: 4px;"
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

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_cut = menu.addAction("Cut")
        act_copy = menu.addAction("Copy")
        act_paste = menu.addAction("Paste")
        menu.addSeparator()
        act_select_all = menu.addAction("Select All")

        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        clipboard_has_text = bool(QApplication.clipboard().text())
        act_cut.setEnabled(has_selection and not self.isReadOnly())
        act_copy.setEnabled(has_selection)
        act_paste.setEnabled(clipboard_has_text and not self.isReadOnly())
        act_select_all.setEnabled(bool(self.toPlainText()))

        chosen = menu.exec(event.globalPos())
        if chosen == act_cut:
            self.cut()
        elif chosen == act_copy:
            self.copy()
        elif chosen == act_paste:
            self.paste()
        elif chosen == act_select_all:
            self.selectAll()


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
        self.setFixedSize(52, 46)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.isEnabled():
            bg = QColor("#101722")
            border = QColor("#202c3b")
            stroke = QColor("#526075")
        elif self.isChecked():
            bg = QColor(255, 122, 69, 34)
            border = QColor("#ff7a45")
            stroke = QColor("#ff7a45")
        elif self.underMouse():
            bg = QColor("#243348")
            border = QColor("#526a86")
            stroke = QColor("#eef3f8")
        else:
            bg = QColor("#1c2938")
            border = QColor("#35475c")
            stroke = QColor("#dbe5f0")

        outer = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(border, 1.4))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(outer, 7, 7)

        painter.setPen(QPen(stroke, 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self._paint_preview(painter, stroke)

    def _paint_preview(self, painter: QPainter, stroke: QColor):
        """Draw the REAL silhouette, scaled into the tile.

        Each tile used to have its own bespoke drawing code, which drifted from
        what the canvas actually produced. Both now call build_body_path, so a
        preview can't disagree with the bubble you get.
        """
        from bubble import build_body_path, ink_stroke
        if self._style in ("text", "scrim", "caption"):
            self._paint_text_style_glyph(painter, stroke)
            return
        box = QRectF(8, 7, self.width() - 16, self.height() - 14)
        # Stable per-shape seed so a tile doesn't wobble differently each repaint.
        seed = (abs(hash(self._style)) % 628) / 100.0
        path = build_body_path(self._style, box, seed)
        # Ink the tile the same way the canvas inks the balloon.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(stroke))
        painter.drawPath(ink_stroke(path, 2.2, seed))

    def _paint_text_style_glyph(self, painter: QPainter, stroke: QColor):
        """Text-only styles have no balloon body — draw a lettering glyph."""
        if self._style == "text":
            f = QFont("Inter")
            f.setPixelSize(21)
            f.setBold(True)
            p = QPainterPath()
            p.addText(9, 29, f, "Aa")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(p, QBrush(stroke))
        elif self._style == "scrim":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(stroke))
            painter.drawRoundedRect(QRectF(7, 14, 32, 14), 3, 3)
            hole = QColor("#0b1119") if self.isChecked() else QColor("#1c2938")
            painter.setBrush(QBrush(hole))
            painter.drawRoundedRect(QRectF(11, 18, 24, 2.4), 1.2, 1.2)
            painter.drawRoundedRect(QRectF(11, 22.4, 17, 2.4), 1.2, 1.2)
        else:   # caption
            f = QFont("Inter")
            f.setPixelSize(24)
            f.setBold(True)
            p = QPainterPath()
            p.addText(15, 31, f, "A")
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(stroke, 1.5))
            painter.drawPath(p)


# ---------------------------------------------------------------------------
# TailShapeButton
# ---------------------------------------------------------------------------

class TailCountButton(QToolButton):
    """Balloon drawn with N tails — Balloon+'s "Number of Tails" row. Numbers
    told you the count but not what it looks like."""

    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self._n = count
        self.setObjectName("StyleButton")
        self.setCheckable(True)
        self.setFixedSize(44, 38)
        self.setToolTip(f"{count} tail{'s' if count != 1 else ''}")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            bg, br, ink = QColor("#101722"), QColor("#202c3b"), QColor("#526075")
        elif self.isChecked():
            bg, br, ink = QColor(255, 122, 69, 34), QColor("#ff7a45"), QColor("#ff7a45")
        elif self.underMouse():
            bg, br, ink = QColor("#243348"), QColor("#526a86"), QColor("#eef3f8")
        else:
            bg, br, ink = QColor("#1c2938"), QColor("#35475c"), QColor("#dbe5f0")
        p.setPen(QPen(br, 1.4))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 7, 7)

        body = QRectF(7, 7, 28, 16)
        shape = QPainterPath()
        shape.addEllipse(body)
        for i in range(self._n):
            # Fan the tails out from the balloon's underside.
            spread = 0 if self._n == 1 else (i / (self._n - 1) - 0.5)
            bx = body.center().x() + spread * 15
            tip_x = bx + spread * 9
            tail = QPainterPath(QPointF(bx - 3.4, body.bottom() - 2))
            tail.lineTo(QPointF(tip_x, body.bottom() + 9))
            tail.lineTo(QPointF(bx + 3.4, body.bottom() - 2))
            tail.closeSubpath()
            shape = shape.united(tail)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ink, 1.6))
        p.drawPath(shape)


class AccentButton(QToolButton):
    """Pictogram toggle for an expression mark — this is a visual editor, a row
    of word-buttons told you nothing about what you were switching on."""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self._kind = kind
        self.setObjectName("StyleButton")
        self.setCheckable(True)
        self.setFixedSize(50, 42)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            bg, br, ink = QColor("#101722"), QColor("#202c3b"), QColor("#526075")
        elif self.isChecked():
            bg, br, ink = QColor(255, 122, 69, 34), QColor("#ff7a45"), QColor("#ff9a70")
        elif self.underMouse():
            bg, br, ink = QColor("#243348"), QColor("#ff7a45"), QColor("#eef3f8")
        else:
            bg, br, ink = QColor("#1c2938"), QColor("#35475c"), QColor("#dbe5f0")
        p.setPen(QPen(br, 1.4))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 7, 7)

        body = QRectF(12, 13, 26, 18)
        k = self._kind
        if k == "halftone":
            # balloon + offset dot band
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ink)
            for row in range(4):
                for col in range(6):
                    x = 18 + col * 4.2 + (2 if row % 2 else 0)
                    y = 19 + row * 4.0
                    p.drawEllipse(QPointF(x, y), 1.25, 1.25)
            p.setBrush(QColor("#1c2938") if not self.isChecked() else QColor("#0b1119"))
            p.setPen(QPen(ink, 1.5))
            p.drawEllipse(body)
        elif k == "ticks":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, 1.5))
            p.drawEllipse(QRectF(13, 18, 24, 15))
            p.setPen(QPen(ink, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(5):
                a = math.radians(-150 + i * 30)
                p.drawLine(QPointF(25 + math.cos(a) * 14, 26 + math.sin(a) * 11),
                           QPointF(25 + math.cos(a) * 19, 26 + math.sin(a) * 15))
        elif k == "impact":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, 1.5))
            p.drawEllipse(QRectF(15, 20, 20, 13))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ink)
            for i in range(5):
                a = math.radians(-152 + i * 31)
                bx, by = 25 + math.cos(a) * 12, 27 + math.sin(a) * 10
                tx, ty = 25 + math.cos(a) * 22, 27 + math.sin(a) * 18
                nx, ny = -math.sin(a), math.cos(a)
                wedge = QPainterPath(QPointF(bx + nx * 1.8, by + ny * 1.8))
                wedge.lineTo(QPointF(tx, ty))
                wedge.lineTo(QPointF(bx - nx * 1.8, by - ny * 1.8))
                wedge.closeSubpath()
                p.drawPath(wedge)
        elif k == "puffs":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, 1.5))
            p.drawEllipse(QRectF(9, 17, 22, 15))
            for cx, cy, rad in ((34, 16, 3.6), (39, 11, 2.4), (43, 7.5, 1.5)):
                p.drawEllipse(QPointF(cx, cy), rad, rad)
        else:   # bolt
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, 1.5))
            p.drawEllipse(QRectF(10, 12, 22, 15))
            bolt = QPainterPath(QPointF(35, 22))
            bolt.lineTo(QPointF(28, 32))
            bolt.lineTo(QPointF(33, 32))
            bolt.lineTo(QPointF(29, 40))
            bolt.lineTo(QPointF(40, 29))
            bolt.lineTo(QPointF(34, 29))
            bolt.closeSubpath()
            p.setBrush(ink)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(bolt)


class BalloonPresetButton(QToolButton):
    """One-click balloon look: a mini balloon in that fill + outline."""

    def __init__(self, fill: QColor, stroke: QColor, parent=None):
        super().__init__(parent)
        self._fill, self._stroke = QColor(fill), QColor(stroke)
        self.setObjectName("StyleButton")
        self.setFixedSize(38, 32)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        border = QColor("#526a86") if self.underMouse() else QColor("#35475c")
        p.setPen(QPen(border, 1.2))
        p.setBrush(QColor("#1c2938"))
        p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 6, 6)
        oval = QRectF(8, 8, self.width() - 16, self.height() - 16)
        if self._fill.alpha() == 0:
            # Transparent fill: show the checkerboard so "Ghost" reads clearly.
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#526a86"))
            p.drawEllipse(oval)
            p.setBrush(QColor("#243348"))
            p.setClipRect(QRectF(oval.center().x(), oval.top(),
                                 oval.width() / 2, oval.height()))
            p.drawEllipse(oval)
            p.setClipping(False)
        else:
            p.setBrush(self._fill)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(oval)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self._stroke, 1.8))
        p.drawEllipse(oval)


class OutlineWidthButton(QToolButton):
    """Balloon+-style outline-thickness preset: draws a ring at that width."""

    def __init__(self, width: float, parent=None):
        super().__init__(parent)
        self._w = width
        self.setObjectName("StyleButton")
        self.setCheckable(True)
        self.setFixedSize(38, 32)
        self.setToolTip("No outline" if width <= 0 else f"{width:g} px outline")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            bg, border, stroke = QColor("#101722"), QColor("#202c3b"), QColor("#526075")
        elif self.isChecked():
            bg, border, stroke = QColor(255, 122, 69, 34), QColor("#ff7a45"), QColor("#ff7a45")
        elif self.underMouse():
            bg, border, stroke = QColor("#243348"), QColor("#526a86"), QColor("#eef3f8")
        else:
            bg, border, stroke = QColor("#1c2938"), QColor("#35475c"), QColor("#dbe5f0")
        painter.setPen(QPen(border, 1.4))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 7, 7)

        ring = QRectF(8, 8, 22, 16)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._w <= 0:
            painter.setPen(QPen(stroke, 1.0, Qt.PenStyle.DashLine))
        else:
            painter.setPen(QPen(stroke, max(1.0, self._w)))
        painter.drawEllipse(ring)


class TailShapeButton(QToolButton):
    """Painted pictogram for a tail render shape (Balloon+-style picker)."""

    def __init__(self, shape: str, parent=None):
        super().__init__(parent)
        self._shape = shape
        self.setObjectName("StyleButton")
        self.setCheckable(True)
        self.setFixedSize(46, 40)
        self.setToolTip(TAIL_SHAPE_LABELS.get(shape, shape))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.isEnabled():
            bg, border, stroke = QColor("#101722"), QColor("#202c3b"), QColor("#526075")
        elif self.isChecked():
            bg, border, stroke = QColor(255, 122, 69, 34), QColor("#ff7a45"), QColor("#ff7a45")
        elif self.underMouse():
            bg, border, stroke = QColor("#243348"), QColor("#526a86"), QColor("#eef3f8")
        else:
            bg, border, stroke = QColor("#1c2938"), QColor("#35475c"), QColor("#dbe5f0")

        outer = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(border, 1.4))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(outer, 7, 7)

        painter.setPen(QPen(stroke, 1.6, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(QBrush(stroke))
        # Pictograms are authored on a 38x34 canvas; centre in the button.
        painter.translate((self.width() - 38) / 2, (self.height() - 34) / 2)
        s = self._shape
        if s == "wedge":
            p = QPainterPath(QPointF(26, 8))
            p.lineTo(QPointF(31, 12))
            p.lineTo(QPointF(11, 27))
            p.closeSubpath()
            painter.drawPath(p)
        elif s == "curved":
            p = QPainterPath(QPointF(29, 8))
            p.cubicTo(QPointF(30, 17), QPointF(24, 24), QPointF(11, 27))
            p.cubicTo(QPointF(21, 20), QPointF(24, 15), QPointF(24, 9))
            p.closeSubpath()
            painter.drawPath(p)
        elif s == "line":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(29, 9), QPointF(12, 26))
            painter.drawLine(QPointF(12, 26), QPointF(17, 24))
            painter.drawLine(QPointF(12, 26), QPointF(14, 21))
        elif s == "dots":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(27, 11), 4.6, 4.0)
            painter.drawEllipse(QPointF(18, 19), 3.2, 2.8)
            painter.drawEllipse(QPointF(11, 25), 2.0, 1.8)
        else:  # none
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(stroke, 1.3))
            painter.drawRect(QRectF(11, 10, 17, 14))
            painter.drawLine(QPointF(11, 10), QPointF(28, 24))
            painter.drawLine(QPointF(28, 10), QPointF(11, 24))


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
        header_w.setFixedHeight(30)
        hbox = QHBoxLayout(header_w)
        hbox.setContentsMargins(14, 4, 12, 0)
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
        self.body_lay.setContentsMargins(12, 4, 12, 10)
        self.body_lay.setSpacing(7)
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
        self.setMinimumWidth(272)
        self.setMaximumWidth(380)
        self.setObjectName("InspectorDock")
        self._bubble     = None
        self._media      = None
        self._redact_item = None
        self._lines_item = None
        self._scene      = None
        self._undo_stack = None
        self._updating   = False
        self._font_combo = None
        self._layer_items = {}
        self._refreshing_layers = False
        self._dual_border_color_val = QColor("#485d76")
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

        # Tabs split the full feature set into stable, predictable work areas.
        self._tabs = QTabBar()
        self._tabs.addTab("Shape")
        self._tabs.addTab("Text")
        self._tabs.addTab("FX")
        self._tabs.addTab("Layers")
        self._tabs.setObjectName("InspectorTabBar")
        self._tabs.setExpanding(True)
        self._tabs.currentChanged.connect(self._stack_tab)
        lay.addWidget(self._tabs)

        self._stack = QStackedWidget()
        lay.addWidget(self._stack, stretch=1)

        def _make_page():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            page = QWidget()
            page.setObjectName("InspectorPage")
            page.setMinimumWidth(0)
            page.setSizePolicy(QSizePolicy.Policy.Ignored,
                               QSizePolicy.Policy.Preferred)
            page_lay = QVBoxLayout(page)
            page_lay.setContentsMargins(0, 0, 0, 0)
            page_lay.setSpacing(0)
            scroll.setWidget(page)
            return scroll, page_lay

        shape_scroll, self._shape_lay = _make_page()
        text_scroll, self._text_lay = _make_page()
        fx_scroll, self._fx_lay = _make_page()

        self._shape_intro_title, self._shape_intro_text = self._add_tab_intro(
            self._shape_lay, "Shape",
            "Choose the bubble form, fill, border, and tail.")
        self._text_intro_title, self._text_intro_text = self._add_tab_intro(
            self._text_lay, "Text",
            "Edit wording, typography, alignment, and spacing.")
        self._fx_intro_title, self._fx_intro_text = self._add_tab_intro(
            self._fx_lay, "Effects",
            "Add shadows, expression marks, photos, and motion effects.")

        # Nothing selected = nothing to configure. Showing a wall of disabled
        # controls on launch was pure noise (and forced a scrollbar); each page
        # gets a short placeholder instead.
        self._placeholders = []
        for lay_, msg in ((self._shape_lay, "Select a bubble to style it.\n\n"
                                            "Double-click the photo to add one."),
                          (self._text_lay, "Select a bubble to edit its text."),
                          (self._fx_lay, "Select a bubble for shadow options,\n"
                                         "or add Speed Lines from the toolbar.")):
            ph = QLabel(msg)
            ph.setObjectName("InspectorPlaceholder")
            ph.setWordWrap(True)
            ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ph.setContentsMargins(22, 40, 22, 20)
            lay_.addWidget(ph)
            self._placeholders.append(ph)
        # Sections register themselves against whichever layout is current.
        self._inspector_lay = self._shape_lay
        self._build_inspector_sections()
        self._stack.addWidget(shape_scroll)
        self._stack.addWidget(text_scroll)
        self._stack.addWidget(fx_scroll)

        layers_page = QWidget()
        layers_page.setObjectName("InspectorPage")
        layers_lay = QVBoxLayout(layers_page)
        layers_lay.setContentsMargins(0, 0, 0, 0)
        layers_lay.setSpacing(0)

        self._layers_intro_title, self._layers_intro_text = self._add_tab_intro(
            layers_lay, "Layers",
            "Control visibility and front-to-back order.")

        layers_header = QWidget()
        layers_header.setObjectName("InspectorSectionHeader")
        layers_header.setFixedHeight(38)
        layers_header_lay = QHBoxLayout(layers_header)
        layers_header_lay.setContentsMargins(14, 0, 12, 0)
        layers_title = QLabel("LAYER STACK")
        layers_title.setObjectName("InspectorSectionTitle")
        layers_header_lay.addWidget(layers_title)
        layers_header_lay.addStretch()
        layers_order = QLabel("FRONT TO BACK")
        layers_order.setObjectName("InspectorHint")
        layers_header_lay.addWidget(layers_order)
        layers_lay.addWidget(layers_header)

        self._layers_stack = QStackedWidget()
        self._layers_list = QListWidget()
        self._layers_list.setObjectName("LayersList")
        self._layers_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._layers_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._layers_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._layers_list.itemChanged.connect(self._on_layer_item_changed)
        self._layers_list.itemSelectionChanged.connect(self._on_layer_selection)
        self._layers_list.itemClicked.connect(
            lambda _item: self._on_layer_selection())
        self._layers_list.model().rowsMoved.connect(self._on_layers_reordered)
        self._layers_stack.addWidget(self._layers_list)

        self._layers_empty = QLabel(
            "No editable layers yet.\n\nAdd a bubble, image layer, blur, pixelate, "
            "or speed lines to start building the stack.")
        self._layers_empty.setObjectName("LayersEmptyState")
        self._layers_empty.setWordWrap(True)
        self._layers_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layers_empty.setContentsMargins(28, 28, 28, 28)
        self._layers_stack.addWidget(self._layers_empty)
        layers_lay.addWidget(self._layers_stack, stretch=1)

        self._layers_actions = QWidget()
        self._layers_actions.setObjectName("LayersActionBar")
        layer_actions = QHBoxLayout(self._layers_actions)
        layer_actions.setContentsMargins(10, 10, 10, 12)
        layer_actions.setSpacing(8)
        for label, delta, tip in (
            ("Move up", -1, "Move selected layer up"),
            ("Move down", 1, "Move selected layer down"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("LayerActionButton")
            btn.setMinimumHeight(32)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _checked=False, d=delta: self._move_selected_layer(d))
            layer_actions.addWidget(btn)
        layers_lay.addWidget(self._layers_actions)
        self._stack.addWidget(layers_page)

    def _add_tab_intro(self, layout, title: str, description: str):
        intro = QWidget()
        intro.setObjectName("InspectorTabIntro")
        intro_lay = QVBoxLayout(intro)
        intro_lay.setContentsMargins(14, 10, 14, 11)
        intro_lay.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("InspectorTabIntroTitle")
        intro_lay.addWidget(title_label)
        description_label = QLabel(description)
        description_label.setObjectName("InspectorTabIntroText")
        description_label.setWordWrap(True)
        intro_lay.addWidget(description_label)
        layout.addWidget(intro)
        return title_label, description_label

    def _build_inspector_sections(self):
        # --- SHAPE tab: the bubble's form ----------------------------------
        self._inspector_lay = self._shape_lay
        self._build_bubble_section()
        self._build_colors_section()
        self._build_border_section()
        self._build_tail_section()
        self._build_stroke_section()
        self._build_layer_section()
        self._build_dual_section()
        self._build_manga_layout_section()
        self._build_collage_layout_section()
        self._build_collage_fx_section()
        self._shape_lay.addStretch()

        # --- TEXT tab: what the bubble says --------------------------------
        self._inspector_lay = self._text_lay
        self._build_text_section()
        self._build_typography_section()
        # Presets + text layout sit under the type controls so they're easy to
        # reach for a text object without hunting.
        self._build_spacing_section()
        self._text_lay.addStretch()

        # --- EFFECTS tab: shadow, speed lines, new-bubble defaults ---------
        # Shadow lives here on its own so toggling it can't reflow the Shape
        # tab under the cursor (that was the jumpy-panel bug).
        self._inspector_lay = self._fx_lay
        self._build_shadow_section()
        self._build_accent_section()
        self._build_photo_section()
        self._build_redact_section()
        self._build_speedlines_section()
        self._build_manga_section()
        self._build_defaults_section()
        self._fx_lay.addStretch()
        self._bubble_sections = (
            self._text_section, self._bubble_section, self._colors_section,
            self._border_section, self._typography_section, self._tail_section,
            self._photo_section, self._shadow_section, self._accent_section,
        )
        self._layer_section.setVisible(False)
        self._layer_section.setEnabled(False)
        # Launch state = nothing selected, so start on the placeholders. This
        # runs at construction; clear() only fires on a selection change, which
        # is why the panel used to open full of dead controls.
        self._set_bubble_sections_visible(False)
        self._defaults_section.setVisible(False)
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._set_placeholder_visible(True)
        self._set_controls_enabled(False)

    def _build_text_section(self):
        section = AccordionSection("TEXT")
        top = QHBoxLayout()
        top.addStretch()
        self._char_count = QLabel("0")
        self._char_count.setObjectName("InspectorHint")
        top.addWidget(self._char_count)
        section.body_lay.addLayout(top)
        self._text_edit = CommitTextEdit()
        self._text_edit.setObjectName("InspectorTextEdit")
        self._text_edit.setFixedHeight(50)
        self._text_edit.setAcceptRichText(False)
        self._text_edit.setPlaceholderText("Type bubble text here…")
        self._text_edit.setToolTip("Bubble text")
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.editCommitted.connect(self._on_text_committed)
        section.body_lay.addWidget(self._text_edit)

        # Lobed balloons (twin / triple) get one box per lobe.
        self._lobe_edits = []
        for i in range(3):
            lbl = QLabel(f"Lobe {i + 1}")
            lbl.setObjectName("InspectorLabel")
            edit = CommitTextEdit()
            edit.setObjectName("InspectorTextEdit")
            edit.setFixedHeight(44)
            edit.setAcceptRichText(False)
            edit.setPlaceholderText(f"Text for lobe {i + 1}…")
            edit.textChanged.connect(
                lambda idx=i: self._on_lobe_text_changed(idx))
            section.body_lay.addWidget(lbl)
            section.body_lay.addWidget(edit)
            lbl.setVisible(False)
            edit.setVisible(False)
            self._lobe_edits.append((lbl, edit))

        self._text_section = section
        self._inspector_lay.addWidget(section)

    def _build_redact_section(self):
        """Controls for a selected blur/pixelate redaction box."""
        section = AccordionSection("REDACT")
        row = QHBoxLayout()
        row.addWidget(self._label("Mode"))
        self._redact_mode_group = QButtonGroup(self)
        self._redact_mode_group.setExclusive(True)
        self._redact_blur_btn = QToolButton()
        self._redact_blur_btn.setText("Blur")
        self._redact_blur_btn.setCheckable(True)
        self._redact_blur_btn.setToolTip("Soften the area beneath the box")
        self._redact_blur_btn.clicked.connect(lambda: self._on_redact_mode("blur"))
        self._redact_pix_btn = QToolButton()
        self._redact_pix_btn.setText("Pixelate")
        self._redact_pix_btn.setCheckable(True)
        self._redact_pix_btn.setToolTip("Pixelate / mosaic the area beneath the box")
        self._redact_pix_btn.clicked.connect(lambda: self._on_redact_mode("pixelate"))
        self._redact_mode_group.addButton(self._redact_blur_btn)
        self._redact_mode_group.addButton(self._redact_pix_btn)
        row.addWidget(self._redact_blur_btn, stretch=1)
        row.addWidget(self._redact_pix_btn, stretch=1)
        section.body_lay.addLayout(row)
        self._redact_intensity = self._compact_slider_row(
            section.body_lay, "Strength", 1, 100, 55, " %",
            self._on_redact_intensity,
            tooltip="Blur strength / pixel density")
        section.setVisible(False)
        self._redact_section = section
        self._inspector_lay.addWidget(section)

    def update_for_redaction(self, item):
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = None
        self._media = None
        self._redact_item = item
        self._set_bubble_sections_visible(False)
        self._layer_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._redact_section.setVisible(True)
        self._set_placeholder_visible(False)
        self._configure_tabs_for_page_mode()
        self._show_tab(self.FX_TAB)
        self._updating = True
        try:
            self._redact_blur_btn.setChecked(item.get_mode() == "blur")
            self._redact_pix_btn.setChecked(item.get_mode() == "pixelate")
            self._redact_intensity.setValue(item.get_intensity())
        finally:
            self._updating = False
        self._refresh_layers()

    def _on_redact_mode(self, mode: str):
        if self._redact_item and not self._updating:
            self._redact_item.set_mode(mode)

    def _on_redact_intensity(self, value: int):
        if self._redact_item and not self._updating:
            self._redact_item.set_intensity(value)

    # Reverse-engineered from the reference sheet: a balloon there carries a
    # halftone shadow, radiating strokes, a star, an exclamation mark and little
    # satellite puffs — often several at once. So these are toggles, not a
    # one-of-four choice.
    ACCENT_DEFS = (
        ("halftone", "Halftone", "Printed dot-screen drop shadow"),
        ("ticks",    "Ticks",    "Short radiating emphasis strokes"),
        ("impact",   "Impact",   "Long tapered shout strokes"),
        ("puffs",    "Puffs",    "Satellite bubbles trailing off"),
        ("bolt",     "Bolt",     "Lightning-bolt shock spur"),
    )

    def _build_accent_section(self):
        """Comic emphasis marks inked around the balloon. Combinable."""
        section = AccordionSection("EXPRESSION")
        grid = QGridLayout()
        grid.setSpacing(5)
        self._accent_btns = {}
        for i, (kind, label, tip) in enumerate(self.ACCENT_DEFS):
            btn = AccentButton(kind)     # NOT exclusive: these stack
            btn.setToolTip(f"{label} — {tip}")
            btn.toggled.connect(lambda on, k=kind: self._on_accent(k, on))
            self._accent_btns[kind] = btn
            grid.addWidget(btn, i // 5, i % 5)
        section.body_lay.addLayout(grid)
        clear_row = QHBoxLayout()
        clear_row.addStretch()
        clear = QPushButton("Clear all")
        clear.setObjectName("LayerActionButton")
        clear.setMinimumHeight(26)
        clear.setToolTip("Remove every expression mark")
        clear.clicked.connect(self._on_accents_clear)
        clear_row.addWidget(clear)
        section.body_lay.addLayout(clear_row)
        self._accent_amount = self._compact_slider_row(
            section.body_lay, "Amount", 0, 100, 70, " %", self._on_accent_amount,
            tooltip="How many strokes / how dense the halftone dots are")
        self._accent_section = section
        self._inspector_lay.addWidget(section)

    def _on_accent(self, kind: str, on: bool):
        if self._bubble and not self._updating:
            self._bubble.set_accent(kind, on)

    def _on_accents_clear(self):
        if not self._bubble:
            return
        self._updating = True
        try:
            for btn in self._accent_btns.values():
                btn.setChecked(False)
        finally:
            self._updating = False
        self._bubble.set_accents(())

    def _on_accent_amount(self, value: int):
        if self._bubble and not self._updating:
            self._bubble.set_accent_amount(value)

    def _build_photo_section(self):
        """Balloon+ keeps the inset-photo controls in their own screen rather
        than bolted onto the main panel — one button here, six sliders and a
        live preview in the popup, and the inspector stays short."""
        section = AccordionSection("PHOTO IN BUBBLE")
        self._photo_btn = QPushButton("Add Photo to Bubble…")
        self._photo_btn.setObjectName("LayerActionButton")
        self._photo_btn.setMinimumHeight(32)
        self._photo_btn.setToolTip(
            "Place a photo inside this bubble and adjust spacing, blur,\n"
            "opacity, zoom and position")
        self._photo_btn.clicked.connect(self._open_photo_dialog)
        section.body_lay.addWidget(self._photo_btn)
        self._photo_section = section
        self._inspector_lay.addWidget(section)

    def _open_photo_dialog(self):
        if not self._bubble:
            return
        from photo_dialog import PhotoInBubbleDialog
        before = self._inset_state(self._bubble)
        dlg = PhotoInBubbleDialog(self._bubble, self)
        dlg.exec()
        after = self._inset_state(self._bubble)
        # The dialog edits the bubble live; record the whole session as ONE
        # undo step rather than one per slider tick.
        if after != before and self._undo_stack:
            self._undo_stack.push(
                InsetPhotoCommand(self._bubble, before, after))
        self._sync_inset_controls(self._bubble)

    def _inset_state(self, bubble) -> dict:
        return {
            "pixmap": bubble._inset_pixmap,
            "spacing": bubble.get_inset_spacing(),
            "blur": bubble.get_inset_blur(),
            "opacity": bubble.get_inset_opacity(),
            "zoom": bubble.get_inset_zoom(),
            "dx": bubble.get_inset_dx(),
            "dy": bubble.get_inset_dy(),
        }

    def _sync_inset_controls(self, bubble):
        self._photo_btn.setText(
            "Edit Bubble Photo…" if bubble.has_inset_photo()
            else "Add Photo to Bubble…")

    def _build_speedlines_section(self):
        """Controls for a selected speed-lines overlay (Balloon+ effect)."""
        section = AccordionSection("SPEED LINES")
        row = QHBoxLayout()
        row.setSpacing(4)
        self._lines_kind_group = QButtonGroup(self)
        self._lines_kind_group.setExclusive(True)
        self._lines_kind_btns = {}
        for kind, label, tip in (("radial", "Radial", "Focus lines from the frame edges"),
                                 ("burst", "Burst", "Fat sunburst wedges"),
                                 ("streak", "Streak", "Horizontal motion streaks")):
            btn = QToolButton()
            btn.setObjectName("AlignButton")
            btn.setText(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setMinimumWidth(62)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _c, k=kind: self._on_lines_kind(k))
            self._lines_kind_group.addButton(btn)
            self._lines_kind_btns[kind] = btn
            row.addWidget(btn)
        row.addStretch()
        section.body_lay.addLayout(row)

        self._lines_density = self._compact_slider_row(
            section.body_lay, "Density", 4, 320, 110, "", self._on_lines_density,
            tooltip="Number of lines")
        self._lines_thickness = self._compact_slider_row(
            section.body_lay, "Weight", 1, 300, 10, " px", self._on_lines_thickness,
            tooltip="Maximum line width at the frame edge")
        self._lines_inner = self._compact_slider_row(
            section.body_lay, "Clear", 5, 90, 55, " %", self._on_lines_inner,
            tooltip="How much of the centre stays clear of lines")

        color_row = QHBoxLayout()
        color_row.addWidget(self._label("Color"))
        self._lines_color_btn = QPushButton()
        self._lines_color_btn.setFixedSize(30, 24)
        self._lines_color_btn.setToolTip("Line color — click to pick")
        self._lines_color_btn.clicked.connect(self._on_lines_color)
        color_row.addWidget(self._lines_color_btn)
        color_row.addStretch()
        section.body_lay.addLayout(color_row)

        hint = QLabel("Drag the red dot on the canvas to move the focus point.")
        hint.setObjectName("InspectorHint")
        hint.setWordWrap(True)
        section.body_lay.addWidget(hint)

        section.setVisible(False)
        self._lines_section = section
        self._inspector_lay.addWidget(section)

    def update_for_speedlines(self, item):
        page_mode = bool(
            self._scene and
            (self._scene.is_manga_mode() or self._scene.is_collage_mode()))
        collage_mode = bool(
            page_mode and self._scene.is_collage_mode())
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = None
        self._media = None
        self._redact_item = None
        self._lines_item = item
        self._set_bubble_sections_visible(False)
        self._spacing_section.setVisible(False)
        self._layer_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(True)
        self._set_placeholder_visible(False)
        self._configure_tabs_for_page_mode()
        self._show_tab(self.FX_TAB)
        self._updating = True
        try:
            for kind, btn in self._lines_kind_btns.items():
                btn.setChecked(kind == item.get_kind())
            self._lines_density.setValue(item.get_density())
            self._lines_thickness.setValue(int(item.get_thickness()))
            self._lines_inner.setValue(item.get_inner())
            self._set_color(self._lines_color_btn, None, item.get_color())
        finally:
            self._updating = False
        self._refresh_layers()

    def _on_lines_kind(self, kind: str):
        if self._lines_item and not self._updating:
            self._lines_item.set_kind(kind)

    def _on_lines_density(self, value: int):
        if self._lines_item and not self._updating:
            self._lines_item.set_density(value)

    def _on_lines_thickness(self, value: int):
        if self._lines_item and not self._updating:
            self._lines_item.set_thickness(float(value))

    def _on_lines_inner(self, value: int):
        if self._lines_item and not self._updating:
            self._lines_item.set_inner(value)

    def _on_lines_color(self):
        if not self._lines_item:
            return
        color = pick_color(self._lines_color_btn, self._lines_item.get_color(),
                           self, allow_alpha=True)
        if color is not None and color.isValid():
            self._lines_item.set_color(color)
            self._set_color(self._lines_color_btn, None, color)

    def _build_spacing_section(self):
        """Text-style extras: preset look, V./H. spacing + Fit to Box. One
        compact accordion section (only shown for text) — no pinned panel."""
        section = AccordionSection("TEXT PRESETS")
        # Preset looks as a compact 3-column button grid (in-flow, text-only —
        # no pinned panel, so it never reserves space or forces a scrollbar).
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, preset in enumerate(TEXT_PRESETS):
            btn = QToolButton()
            btn.setObjectName("PresetButton")
            btn.setText(preset["name"])
            btn.setToolTip(f"Apply the “{preset['name']}” text look")
            btn.clicked.connect(lambda _c, p=preset: self._on_text_preset(p))
            grid.addWidget(btn, i // 3, i % 3)
        section.body_lay.addLayout(grid)

        self._v_spacing = self._compact_slider_row(
            section.body_lay, "V. Spacing", -20, 200, 0, " px",
            self._on_v_spacing, tooltip="Extra space between lines")
        self._h_spacing = self._compact_slider_row(
            section.body_lay, "H. Spacing", -10, 100, 0, " px",
            self._on_h_spacing, tooltip="Extra space between letters")
        fit_btn = QPushButton("Fit Text to Box")
        fit_btn.setObjectName("LayerActionButton")
        fit_btn.setMinimumHeight(30)
        fit_btn.setToolTip("Auto-size the text to fill the box")
        fit_btn.clicked.connect(self._on_fit_to_box)
        section.body_lay.addWidget(fit_btn)
        section.setVisible(False)
        self._spacing_section = section
        self._inspector_lay.addWidget(section)

    def _on_text_preset(self, preset: dict):
        if self._bubble:
            self._bubble.apply_text_preset(preset)
            self.update_for_bubble(self._bubble)

    def _on_v_spacing(self, value: int):
        if self._bubble and not self._updating:
            self._bubble.set_line_spacing(value)

    def _on_h_spacing(self, value: int):
        if self._bubble and not self._updating:
            self._bubble.set_letter_spacing(value)

    def _on_fit_to_box(self):
        if self._bubble:
            self._bubble.fit_text_to_box()

    def _build_bubble_section(self):
        section = AccordionSection("BUBBLE")

        # All bubble styles in a grid that fits the fixed inspector width.
        grid = QGridLayout()
        grid.setSpacing(6)
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

    # One-click balloon looks (Balloon+ puts two of these next to "Balloon
    # Color"; a few more cover the cases people actually reach for).
    # (label, fill RGBA, stroke RGB, text RGB, tooltip)
    BALLOON_PRESETS = (
        ("Classic", (255, 255, 255, 240), (20, 20, 20), (15, 15, 15),
         "White balloon, black outline"),
        ("Inverted", (18, 18, 18, 240), (255, 255, 255), (245, 245, 245),
         "Black balloon, white outline"),
        ("Ghost", (255, 255, 255, 0), (255, 255, 255), (255, 255, 255),
         "No fill — outline and text only"),
        ("Shout", (255, 216, 0, 255), (20, 20, 20), (15, 15, 15),
         "Yellow balloon for emphasis"),
        ("Alert", (214, 40, 40, 255), (20, 20, 20), (255, 255, 255),
         "Red balloon, white text"),
    )

    def _build_colors_section(self):
        section = AccordionSection("FILL")

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        self._balloon_preset_btns = []
        for label, fill, stroke, text, tip in self.BALLOON_PRESETS:
            btn = BalloonPresetButton(QColor(*fill), QColor(*stroke))
            btn.setToolTip(f"{label} — {tip}")
            btn.clicked.connect(
                lambda _c, f=fill, s=stroke, t=text: self._on_balloon_preset(f, s, t))
            self._balloon_preset_btns.append(btn)
            preset_row.addWidget(btn)
        preset_row.addStretch()
        section.body_lay.addLayout(preset_row)

        self._fill_btn, self._fill_hex = self._color_row(
            section.body_lay, "Color", QColor(255, 255, 255), self._on_fill_color,
            tooltip="Bubble fill color — click to pick"
        )
        self._bubble_opacity = self._compact_slider_row(
            section.body_lay, "Opacity", 0, 100, 94, " %", self._on_bubble_opacity,
            tooltip="Bubble fill opacity"
        )
        self._colors_section = section
        self._inspector_lay.addWidget(section)

    # Outline thickness presets, mirroring Balloon+'s "Outline Width" row.
    OUTLINE_PRESETS = (0.0, 1.0, 2.0, 3.5, 5.0, 8.0)

    def _build_border_section(self):
        """Balloon+ treats the balloon outline as a first-class control
        (colour + a row of visual thickness presets) — so do we."""
        section = AccordionSection("BORDER")
        self._stroke_btn, self._stroke_hex = self._color_row(
            section.body_lay, "Color", QColor(0, 0, 0), self._on_border_color,
            tooltip="Bubble outline color"
        )
        width_row = QHBoxLayout()
        width_row.setSpacing(4)
        self._outline_group = QButtonGroup(self)
        self._outline_group.setExclusive(True)
        self._outline_btns = {}
        for w in self.OUTLINE_PRESETS:
            btn = OutlineWidthButton(w)
            btn.clicked.connect(lambda _c, ww=w: self._on_outline_preset(ww))
            self._outline_group.addButton(btn)
            self._outline_btns[w] = btn
            width_row.addWidget(btn)
        width_row.addStretch()
        section.body_lay.addLayout(width_row)

        fine = QHBoxLayout()
        fine.addWidget(self._label("Width"))
        fine.addStretch()
        self._border_width = QDoubleSpinBox()
        self._border_width.setRange(0.0, 40.0)
        self._border_width.setSingleStep(0.5)
        self._border_width.setSuffix(" px")
        self._border_width.setFixedWidth(84)
        self._border_width.setToolTip("Bubble outline width in pixels")
        self._border_width.valueChanged.connect(self._on_border_width)
        fine.addWidget(self._border_width)
        section.body_lay.addLayout(fine)

        self._border_section = section
        self._inspector_lay.addWidget(section)

    def _outline_scale(self) -> float:
        """Presets are authored for a default-size bubble; on a bubble scaled up
        for a high-resolution photo they scale with it, so "2 px" always reads
        as the same visual weight regardless of the photo's pixel size."""
        if self._bubble is None:
            return 1.0
        from bubble import DEFAULT_W
        return max(1.0, self._bubble.body_rect.width() / DEFAULT_W)

    def _on_outline_preset(self, base_width: float):
        self._on_border_width(base_width * self._outline_scale())

    def _on_balloon_preset(self, fill, stroke, text):
        """Apply a whole balloon look in one click, as one undo step."""
        if not self._bubble or not self._undo_stack:
            return
        b = self._bubble
        new_fill, new_stroke, new_text = QColor(*fill), QColor(*stroke), QColor(*text)
        self._undo_stack.beginMacro("Balloon Preset")
        if b.get_fill_color() != new_fill:
            self._undo_stack.push(
                FillColorChangeCommand(b, b.get_fill_color(), new_fill))
        if b.get_border_color() != new_stroke:
            self._undo_stack.push(
                BorderColorChangeCommand(b, b.get_border_color(), new_stroke))
        if b.get_text_color() != new_text:
            self._undo_stack.push(
                TextColorChangeCommand(b, b.get_text_color(), new_text))
        self._undo_stack.endMacro()
        self.update_for_bubble(b)

    def _sync_outline_buttons(self, width: float):
        scale = self._outline_scale()
        for w, btn in self._outline_btns.items():
            btn.setChecked(abs(w * scale - width) < max(0.05, 0.06 * scale))

    def _build_layer_section(self):
        section = AccordionSection("LAYER")
        self._layer_opacity = self._compact_slider_row(
            section.body_lay, "Opacity", 0, 100, 100, " %", self._on_layer_opacity,
            tooltip="Selected image layer opacity"
        )
        self._layer_section = section
        self._inspector_lay.addWidget(section)

    # Curated families for the visual font grid: bundled fonts first, then
    # common system faces (filtered by availability at build time).
    # Comic / manga lettering faces ONLY — all bundled under fonts/ and shipped
    # with the app, so the grid looks identical on every machine. Generic system
    # UI fonts (Liberation, DejaVu, Cantarell…) are deliberately excluded: they
    # are wrong for speech-bubble lettering. The dropdown below still exposes
    # every installed font for anyone who wants one.
    # Klee One stays FIRST and remains the default: it is the pen-style manga
    # face the app shipped with and reads cleanly at bubble sizes.
    FONT_CANDIDATES = (
        "Comic Neue",        # comic lettering — default
        "Klee One",          # manga pen-style (JP + latin)
        "Patrick Hand",      # casual hand lettering
        "Yusei Magic",       # manga handwriting (JP + latin)
        "Zen Kurenaido",     # soft manga handwriting (JP + latin)
        "Permanent Marker",  # marker-pen lettering
        "Bangers",           # classic comic shout / SFX
        "Luckiest Guy",      # bold cartoon display
        "Anton",             # heavy headline / impact
        "Dela Gothic One",   # heavy manga display (JP + latin)
        "Mochiy Pop One",    # rounded pop manga (JP + latin)
        "Inter",             # neutral fallback for captions
    )

    # Shown ON the tile, rendered in that face — legible and self-identifying.
    FONT_LABELS = {
        "Klee One": "Klee", "Comic Neue": "Comic", "Patrick Hand": "Patrick",
        "Yusei Magic": "Yusei", "Zen Kurenaido": "Zen",
        "Permanent Marker": "Marker", "Bangers": "Bangers",
        "Luckiest Guy": "Lucky", "Anton": "Anton",
        "Dela Gothic One": "Dela", "Mochiy Pop One": "Mochiy", "Inter": "Inter",
    }

    def _build_typography_section(self):
        section = AccordionSection("TYPOGRAPHY")

        # Balloon+-style visual font tiles: each shows "Aa1" in its own face.
        # Populated deferred — bundled fonts register AFTER the window builds
        # (see main._load_fonts), so an immediate availability check misses them.
        self._font_tiles = {}
        self._font_tile_grid = QGridLayout()
        self._font_tile_grid.setSpacing(6)
        section.body_lay.addLayout(self._font_tile_grid)
        QTimer.singleShot(250, self._populate_font_tiles)

        row = QHBoxLayout()
        self._font_row_layout = row
        self._font_combo_placeholder = QWidget()
        self._font_combo_placeholder.setFixedHeight(32)
        self._font_combo_placeholder.setToolTip("Font family")
        row.addWidget(self._font_combo_placeholder, stretch=1)
        # 300 ms: after main._load_fonts registers the bundled fonts, so the
        # combo (and the tile grid above) list Klee One / Inter / Anton too.
        QTimer.singleShot(300, self._create_font_combo)

        self._weight_combo = QComboBox()
        self._weight_combo.addItems(("Regular", "Bold", "Italic", "Bold Italic"))
        self._weight_combo.setFixedWidth(86)
        self._weight_combo.setToolTip("Font weight")
        self._weight_combo.currentIndexChanged.connect(self._on_font_weight)
        row.addWidget(self._weight_combo)
        section.body_lay.addLayout(row)

        # Font size as a slider — the chosen size is authoritative; resizing a
        # bubble no longer auto-shrinks the text (it grows the body to fit).
        size_row = QHBoxLayout()
        size_row.addWidget(self._label("Size"))
        self._font_size = QSlider(Qt.Orientation.Horizontal)
        self._font_size.setRange(6, 96)
        self._font_size.setToolTip("Font size")
        self._font_size.valueChanged.connect(self._on_font_size)
        self._font_size.valueChanged.connect(
            lambda v: self._font_size_value.setText(f"{v} px"))
        size_row.addWidget(self._font_size, 1)
        self._font_size_value = QLabel("20 px")
        self._font_size_value.setFixedWidth(46)
        self._font_size_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        size_row.addWidget(self._font_size_value)
        section.body_lay.addLayout(size_row)

        row2 = QHBoxLayout()
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

        # Text outline (comic lettering) — colour + thickness
        outline_row = QHBoxLayout()
        outline_row.addWidget(self._label("Outline"))
        self._outline_color_btn = QPushButton()
        self._outline_color_btn.setFixedSize(28, 28)
        self._outline_color_btn.setToolTip("Text outline color — click to pick")
        self._outline_color_btn.clicked.connect(self._on_text_outline_color)
        outline_row.addWidget(self._outline_color_btn)
        outline_row.addStretch()
        self._outline_width = QDoubleSpinBox()
        self._outline_width.setRange(0.0, 8.0)
        self._outline_width.setSingleStep(0.5)
        self._outline_width.setSuffix(" px")
        self._outline_width.setFixedWidth(76)
        self._outline_width.setToolTip("Text outline thickness (0 = off)")
        self._outline_width.valueChanged.connect(self._on_text_outline_width)
        outline_row.addWidget(self._outline_width)
        section.body_lay.addLayout(outline_row)

        self._typography_section = section
        self._inspector_lay.addWidget(section)

    def _build_tail_section(self):
        section = AccordionSection("TAIL")

        # Tail render shape — Balloon+-style pictogram picker
        shape_row = QHBoxLayout()
        shape_row.setSpacing(6)
        self._tail_shape_group = QButtonGroup(self)
        self._tail_shape_group.setExclusive(True)
        self._tail_shape_btns = {}
        for shape in TAIL_SHAPES:
            btn = TailShapeButton(shape)
            btn.clicked.connect(lambda _c, s=shape: self._on_tail_shape(s))
            self._tail_shape_group.addButton(btn)
            self._tail_shape_btns[shape] = btn
            shape_row.addWidget(btn)
        shape_row.addStretch()
        section.body_lay.addLayout(shape_row)

        # Number of tails (0-3)
        count_row = QHBoxLayout()
        count_row.setSpacing(6)
        count_row.addWidget(self._label("Tails"))
        self._tail_count_group = QButtonGroup(self)
        self._tail_count_group.setExclusive(True)
        self._tail_count_btns = {}
        for n in range(4):
            btn = TailCountButton(n)
            btn.clicked.connect(lambda _c, k=n: self._on_tail_count(k))
            self._tail_count_group.addButton(btn)
            self._tail_count_btns[n] = btn
            count_row.addWidget(btn)
        count_row.addStretch()
        section.body_lay.addLayout(count_row)

        # No "Anchor" preset dropdown: the tail is dragged straight to where
        # you want it on the canvas, which makes a list of 8 fixed positions
        # redundant. _tail_position stays as hidden state for older projects.
        self._tail_position = QComboBox()
        self._tail_position.addItems(TAIL_POSITIONS)
        self._tail_position.setVisible(False)
        self._tail_width = self._spin_row(
            section.body_lay, "Width", 6, 400, 40, " px", self._on_tail_width,
            tooltip="Width of the tail at its base in pixels"
        )
        self._tail_section = section
        self._stroke_section = section
        self._inspector_lay.addWidget(section)

    def _build_stroke_section(self):
        return

    def _build_shadow_section(self):
        section = AccordionSection("SHADOW")
        self._shadow_check = None   # None/Soft/Solid IS the on-off control

        # Quick presets (Balloon+: none / soft / solid offset)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        self._shadow_preset_btns = []
        for name, tip in (("None", "No shadow"),
                          ("Soft", "Soft blurred drop shadow"),
                          ("Solid", "Hard offset comic shadow")):
            btn = QPushButton(name)
            btn.setObjectName("PresetToggle")
            btn.setCheckable(True)
            btn.setMinimumHeight(28)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _c, k=name: self._on_shadow_preset(k))
            self._shadow_preset_btns.append(btn)
            preset_row.addWidget(btn)
        section.body_lay.addLayout(preset_row)

        self._shadow_color_btn, _ = self._color_row(
            section.body_lay, "Color", QColor(0, 0, 0), self._on_shadow_color,
            tooltip="Shadow color"
        )
        self._shadow_blur = self._spin_row(
            section.body_lay, "Blur", 0, 400, 12, " px", self._on_shadow_blur,
            tooltip="Shadow blur radius in pixels"
        )
        offset = QHBoxLayout()
        offset.addWidget(self._label("Offset"))
        self._shadow_x = QSpinBox()
        self._shadow_x.setRange(-400, 400)
        self._shadow_x.setPrefix("X ")
        self._shadow_x.setSuffix(" px")
        self._shadow_x.setToolTip("Shadow horizontal offset")
        self._shadow_x.valueChanged.connect(self._on_shadow_offset)
        self._shadow_y = QSpinBox()
        self._shadow_y.setRange(-400, 400)
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
        self._shadow_section = section
        self._inspector_lay.addWidget(section)

    def _build_defaults_section(self):
        """Balloon+-style "Default Balloon Settings": capture the selected
        bubble's look as the default for every NEW bubble."""
        section = AccordionSection("NEW BUBBLE DEFAULTS")
        self._save_default_btn = QPushButton("Save Current as Default")
        self._save_default_btn.setObjectName("LayerActionButton")
        self._save_default_btn.setMinimumHeight(30)
        self._save_default_btn.setToolTip(
            "New bubbles will use the selected bubble's style, colors, font,\n"
            "tail and shadow settings")
        self._save_default_btn.clicked.connect(self._on_save_defaults)
        section.body_lay.addWidget(self._save_default_btn)
        self._reset_default_btn = QPushButton("Reset to Factory Defaults")
        self._reset_default_btn.setObjectName("LayerActionButton")
        self._reset_default_btn.setMinimumHeight(30)
        self._reset_default_btn.setToolTip("Forget the saved defaults")
        self._reset_default_btn.clicked.connect(self._on_reset_defaults)
        section.body_lay.addWidget(self._reset_default_btn)
        self._defaults_section = section
        self._inspector_lay.addWidget(section)

    def _build_manga_section(self):
        section = AccordionSection("COMIC PAGE")

        priority_note = QLabel(
            "PAGE + FRAME — these remain visible after photos fill the panels.")
        priority_note.setObjectName("InspectorHint")
        priority_note.setWordWrap(True)
        priority_note.setToolTip(
            "Set the paper/gutter background and panel ink before secondary guides")
        section.body_lay.addWidget(priority_note)

        self._manga_page_btn, self._manga_page_hex = self._color_row(
            section.body_lay, "Page / gutters", QColor("#f2eee5"),
            lambda: self._on_manga_color("page_color",
                                          self._manga_page_btn,
                                          self._manga_page_hex),
            tooltip="Color of the paper and spaces between panels")
        self._manga_border_btn, self._manga_border_hex = self._color_row(
            section.body_lay, "Frame ink", QColor("#241f1b"),
            lambda: self._on_manga_color("border_color",
                                          self._manga_border_btn,
                                          self._manga_border_hex),
            tooltip="Panel frame color; remains visible around imported images")
        self._manga_border_width = self._compact_slider_row(
            section.body_lay, "Ink width", 1, 18, 6, " px",
            lambda value: self._on_manga_number("border_width", value),
            tooltip="Thickness of the hand-drawn panel frame")

        self._manga_image_background = self._option_buttons(
            section.body_lay, "WHEN A PHOTO IS SMALLER",
            (("blur", "Blurred photo"), ("solid", "Panel color")), 2,
            lambda value: self._set_manga_style_option(
                "image_background", value),
            "Choose what fills exposed space behind a shrunken photo",
            (
                "Fill exposed space with a soft, enlarged copy of the photo",
                "Fill exposed space with the palette's empty-panel color",
            ))

        _, self._manga_presets, presets_lay = self._disclosure(
            section.body_lay, "Preset palettes",
            "Optional ready-made page and frame color combinations")
        self._manga_theme = self._option_buttons(
            presets_lay, "Choose a palette",
            ("Warm paper", "Classic ink", "Noir", "Rose pulp", "Night blue"),
            2, self._on_manga_theme,
            tooltip=("Apply a coordinated paper and ink palette; every color "
                     "remains editable"),
            option_tooltips=(
                "Cream paper with warm dark ink",
                "White paper with crisp black ink",
                "Dark page with pale comic frames",
                "Muted rose paper and burgundy ink",
                "Deep blue page with cool pale ink",
            ))

        self._manga_roughness = self._compact_slider_row(
            section.body_lay, "Hand drawn", 0, 90, 34, "",
            lambda value: self._on_manga_number("roughness", value),
            tooltip="How uneven and angled panel edges should feel")

        _, self._manga_guides, guides_lay = self._disclosure(
            section.body_lay, "Empty-panel appearance",
            "Optional colors that disappear after images fill the panels")

        self._manga_empty_btn, self._manga_empty_hex = self._color_row(
            guides_lay, "Empty panels", QColor("#e8e1d5"),
            lambda: self._on_manga_color("empty_color",
                                          self._manga_empty_btn,
                                          self._manga_empty_hex),
            tooltip="Background color for panels without an image")
        self._manga_placeholder_btn, self._manga_placeholder_hex = self._color_row(
            guides_lay, "Indicators", QColor("#746d65"),
            lambda: self._on_manga_color("placeholder_color",
                                          self._manga_placeholder_btn,
                                          self._manga_placeholder_hex),
            tooltip="Open-image indicator color")
        section.setVisible(False)
        self._manga_section = section
        self._inspector_lay.addWidget(section)

    def _build_manga_layout_section(self):
        section = AccordionSection("COMIC LAYOUT")

        live_note = QLabel(
            "START HERE — choose the page feel. Drop images into the panels. "
            "Regenerate gives you another version of that choice.")
        live_note.setObjectName("InspectorHint")
        live_note.setWordWrap(True)
        section.body_lay.addWidget(live_note)

        self._comic_quick_preset = self._option_buttons(
            section.body_lay, "PAGE FEEL",
            (("mixed", "Mixed page"),
             ("classic", "Classic · 6"),
             ("focus", "Big moment · 4"),
             ("action", "Fast action · 8")),
            2, self._on_comic_quick_preset,
            "One click chooses a sensible panel count and composition",
            (
                "Variable panel count and composition; Regenerate makes the next version",
                "Six balanced panels for general storytelling",
                "Four panels with one emphasized image",
                "Eight panels with stronger size contrast",
            ))

        _, self._manga_advanced, advanced = self._disclosure(
            section.body_lay, "Fine tune layout",
            "Optional controls for exact panel count, spacing, and reading order")

        count_tip = ("Choose exactly 4, 6, 7, or 8 panels. Changing this creates "
                     "the new count immediately without discarding loaded images.")
        count_tips = (
            "Four spacious panels for slow pacing",
            "Six panels for a conventional comic page",
            "Seven panels for mixed pacing",
            "Eight compact panels for fast pacing",
        )
        self._manga_panel_count = self._option_buttons(
            advanced, "Exact panel count", ("4", "6", "7", "8"),
            4, self._on_manga_layout_count, count_tip, count_tips)

        composition_tips = (
            "Emphasize one large establishing or climax panel",
            "Keep panel sizes calmer and more evenly paced",
            "Use moderate, readable panels suited to conversations",
            "Create stronger size contrast for faster, dramatic pacing",
        )
        self._manga_composition = self._option_buttons(
            advanced, "Exact composition",
            ("Feature", "Balanced", "Dialogue", "Action"), 2,
            lambda value: self._set_manga_layout_option("composition", value),
            ("Controls storytelling rhythm and relative panel sizes. Feature "
             "emphasizes one panel; Action creates stronger contrast."),
            composition_tips)

        self._manga_margin = self._compact_slider_row(
            advanced, "Page margin", 0, 100, 22, " px",
            lambda value: self._set_manga_layout_option("margin", value),
            tooltip="Space around the outside of the comic page")
        self._manga_row_gutter = self._compact_slider_row(
            advanced, "Row gutter", 0, 80, 18, " px",
            lambda value: self._set_manga_layout_option("row_gutter", value),
            tooltip="Space between horizontal story tiers")
        self._manga_column_gutter = self._compact_slider_row(
            advanced, "Panel gutter", 0, 80, 12, " px",
            lambda value: self._set_manga_layout_option("column_gutter", value),
            tooltip="Space between panels in the same tier")
        self._manga_variation = self._compact_slider_row(
            advanced, "Emphasis", 0, 100, 48, " %",
            lambda value: self._set_manga_layout_option("variation", value),
            tooltip="How strongly panel sizes vary within the composition")

        direction_tip = (
            "Sets image assignment and optional panel-number order within each row")
        self._manga_direction = self._option_buttons(
            advanced, "Reading order",
            (("Right to left", "Right → left"),
             ("Left to right", "Left → right")), 2,
            lambda value: self._set_manga_layout_option(
                "reading_direction", value),
            direction_tip,
            ("Top-right toward bottom-left",
             "Top-left toward bottom-right"))

        self._manga_numbers = QCheckBox("Show panel numbers while editing")
        self._manga_numbers.setToolTip(
            "Reading-order guides are shown on canvas but excluded from export")
        self._manga_numbers.toggled.connect(
            lambda value: self._set_manga_layout_option("show_numbers", value))
        advanced.addWidget(self._manga_numbers)

        note = QLabel(
            "Fine-tune controls update the page live. Loaded images are never discarded.")
        note.setObjectName("InspectorHint")
        note.setWordWrap(True)
        advanced.addWidget(note)

        section.setVisible(False)
        self._manga_layout_section = section
        self._inspector_lay.addWidget(section)

    def _on_manga_layout_count(self, text: str):
        self._set_manga_layout_option("panel_count", int(text))

    def _on_comic_quick_preset(self, name: str):
        if self._updating or self._scene is None:
            return
        presets = {
            "mixed": (0, "Random"),
            "classic": (6, "Balanced"),
            "focus": (4, "Feature"),
            "action": (8, "Action"),
        }
        panel_count, composition = presets[name]
        self._scene.apply_manga_layout_preset(panel_count, composition)
        self.show_manga_settings()

    def _build_collage_layout_section(self):
        section = AccordionSection("COLLAGE LAYOUT")
        live_note = QLabel(
            "Choose a direction, photo count, and layout. Then drop photos "
            "into the frames.")
        live_note.setObjectName("InspectorHint")
        live_note.setWordWrap(True)
        section.body_lay.addWidget(live_note)

        self._collage_orientation = QPushButton("↕  Vertical page")
        self._collage_orientation.setObjectName("OrientationToggle")
        self._collage_orientation.setToolTip(
            "Switch the whole collage between vertical and horizontal")
        self._collage_orientation.clicked.connect(
            self._toggle_collage_orientation)
        section.body_lay.addWidget(self._collage_orientation)

        self._collage_count = PhotoCountStepper(4, self)
        self._collage_count.setToolTip(
            "Use − or + to remove or add a photo frame (2–9)")
        self._collage_count.valueChanged.connect(
            lambda value: self._set_collage_layout_option(
                "photo_count", value))
        section.body_lay.addWidget(self._collage_count)

        layout_label = self._label("LAYOUT")
        layout_label.setToolTip("Tap a picture to choose the frame arrangement")
        section.body_lay.addWidget(layout_label)
        self._collage_layout_type = CollageTemplateStrip(self)
        self._collage_layout_type.setToolTip(
            "Visual previews of the available collage arrangements")
        self._collage_layout_type.currentTextChanged.connect(
            lambda text: self._set_collage_layout_option(
                "layout_type", text))
        section.body_lay.addWidget(self._collage_layout_type)

        shuffle_note = QLabel(
            "Shuffle tries a different layout while keeping your photos.")
        shuffle_note.setObjectName("InspectorHint")
        shuffle_note.setWordWrap(True)
        section.body_lay.addWidget(shuffle_note)

        section.setVisible(False)
        self._collage_layout_section = section
        self._inspector_lay.addWidget(section)

    def _build_collage_fx_section(self):
        section = AccordionSection("COLLAGE COLORS & FRAME")
        priority = QLabel(
            "Background and frame are the primary collage styling controls; "
            "photos cover the frame interiors.")
        priority.setObjectName("InspectorHint")
        priority.setWordWrap(True)
        section.body_lay.addWidget(priority)

        self._collage_bg_btn, self._collage_bg_hex = self._color_row(
            section.body_lay, "Background", QColor("#ffffff"),
            lambda: self._on_collage_color(
                "page_color", self._collage_bg_btn, self._collage_bg_hex),
            tooltip="Canvas color visible around and between photo frames")
        self._collage_frame_btn, self._collage_frame_hex = self._color_row(
            section.body_lay, "Frame color", QColor("#ffffff"),
            lambda: self._on_collage_color(
                "border_color", self._collage_frame_btn, self._collage_frame_hex),
            tooltip="Outline color drawn around each imported photo")
        self._collage_frame_width = self._compact_slider_row(
            section.body_lay, "Frame width", 0, 40, 0, " px",
            lambda value: self._set_collage_style_option("border_width", value),
            tooltip="Outline thickness around every photo frame; zero hides it")
        self._collage_gap = self._compact_slider_row(
            section.body_lay, "Spacing", 0, 120, 18, " px",
            lambda value: self._set_collage_layout_option("gap", value),
            tooltip="Background or frame space separating adjacent photos")
        self._collage_corners = self._compact_slider_row(
            section.body_lay, "Corner radius", 0, 180, 24, " px",
            lambda value: self._set_collage_style_option("corner_radius", value),
            tooltip="Round every photo frame; zero keeps corners square")
        self._collage_margin = self._compact_slider_row(
            section.body_lay, "Outer margin", 0, 160, 28, " px",
            lambda value: self._set_collage_layout_option("margin", value),
            tooltip="Background space around the outside of the collage")

        self._collage_image_background = self._option_buttons(
            section.body_lay, "WHEN A PHOTO IS SMALLER",
            (("blur", "Blurred photo"), ("solid", "Panel color")), 2,
            lambda value: self._set_collage_style_option(
                "image_background", value),
            "Choose what fills exposed space behind a shrunken photo",
            (
                "Instagram-style blurred photo fills the exposed space",
                "The selected palette's frame-box color fills the exposed space",
            ))

        _, self._collage_presets, presets_lay = self._disclosure(
            section.body_lay, "Preset palettes",
            "Optional ready-made background and frame combinations")
        self._collage_theme = self._option_buttons(
            presets_lay, "Choose a palette",
            ("Gallery white", "Midnight", "Warm cream", "Soft blush", "Slate"),
            2, self._on_collage_theme,
            ("Preset pairs update Background and Frame color together; both "
             "remain editable"),
            (
                "Clean white gallery background and frame",
                "Dark background and frame",
                "Cream background with a soft white frame",
                "Blush background with a white frame",
                "Slate background with a pale frame",
            ))

        _, self._collage_saved_presets, saved_lay = self._disclosure(
            section.body_lay, "Saved presets",
            "Save, reuse, rename, update, delete, or make a collage preset the default")
        self._collage_preset_combo = QComboBox()
        self._collage_preset_combo.setToolTip(
            "Choose a named preset to apply it immediately")
        self._collage_preset_combo.currentIndexChanged.connect(
            self._on_collage_preset_selected)
        saved_lay.addWidget(self._collage_preset_combo)
        preset_actions = QHBoxLayout()
        save_preset = QPushButton("Save current…")
        save_preset.setObjectName("LayerActionButton")
        save_preset.setToolTip("Save the current layout and colors with a name")
        save_preset.clicked.connect(self._save_collage_preset_as)
        preset_actions.addWidget(save_preset, stretch=1)
        manage = QPushButton("Manage ▾")
        manage.setObjectName("LayerActionButton")
        manage.setToolTip("Update, rename, delete, or set the selected preset as default")
        menu = QMenu(manage)
        menu.addAction("Update selected", self._update_collage_preset)
        menu.addAction("Rename selected…", self._rename_collage_preset)
        menu.addAction("Use selected on startup", self._default_collage_preset)
        menu.addSeparator()
        menu.addAction("Delete selected…", self._delete_collage_preset)
        manage.setMenu(menu)
        preset_actions.addWidget(manage)
        saved_lay.addLayout(preset_actions)
        self._collage_default_preset = QLabel()
        self._collage_default_preset.setObjectName("InspectorHint")
        saved_lay.addWidget(self._collage_default_preset)
        self._refresh_collage_presets()

        section.setVisible(False)
        self._collage_fx_section = section
        self._inspector_lay.addWidget(section)

    def _set_collage_layout_option(self, key: str, value):
        if not self._updating and self._scene is not None:
            self._scene.set_collage_layout_setting(key, value)
            if key == "photo_count":
                actual = int(
                    self._scene.collage_layout_settings()["photo_count"])
                if self._collage_count.value() != actual:
                    self._updating = True
                    try:
                        self._collage_count.setValue(actual)
                    finally:
                        self._updating = False

    def _toggle_collage_orientation(self):
        if self._updating or self._scene is None:
            return
        current = str(
            self._scene.collage_layout_settings()["aspect_ratio"])
        new_value = (
            "Landscape · 16:9"
            if current != "Landscape · 16:9"
            else "Portrait · 4:5"
        )
        self._scene.set_collage_layout_setting("aspect_ratio", new_value)
        self._sync_collage_orientation(new_value)

    def _sync_collage_orientation(self, aspect: str):
        horizontal = aspect in ("Landscape · 16:9", "Photo · 3:2")
        self._collage_orientation.setText(
            "↔  Horizontal page" if horizontal else "↕  Vertical page")
        self._collage_orientation.setToolTip(
            "Switch to a vertical page" if horizontal
            else "Switch to a horizontal page")
        self._collage_layout_type.set_vertical(not horizontal)

    def _set_collage_style_option(self, key: str, value):
        if not self._updating and self._scene is not None:
            self._scene.set_collage_style(key, value)

    def _set_manga_style_option(self, key: str, value):
        if not self._updating and self._scene is not None:
            self._scene.set_manga_style(key, value)

    def _on_collage_theme(self, name: str):
        if self._updating or self._scene is None:
            return
        self._scene.apply_collage_theme(name)
        self.show_manga_settings()

    def _refresh_collage_presets(self, select_name: str | None = None):
        import collage_presets
        current = select_name or self._selected_collage_preset_name()
        self._collage_preset_combo.blockSignals(True)
        self._collage_preset_combo.clear()
        self._collage_preset_combo.addItem("Choose saved preset…", "")
        for name in sorted(collage_presets.load_all(), key=str.casefold):
            self._collage_preset_combo.addItem(name, name)
        if current:
            index = self._collage_preset_combo.findData(current)
            self._collage_preset_combo.setCurrentIndex(max(0, index))
        self._collage_preset_combo.blockSignals(False)
        default = collage_presets.default_name()
        self._collage_default_preset.setText(
            f"Startup preset: {default or collage_presets.FACTORY_NAME}")

    def _selected_collage_preset_name(self) -> str:
        if not hasattr(self, "_collage_preset_combo"):
            return ""
        return str(self._collage_preset_combo.currentData() or "")

    def _on_collage_preset_selected(self, index: int):
        if self._updating or self._scene is None:
            return
        import collage_presets
        name = str(self._collage_preset_combo.itemData(index) or "")
        preset = collage_presets.load_all().get(name)
        if preset is not None:
            self._scene.apply_collage_preset(preset)
            self.show_manga_settings()

    def _save_collage_preset_as(self):
        if self._scene is None:
            return
        name, accepted = QInputDialog.getText(
            self, "Save Collage Preset", "Preset name:")
        name = name.strip()
        if not accepted or not name:
            return
        import collage_presets
        if name in collage_presets.load_all():
            overwrite = QMessageBox.question(
                self, "Replace Preset", f"Replace the preset “{name}”?")
            if overwrite != QMessageBox.StandardButton.Yes:
                return
        collage_presets.save(name, self._scene.collage_preset())
        self._refresh_collage_presets(name)

    def _update_collage_preset(self):
        name = self._selected_collage_preset_name()
        if name and self._scene is not None:
            import collage_presets
            collage_presets.save(name, self._scene.collage_preset())
            self._refresh_collage_presets(name)

    def _rename_collage_preset(self):
        old_name = self._selected_collage_preset_name()
        if not old_name:
            return
        new_name, accepted = QInputDialog.getText(
            self, "Rename Collage Preset", "Preset name:", text=old_name)
        new_name = new_name.strip()
        if not accepted or not new_name or new_name == old_name:
            return
        import collage_presets
        if new_name in collage_presets.load_all():
            QMessageBox.information(
                self, "Preset Exists", "Choose a different preset name.")
            return
        collage_presets.rename(old_name, new_name)
        self._refresh_collage_presets(new_name)

    def _default_collage_preset(self):
        name = self._selected_collage_preset_name()
        if name:
            import collage_presets
            collage_presets.set_default(name)
            self._refresh_collage_presets(name)

    def _delete_collage_preset(self):
        name = self._selected_collage_preset_name()
        if not name:
            return
        answer = QMessageBox.question(
            self, "Delete Collage Preset", f"Delete the preset “{name}”?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        import collage_presets
        collage_presets.delete(name)
        self._refresh_collage_presets()

    def _on_collage_color(self, key: str, btn, label):
        if self._scene is None:
            return
        current = QColor(self._scene.collage_style()[key])
        color = pick_color(btn, current, self, allow_alpha=False)
        if color is not None:
            self._scene.set_collage_style(key, color)
            self._set_color(btn, label, color)

    def _set_manga_layout_option(self, key: str, value):
        if not self._updating and self._scene is not None:
            self._scene.set_manga_layout_setting(key, value)

    def _on_manga_theme(self, name: str):
        if self._updating or self._scene is None:
            return
        self._scene.apply_manga_theme(name)
        # A palette is an FX edit, not a navigation event. Sync its swatches
        # in place and leave the user on the tab they deliberately chose.
        style = self._scene.manga_style()
        self._updating = True
        try:
            for key, btn, label in (
                ("page_color", self._manga_page_btn, self._manga_page_hex),
                ("empty_color", self._manga_empty_btn, self._manga_empty_hex),
                ("border_color", self._manga_border_btn,
                 self._manga_border_hex),
                ("placeholder_color", self._manga_placeholder_btn,
                 self._manga_placeholder_hex),
            ):
                self._set_color(btn, label, QColor(style[key]))
        finally:
            self._updating = False

    def _on_manga_color(self, key: str, btn, label):
        if self._scene is None:
            return
        current = QColor(self._scene.manga_style()[key])
        color = pick_color(btn, current, self, allow_alpha=False)
        if color is not None:
            self._scene.set_manga_style(key, color)
            self._set_color(btn, label, color)

    def _on_manga_number(self, key: str, value: int):
        if not self._updating and self._scene is not None:
            self._scene.set_manga_style(key, value)

    def _flash_button(self, btn: QPushButton, text: str):
        original = btn.text()
        btn.setText(text)
        QTimer.singleShot(1400, lambda: btn.setText(original))

    def _on_save_defaults(self):
        if self._bubble is not None:
            bubble_defaults.save_from_bubble(self._bubble)
            self._flash_button(self._save_default_btn, "Saved ✓")

    def _on_reset_defaults(self):
        bubble_defaults.reset()
        self._flash_button(self._reset_default_btn, "Reset ✓")

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
        # A short-lived offscreen window can be destroyed before this deferred
        # setup runs. In the live editor the layout is present; during teardown
        # there is simply nothing left to populate.
        if self._font_combo_placeholder is None:
            return
        self._font_combo = QComboBox()
        self._font_combo.setEditable(True)
        self._font_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._font_combo.setFixedHeight(32)
        self._font_combo.setToolTip("Font family")
        families = sorted(QFontDatabase.families(), key=str.casefold)
        self._font_combo.addItems(families)
        self._font_combo.currentTextChanged.connect(self._on_font_family_name)
        try:
            idx = self._font_row_layout.indexOf(self._font_combo_placeholder)
        except RuntimeError:
            self._font_combo.deleteLater()
            self._font_combo = None
            return
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

    def _disclosure(self, layout, text, tooltip=""):
        toggle = QToolButton()
        toggle.setObjectName("InspectorDisclosure")
        toggle.setText(text)
        toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setCheckable(True)
        toggle.setToolTip(tooltip)
        body = QWidget()
        body.setObjectName("InspectorDisclosureBody")
        body.setVisible(False)
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 2, 0, 0)
        body_lay.setSpacing(7)

        def _toggle(opened):
            toggle.setArrowType(
                Qt.ArrowType.DownArrow if opened else Qt.ArrowType.RightArrow)
            body.setVisible(opened)

        toggle.toggled.connect(_toggle)
        layout.addWidget(toggle)
        layout.addWidget(body)
        return toggle, body, body_lay

    def _option_buttons(self, layout, label_text, choices, columns, callback,
                        tooltip="", option_tooltips=None):
        label = self._label(label_text)
        label.setToolTip(tooltip)
        layout.addWidget(label)
        choices_widget = OptionButtonGrid(
            choices, columns=columns, tooltips=option_tooltips, parent=self)
        choices_widget.setToolTip(tooltip)
        choices_widget.currentTextChanged.connect(callback)
        layout.addWidget(choices_widget)
        return choices_widget

    def _color_row(self, layout, label_text, color, callback, tooltip=""):
        row = QHBoxLayout()
        label_widget = self._label(label_text)
        label_widget.setToolTip(tooltip)
        row.addWidget(label_widget)
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
        label_widget = self._label(label_text)
        label_widget.setToolTip(tooltip)
        row.addWidget(label_widget)
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
        label_widget = self._label(label_text)
        label_widget.setToolTip(tooltip)
        row.addWidget(label_widget)
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
        label_widget = self._label(label_text)
        label_widget.setToolTip(tooltip)
        row.addWidget(label_widget)
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

    SHAPE_TAB = 0
    TEXT_TAB = 1
    FX_TAB = 2
    LAYERS_TAB = 3

    def _show_tab(self, index: int):
        """Jump to the tab holding the controls for what was just selected."""
        if self._tabs.currentIndex() != index:
            self._tabs.setCurrentIndex(index)

    def _stack_tab(self, index: int):
        self._stack.setCurrentIndex(index)
        if index == self.LAYERS_TAB:
            self._refresh_layers()

    def _configure_tabs_for_page_mode(self):
        """Keep page controls and selected-object controls from colliding."""
        collage = bool(self._scene and self._scene.is_collage_mode())
        comic = bool(self._scene and self._scene.is_manga_mode())
        page_mode = collage or comic
        self._tabs.setTabText(self.SHAPE_TAB,
                              "Collage" if collage else "Comic" if comic else "Shape")
        self._tabs.setTabText(self.TEXT_TAB, "Text")
        self._tabs.setTabText(self.FX_TAB, "Selected FX" if page_mode else "FX")
        self._tabs.setTabText(self.LAYERS_TAB, "Layers")
        self._tabs.setTabVisible(self.TEXT_TAB, not page_mode)
        if collage:
            self._shape_intro_title.setText("Photo collage")
            self._shape_intro_text.setText(
                "Choose the frame layout, spacing, colors, and finish.")
        elif comic:
            self._shape_intro_title.setText("Comic page")
            self._shape_intro_text.setText(
                "Shape the page rhythm, panels, gutters, and paper.")
        else:
            self._shape_intro_title.setText("Shape")
            self._shape_intro_text.setText(
                "Choose the bubble form, fill, border, and tail.")
        self._fx_intro_title.setText("Selected effects" if page_mode else "Effects")
        self._fx_intro_text.setText(
            "Edit effects attached to the active frame."
            if page_mode else
            "Add shadows, expression marks, photos, and motion effects.")

    def _configure_tabs_for_object(self):
        self._tabs.setTabText(self.SHAPE_TAB, "Shape")
        self._tabs.setTabText(self.TEXT_TAB, "Text")
        self._tabs.setTabText(self.FX_TAB, "FX")
        self._tabs.setTabText(self.LAYERS_TAB, "Layers")
        self._tabs.setTabVisible(self.TEXT_TAB, True)
        self._shape_intro_title.setText("Shape")
        self._shape_intro_text.setText(
            "Choose the bubble form, fill, border, and tail.")
        self._fx_intro_title.setText("Effects")
        self._fx_intro_text.setText(
            "Add shadows, expression marks, photos, and motion effects.")

    # ------------------------------------------------------------------
    # Public update API
    # ------------------------------------------------------------------

    def update_for_bubble(self, bubble):
        self._configure_tabs_for_object()
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = bubble
        self._media  = None
        self._redact_item = None
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(False)
        self._spacing_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._layer_section.setVisible(False)
        self._set_placeholder_visible(False)
        self._defaults_section.setVisible(True)
        self._set_bubble_sections_visible(True)
        self._set_controls_enabled(True)
        self._updating = True
        try:
            self._text_edit.setPlainText(bubble.get_text())
            self._update_char_count()
            self._sync_lobe_edits(bubble)
            style = bubble.get_style()
            self._spacing_section.setVisible(style == "text")
            # Tailless styles (text / scrim / caption) have no bubble body to
            # attach a tail to — hide the whole section rather than offer
            # controls that do nothing.
            from bubble import TAILED_STYLES
            self._tail_section.setVisible(style in TAILED_STYLES)
            # A photo needs a filled silhouette to sit in; text and caption are
            # bare glyphs, so the inset has nothing to clip to.
            self._photo_section.setVisible(style not in ("text", "caption"))
            # Likewise the fill/border of a bare-glyph style isn't a "bubble".
            self._border_section.setVisible(style != "text")
            if style == "text":
                self._v_spacing.setValue(int(bubble.get_line_spacing()))
                self._h_spacing.setValue(int(bubble.get_letter_spacing()))
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
            self._check_font_tile(font.family())
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
            tail_shape = bubble.get_tail_shape()
            for key, btn in self._tail_shape_btns.items():
                btn.setChecked(key == tail_shape)
            tail_count = bubble.get_tail_count()
            for n, btn in self._tail_count_btns.items():
                btn.setChecked(n == tail_count)
            self._set_color(self._outline_color_btn, None,
                            bubble.get_text_outline_color())
            self._outline_width.setValue(bubble.get_text_outline_width())
            self._border_width.setValue(bubble.get_border_width())
            self._sync_outline_buttons(bubble.get_border_width())
            self._sync_inset_controls(bubble)
            active = bubble.get_accents()
            for k, btn in self._accent_btns.items():
                btn.setChecked(k in active)
            self._accent_amount.setValue(bubble.get_accent_amount())
            self._set_shadow_controls(bubble.get_shadow())
            self._sync_shadow_presets(bubble.get_shadow())
        finally:
            self._updating = False
        self._refresh_layers()

    def update_for_media(self, media_item):
        self._configure_tabs_for_object()
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = None
        self._media  = media_item
        self._redact_item = None
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(False)
        self._spacing_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._layer_section.setVisible(True)
        self._set_placeholder_visible(False)
        self._set_controls_enabled(False)
        self._enable_style_add_mode()
        self._layer_section.setEnabled(True)
        self._layer_opacity.setValue(round(media_item.opacity() * 100))
        self._refresh_layers()

    def show_dual_settings(self):
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = None
        self._media  = None
        self._redact_item = None
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(False)
        self._spacing_section.setVisible(False)
        self._set_controls_enabled(False)
        self._layer_section.setEnabled(False)
        self._layer_section.setVisible(False)
        self._set_placeholder_visible(False)
        self._dual_section.setVisible(True)

    def show_manga_settings(self):
        self._configure_tabs_for_page_mode()
        self._bubble = None
        self._media = None
        self._redact_item = None
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(False)
        self._spacing_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._layer_section.setVisible(False)
        self._defaults_section.setVisible(False)
        self._set_bubble_sections_visible(False)
        self._set_placeholder_visible(False)
        is_collage = bool(self._scene and self._scene.is_collage_mode())
        self._manga_section.setVisible(not is_collage)
        self._manga_layout_section.setVisible(not is_collage)
        self._collage_layout_section.setVisible(is_collage)
        self._collage_fx_section.setVisible(is_collage)
        self._show_tab(self.SHAPE_TAB)
        if self._scene is None:
            return
        self._updating = True
        try:
            if is_collage:
                style = self._scene.collage_style()
                layout = self._scene.collage_layout_settings()
                for key, btn, label in (
                    ("page_color", self._collage_bg_btn, self._collage_bg_hex),
                    ("border_color", self._collage_frame_btn,
                     self._collage_frame_hex),
                ):
                    self._set_color(btn, label, QColor(style[key]))
                self._collage_frame_width.setValue(int(style["border_width"]))
                self._collage_corners.setValue(int(style["corner_radius"]))
                self._collage_image_background.setCurrentText(
                    str(style["image_background"]))
                self._collage_count.setValue(int(layout["photo_count"]))
                self._collage_layout_type.setCurrentText(
                    str(layout["layout_type"]))
                aspect = str(layout["aspect_ratio"])
                self._sync_collage_orientation(aspect)
                self._collage_margin.setValue(int(layout["margin"]))
                self._collage_gap.setValue(int(layout["gap"]))
            else:
                style = self._scene.manga_style()
                layout = self._scene.manga_layout_settings()
                for key, btn, label in (
                    ("page_color", self._manga_page_btn, self._manga_page_hex),
                    ("empty_color", self._manga_empty_btn, self._manga_empty_hex),
                    ("border_color", self._manga_border_btn,
                     self._manga_border_hex),
                    ("placeholder_color", self._manga_placeholder_btn,
                     self._manga_placeholder_hex),
                ):
                    self._set_color(btn, label, QColor(style[key]))
                self._manga_border_width.setValue(int(style["border_width"]))
                self._manga_roughness.setValue(int(style["roughness"]))
                self._manga_image_background.setCurrentText(
                    str(style["image_background"]))
                count = int(layout["panel_count"])
                if count == 0:
                    self._manga_panel_count.clearSelection()
                else:
                    self._manga_panel_count.setCurrentText(str(count))
                composition = str(layout["composition"])
                if composition == "Random":
                    self._manga_composition.clearSelection()
                else:
                    self._manga_composition.setCurrentText(composition)
                self._manga_margin.setValue(int(layout["margin"]))
                self._manga_row_gutter.setValue(int(layout["row_gutter"]))
                self._manga_column_gutter.setValue(int(layout["column_gutter"]))
                self._manga_variation.setValue(int(layout["variation"]))
                self._manga_direction.setCurrentText(
                    str(layout["reading_direction"]))
                self._manga_numbers.setChecked(bool(layout["show_numbers"]))
                quick = {
                    (0, "Random"): "mixed",
                    (6, "Balanced"): "classic",
                    (4, "Feature"): "focus",
                    (8, "Action"): "action",
                }.get((count, str(layout["composition"])))
                if quick:
                    self._comic_quick_preset.setCurrentText(quick)
                else:
                    self._comic_quick_preset.clearSelection()
        finally:
            self._updating = False

    def clear(self):
        self._configure_tabs_for_object()
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = None
        self._media  = None
        self._redact_item = None
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(False)
        self._spacing_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._set_controls_enabled(False)
        self._enable_style_add_mode()
        self._layer_section.setEnabled(False)
        self._layer_section.setVisible(False)
        # No selection: hide the controls entirely and show the placeholders.
        self._set_bubble_sections_visible(False)
        self._defaults_section.setVisible(False)
        self._set_placeholder_visible(True)
        self._refresh_layers()

    def clear_selection(self):
        self._configure_tabs_for_object()
        self._manga_section.setVisible(False)
        self._manga_layout_section.setVisible(False)
        self._collage_layout_section.setVisible(False)
        self._collage_fx_section.setVisible(False)
        self._bubble = None
        self._media = None
        self._redact_item = None
        self._redact_section.setVisible(False)
        self._lines_section.setVisible(False)
        self._spacing_section.setVisible(False)
        self._dual_section.setVisible(False)
        self._set_controls_enabled(False)
        self._enable_style_add_mode()
        self._layer_section.setEnabled(False)
        self._layer_section.setVisible(False)
        # No selection: hide the controls entirely and show the placeholders.
        self._set_bubble_sections_visible(False)
        self._defaults_section.setVisible(False)
        self._set_placeholder_visible(True)
        self._refresh_layers()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_controls_enabled(self, enabled: bool):
        for widget in (
            self._text_section, self._fill_btn, self._stroke_btn,
            self._font_size, self._weight_combo, self._text_color_btn,
            self._tail_position, self._tail_width, self._border_width,

            self._bubble_opacity,
            self._outline_color_btn, self._outline_width,
            self._save_default_btn, self._accent_amount,
        ):
            if hasattr(widget, "setEnabled"):
                widget.setEnabled(enabled)
        for btn in self._style_btns.values():
            btn.setEnabled(enabled)
        for btn in self._font_tiles.values():
            btn.setEnabled(enabled)
        for btn in self._align_btns.values():
            btn.setEnabled(enabled)
        for btn in self._outline_btns.values():
            btn.setEnabled(enabled)
        for btn in self._balloon_preset_btns:
            btn.setEnabled(enabled)
        for btn in self._accent_btns.values():
            btn.setEnabled(enabled)
        for btn in self._tail_shape_btns.values():
            btn.setEnabled(enabled)
        for btn in self._tail_count_btns.values():
            btn.setEnabled(enabled)
        for btn in self._shadow_preset_btns:
            btn.setEnabled(enabled)
        # Detail controls follow the shadow's own on/off state, not selection.
        if enabled and self._bubble is not None:
            self._set_shadow_detail_enabled(
                bool(self._bubble.get_shadow().get("enabled")))
        else:
            self._set_shadow_detail_enabled(False)

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

    def _set_placeholder_visible(self, visible: bool):
        for ph in getattr(self, "_placeholders", ()):
            ph.setVisible(visible)

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
        self._update_char_count()

    def _update_char_count(self):
        self._char_count.setText(f"{len(self._text_edit.toPlainText())}")

    def focus_lobe_editor(self, index: int):
        """Show the Text tab and put the caret in the requested lobe's box."""
        self._show_tab(self.TEXT_TAB)
        if 0 <= index < len(self._lobe_edits):
            _lbl, edit = self._lobe_edits[index]
            if edit.isVisible():
                edit.setFocus()
                edit.moveCursor(edit.textCursor().MoveOperation.End)

    def _on_lobe_text_changed(self, index: int):
        if self._bubble and not self._updating and self._bubble.is_lobed():
            _lbl, edit = self._lobe_edits[index]
            self._bubble.set_lobe_text(index, edit.toPlainText())

    def _sync_lobe_edits(self, bubble):
        n = bubble.lobe_count() if bubble.is_lobed() else 0
        # A lobed balloon has no single text body — swap the one box for N.
        self._text_edit.setVisible(n == 0)
        self._char_count.setVisible(n == 0)
        for i, (lbl, edit) in enumerate(self._lobe_edits):
            show = i < n
            lbl.setVisible(show)
            edit.setVisible(show)
            if show:
                edit.blockSignals(True)
                edit.setPlainText(bubble.get_lobe_text(i))
                edit.blockSignals(False)

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

    def _populate_font_tiles(self):
        if self._font_tiles:
            return
        available = set(QFontDatabase.families())
        families = [f for f in self.FONT_CANDIDATES if f in available]
        if len(families) < 2:
            # Bundled fonts missing (broken install / dev run without fonts/):
            # fall back to any display-ish system faces so the grid isn't blank.
            for fallback in ("Impact", "Comic Sans MS", "Georgia", "Verdana",
                             "DejaVu Sans", "Noto Sans", "Liberation Sans"):
                if fallback in available and fallback not in families:
                    families.append(fallback)
        families = families[:12]
        cols = 2
        for i, family in enumerate(families):
            btn = QToolButton()
            btn.setObjectName("FontTile")
            # Sample text ABOVE the family name: you can read the face AND know
            # what it's called. A 13 px "Aa1" told you neither.
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.setText(self.FONT_LABELS.get(family, family))
            f = QFont(family, 17)
            f.setBold(family in ("Comic Neue", "Inter"))
            btn.setFont(f)
            btn.setCheckable(True)
            btn.setFixedHeight(46)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding,
                              QSizePolicy.Policy.Fixed)
            btn.setToolTip(family)
            btn.setEnabled(self._bubble is not None)
            btn.clicked.connect(lambda _c, fam=family: self._on_font_tile(fam))
            self._font_tiles[family] = btn
            self._font_tile_grid.addWidget(btn, i // cols, i % cols)
        if self._bubble is not None:
            self._check_font_tile(self._bubble.get_font().family())

    def _on_font_tile(self, family: str):
        self._on_font_family(QFont(family))
        self._check_font_tile(family)

    def _check_font_tile(self, family: str):
        """Reflect the current family in the tile grid (none may match)."""
        fam = family.casefold()
        for name, btn in self._font_tiles.items():
            btn.setChecked(name.casefold() == fam)

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
        color = pick_color(self._text_color_btn, old, self, allow_alpha=False)
        if color is not None and color.isValid():
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
        color = pick_color(self._fill_btn, old, self, allow_alpha=True)
        if color is not None and color.isValid():
            self._undo_stack.push(FillColorChangeCommand(self._bubble, old, color))
            self._set_color(self._fill_btn, self._fill_hex, color)

    def _on_border_color(self):
        if not self._bubble or not self._undo_stack:
            return
        old = self._bubble.get_border_color()
        color = pick_color(self._stroke_btn, old, self, allow_alpha=False)
        if color is not None and color.isValid():
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
        value = float(value)
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_border_width()
            if old != value:
                self._undo_stack.push(BorderWidthChangeCommand(self._bubble, old, value))
            self._updating = True
            try:
                self._border_width.setValue(value)
                self._sync_outline_buttons(value)
            finally:
                self._updating = False

    def _on_tail_shape(self, shape: str):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_tail_shape()
            if old != shape:
                self._undo_stack.push(TailShapeChangeCommand(self._bubble, old, shape))

    def _on_tail_count(self, count: int):
        if self._bubble and not self._updating and self._undo_stack:
            old = self._bubble.get_tail_count()
            if old != count:
                self._undo_stack.push(TailCountChangeCommand(self._bubble, old, count))

    def _on_text_outline_color(self):
        if not self._bubble or not self._undo_stack:
            return
        old_c = self._bubble.get_text_outline_color()
        old_w = self._bubble.get_text_outline_width()
        color = pick_color(self._outline_color_btn, old_c, self, allow_alpha=False)
        if color is not None and color.isValid():
            # Picking a colour while the outline is off turns it on.
            new_w = old_w if old_w > 0 else 2.0
            self._undo_stack.push(TextOutlineChangeCommand(
                self._bubble, old_c, old_w, color, new_w))
            self._set_color(self._outline_color_btn, None, color)

    def _on_text_outline_width(self, value: float):
        if self._bubble and not self._updating and self._undo_stack:
            old_c = self._bubble.get_text_outline_color()
            old_w = self._bubble.get_text_outline_width()
            if old_w != value:
                self._undo_stack.push(TextOutlineChangeCommand(
                    self._bubble, old_c, old_w, old_c, value))

    def _on_shadow_preset(self, name: str):
        k = self._outline_scale()      # bubble size relative to the default
        presets = {
            "None":  {"enabled": False},
            "Soft":  {"enabled": True, "color": QColor(0, 0, 0),
                      "blur": round(16 * k), "offset_x": round(7 * k),
                      "offset_y": round(8 * k), "opacity": 55},
            "Solid": {"enabled": True, "color": QColor(0, 0, 0),
                      "blur": 0, "offset_x": round(9 * k),
                      "offset_y": round(10 * k), "opacity": 100},
        }
        preset = presets.get(name)
        if preset and self._bubble and self._undo_stack:
            old = self._bubble.get_shadow()
            new = dict(old)
            new.update(preset)
            self._undo_stack.push(ShadowChangeCommand(self._bubble, old, new))
            self._updating = True
            try:
                self._set_shadow_controls(self._bubble.get_shadow())
                self._sync_shadow_presets(self._bubble.get_shadow())
            finally:
                self._updating = False

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
        self._set_shadow_detail_enabled(bool(shadow["enabled"]))
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

    def _shadow_detail_widgets(self):
        return (self._shadow_color_btn, self._shadow_blur, self._shadow_x,
                self._shadow_y, self._shadow_opacity)

    def _set_shadow_detail_enabled(self, on: bool):
        for widget in self._shadow_detail_widgets():
            widget.setEnabled(on)

    def _on_shadow_enabled(self, checked: bool):
        self._set_shadow_detail_enabled(checked)
        self._shadow_update(enabled=checked)

    def _sync_shadow_presets(self, shadow: dict):
        """Light up whichever preset row entry matches the current shadow."""
        if not shadow.get("enabled"):
            name = "None"
        elif int(shadow.get("blur", 0)) <= 2:
            name = "Solid"
        else:
            name = "Soft"
        for btn in self._shadow_preset_btns:
            btn.setChecked(btn.text() == name)

    def _on_shadow_color(self):
        if not self._bubble:
            return
        old   = self._bubble.get_shadow()
        color = pick_color(self._shadow_color_btn, old["color"], self,
                           allow_alpha=False)
        if color is not None and color.isValid():
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
                # An empty bubble has no lines at all — indexing [0] crashed.
                lines = item.get_text().splitlines()
                label = (lines[0][:28] if lines else "") or "empty"
                items.append((item.zValue(), item, f"Bubble — {label}"))
            elif isinstance(item, RedactionItem):
                name = "Pixelate" if item.get_mode() == "pixelate" else "Blur"
                frame = getattr(item, "_page_panel_index", None)
                label = (f"Frame {frame + 1} · {name}"
                         if frame is not None else f"{name} box")
                items.append((item.zValue(), item, label))
            elif isinstance(item, SpeedLinesItem):
                frame = getattr(item, "_page_panel_index", None)
                label = (f"Frame {frame + 1} · Lines"
                         if frame is not None else "Speed lines")
                items.append((item.zValue(), item, label))
            elif isinstance(item, MediaItem) and getattr(item, "_is_overlay", False):
                items.append((item.zValue(), item, "Image layer"))
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
        has_layers = bool(items)
        self._layers_stack.setCurrentWidget(
            self._layers_list if has_layers else self._layers_empty)
        self._layers_actions.setVisible(has_layers)
        self._refreshing_layers = False

    def _normalize_layer_z_values(self):
        if self._scene is None:
            return
        items = []
        for item in self._scene.items():
            if isinstance(item, (BubbleItem, RedactionItem, SpeedLinesItem)):
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
            # Do not leave the user stranded on the layer list: the selected
            # effect's live controls are the useful next destination.
            if isinstance(item, RedactionItem):
                self.update_for_redaction(item)
            elif isinstance(item, SpeedLinesItem):
                self.update_for_speedlines(item)

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
                if isinstance(item, (BubbleItem, RedactionItem, SpeedLinesItem))
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
