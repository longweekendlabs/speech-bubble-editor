"""
bubble.py — BubbleItem: draggable, resizable speech bubble QGraphicsItem.

Key design: tail + body are united into ONE QPainterPath so the border
traces the outer edge seamlessly — no seam, no black line cutting the tail.

Styles:  "oval" | "cloud" | "rect" | "spiky" | "text" | "scrim" | "caption"
"""

import math
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsSceneMouseEvent,
    QGraphicsSceneContextMenuEvent, QMenu, QStyleOptionGraphicsItem,
    QWidget
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QCursor
)
from PyQt6.QtCore import Qt, QRectF, QPointF

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HANDLE_SIZE   = 10
TAIL_DOT_R    = 9
DEFAULT_W     = 220
DEFAULT_H     = 130
DEFAULT_STYLE = "oval"
ANCHORS = ["TL", "TC", "TR", "ML", "MR", "BL", "BC", "BR"]


# ---------------------------------------------------------------------------
# TailHandle — manual-drag red dot
# ---------------------------------------------------------------------------

class TailHandle(QGraphicsEllipseItem):
    """
    Red dot the user drags to repoint the tail.
    Manual drag (no ItemIsMovable) so it doesn't fight parent item movement.
    """

    def __init__(self, parent_bubble: "BubbleItem"):
        r = TAIL_DOT_R
        super().__init__(-r, -r, r * 2, r * 2, parent_bubble)
        self._bubble   = parent_bubble
        self._dragging = False

        self.setBrush(QBrush(QColor(220, 40, 40)))
        self.setPen(QPen(QColor(255, 255, 255), 2.0))
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setToolTip("Drag to repoint tail")

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._dragging:
            new_pos = self._bubble.mapFromScene(event.scenePos())
            self.setPos(new_pos)
            self._bubble.prepareGeometryChange()
            self._bubble.update()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# ResizeHandle
# ---------------------------------------------------------------------------

class ResizeHandle(QGraphicsRectItem):
    CURSORS = {
        "TL": Qt.CursorShape.SizeFDiagCursor, "TR": Qt.CursorShape.SizeBDiagCursor,
        "BL": Qt.CursorShape.SizeBDiagCursor, "BR": Qt.CursorShape.SizeFDiagCursor,
        "TC": Qt.CursorShape.SizeVerCursor,   "BC": Qt.CursorShape.SizeVerCursor,
        "ML": Qt.CursorShape.SizeHorCursor,   "MR": Qt.CursorShape.SizeHorCursor,
    }

    def __init__(self, anchor: str, parent_bubble: "BubbleItem"):
        s = HANDLE_SIZE
        super().__init__(-s / 2, -s / 2, s, s, parent_bubble)
        self._anchor      = anchor
        self._bubble      = parent_bubble
        self._dragging    = False
        self._start_mouse = QPointF()
        self._start_rect  = QRectF()

        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(80, 120, 220), 1.5))
        self.setZValue(11)
        self.setCursor(QCursor(self.CURSORS[anchor]))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging    = True
            self._start_mouse = event.scenePos()
            self._start_rect  = QRectF(self._bubble.body_rect)
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if not self._dragging:
            return
        delta = event.scenePos() - self._start_mouse
        r, a, MIN = QRectF(self._start_rect), self._anchor, 60

        if "L" in a:
            nl = r.left() + delta.x()
            if r.right() - nl >= MIN: r.setLeft(nl)
        if "R" in a:
            nr = r.right() + delta.x()
            if nr - r.left() >= MIN: r.setRight(nr)
        if "T" in a:
            nt = r.top() + delta.y()
            if r.bottom() - nt >= MIN: r.setTop(nt)
        if "B" in a:
            nb = r.bottom() + delta.y()
            if nb - r.top() >= MIN: r.setBottom(nb)

        self._bubble.set_body_rect(r)
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            old_rect = self._start_rect
            new_rect = self._bubble.body_rect
            if old_rect != new_rect:
                stack = self._bubble._undo_stack()
                if stack:
                    from undo_commands import ResizeBubbleCommand
                    stack.push(ResizeBubbleCommand(self._bubble, old_rect, new_rect))
        event.accept()


# ---------------------------------------------------------------------------
# BubbleItem
# ---------------------------------------------------------------------------

class BubbleItem(QGraphicsItem):
    """Speech bubble on the photo canvas."""

    def __init__(self, scene_x: float, scene_y: float,
                 style: str = DEFAULT_STYLE, parent=None):
        super().__init__(parent)

        hw, hh = DEFAULT_W / 2, DEFAULT_H / 2
        self._body_rect = QRectF(-hw, -hh, DEFAULT_W, DEFAULT_H)

        self._style        = style
        self._fill_color   = QColor(255, 255, 255, 240)
        self._border_color = QColor(20, 20, 20)
        self._border_width = 2.0

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,            True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,         True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable,          True)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.setPos(scene_x, scene_y)

        # Undo tracking state
        self._drag_start_pos:  QPointF | None = None   # set on press, cleared on release
        self._text_before_edit: str | None    = None   # set on double-click
        self._is_editing:      bool           = False  # True while text editor is open

        # Tail handle
        self._tail = TailHandle(self)
        self._tail.setPos(0, hh + 70)
        self._tail.setVisible(False)

        # Text — default font is "Klee One" (manga/UTF-8 friendly, bundled).
        # Falls back gracefully to system fonts if the file isn't present.
        _default_font = QFont("Klee One", 20)
        _default_font.setBold(True)
        self._font_pt: int = 20          # user's preferred point size; auto-shrink
                                          # may reduce it temporarily but will try
                                          # to restore it when text is removed.
        self._text_item = QGraphicsTextItem(self)
        self._text_item.setPlainText("Type here...")
        self._text_item.setDefaultTextColor(QColor(15, 15, 15))
        self._text_item.setFont(_default_font)
        self._text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self._text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        # Grow / shrink font in real time as the user types or pastes text
        self._text_item.document().contentsChanged.connect(self._on_text_contents_changed)
        self._reposition_text()

        # Resize handles
        self._handles: dict[str, ResizeHandle] = {}
        for anchor in ANCHORS:
            h = ResizeHandle(anchor, self)
            h.setVisible(False)
            self._handles[anchor] = h
        self._update_handle_positions()

    # ------------------------------------------------------------------
    # Getters (used by PropertiesPanel)
    # ------------------------------------------------------------------

    @property
    def body_rect(self) -> QRectF:
        return QRectF(self._body_rect)

    def get_style(self) -> str:
        return self._style

    def get_font(self) -> QFont:
        return QFont(self._text_item.font())

    def get_text_color(self) -> QColor:
        return QColor(self._text_item.defaultTextColor())

    def get_fill_color(self) -> QColor:
        return QColor(self._fill_color)

    def get_border_color(self) -> QColor:
        return QColor(self._border_color)

    def get_border_width(self) -> float:
        return self._border_width

    def get_text(self) -> str:
        return self._text_item.toPlainText()

    # ------------------------------------------------------------------
    # Setters
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Internal helper — scene notification for properties panel refresh
    # ------------------------------------------------------------------

    def _notify_changed(self):
        """Tell the scene that this bubble's visual properties changed.

        PhotoScene.bubble_changed is picked up by MainWindow, which refreshes
        the PropertiesPanel whenever the changed bubble is currently selected.
        """
        scene = self.scene()
        if scene and hasattr(scene, 'bubble_changed'):
            scene.bubble_changed.emit(self)

    # ------------------------------------------------------------------

    def set_style(self, style: str):
        # prepareGeometryChange() BEFORE we change anything so Qt invalidates
        # the OLD bounding rect (which included the tail area).
        # Without this, switching styles can leave ghost artefacts on screen.
        self.prepareGeometryChange()
        if self.scene():
            self.scene().update()   # force full scene repaint for good measure
        prev_style = self._style
        self._style = style
        # Tail is hidden for styles that have no tail
        self._tail.setVisible(
            self.isSelected() and style not in ("text", "rect", "scrim", "caption"))

        # Switching AWAY from scrim: body_rect is still full-canvas-width and
        # flat, which breaks cloud/oval/spiky shape geometry (Audi logo effect).
        # Reset to the default speech-bubble dimensions before changing style.
        if prev_style == "scrim" and style != "scrim":
            hw, hh = DEFAULT_W / 2, DEFAULT_H / 2
            self._body_rect = QRectF(-hw, -hh, DEFAULT_W, DEFAULT_H)
            self._reposition_text()
            self._update_handle_positions()

        # Scrim: apply dark-strip defaults, compact height, snap to full width
        if style == "scrim" and prev_style != "scrim":
            self._fill_color   = QColor(0, 0, 0, 200)    # 78 % opacity — Instagram look
            self._border_width = 0.0
            self._text_item.setDefaultTextColor(QColor(255, 255, 255))
            scrim_font = QFont("Montserrat", 24)
            scrim_font.setBold(True)
            self._font_pt = 24
            self._text_item.setFont(scrim_font)
            # Compact height: ~7 % of scene height so it's a slim caption strip
            scene = self.scene()
            if scene and hasattr(scene, 'has_photo') and scene.has_photo():
                compact_h = max(44.0, scene.sceneRect().height() * 0.07)
            else:
                compact_h = 60.0
            cur_w = self._body_rect.width()
            self._body_rect = QRectF(-cur_w / 2, -compact_h / 2, cur_w, compact_h)
            self._snap_to_scrim()

        # Caption: stroke-text overlay — no background, no tail, white text by default
        if style == "caption" and prev_style != "caption":
            self._fill_color   = QColor(0, 0, 0, 0)     # transparent background
            self._border_color = QColor(0, 0, 0)         # black outline
            self._border_width = 2.0                     # outline offset in px
            self._text_item.setDefaultTextColor(QColor(255, 255, 255))
            cap_font = QFont("Anton", 40)
            cap_font.setCapitalization(QFont.Capitalization.AllUppercase)
            self._font_pt = 40
            self._text_item.setFont(cap_font)
            self._text_item.setVisible(False)            # paint() draws stroke text
            self._reposition_text()

        # Leaving caption: restore text item and defaults
        if prev_style == "caption" and style != "caption":
            self._text_item.setVisible(True)
            self._text_item.setDefaultTextColor(QColor(15, 15, 15))

        self.update()
        self._notify_changed()

    def set_fill_color(self, color: QColor):
        self._fill_color = color
        self.update()
        self._notify_changed()

    def set_border_color(self, color: QColor):
        self._border_color = color
        self.update()
        self._notify_changed()

    def set_border_width(self, w: float):
        self._border_width = w
        self.update()
        self._notify_changed()

    def set_body_rect(self, rect: QRectF):
        self.prepareGeometryChange()
        self._body_rect = QRectF(rect)
        # When the user manually resizes the bubble, try to restore the
        # preferred font size — the new (larger) rect may have room for it.
        cur = QFont(self._text_item.font())
        if 0 < cur.pointSize() < self._font_pt:
            cur.setPointSize(self._font_pt)
            self._text_item.setFont(cur)
        self._reposition_text()
        self._update_handle_positions()
        self.update()

    def set_font(self, font: QFont):
        self._text_item.setFont(font)
        # Remember what the user actually wants so auto-shrink can restore it
        if font.pointSize() > 0:
            self._font_pt = font.pointSize()
        self._reposition_text()
        self.update()
        self._notify_changed()

    def set_text_color(self, color: QColor):
        self._text_item.setDefaultTextColor(color)
        self.update()
        self._notify_changed()

    def set_text(self, text: str):
        self._text_item.setPlainText(text)
        self._reposition_text()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _reposition_text(self):
        r     = self._body_rect
        style = self._style

        # Oval bubbles narrow significantly at top/bottom — an ellipse
        # inscribed in a 220×312 rect is only ~85 px wide at ±144 px from
        # centre, while text set to (width-24) would be 196 px: the top/bottom
        # lines visually overflow the white oval onto the photo background.
        #
        # Fix: for oval use 55 % of width so text always sits inside the
        # ellipse, and cap the height at 1.1× width so the oval never gets
        # so elongated that the maths breaks down.
        if style == "oval":
            tw    = max(40, r.width() * 0.55)
            v_pad = 40
            # At this cap with tw=0.55w the text top lands exactly on the
            # safe inscribed boundary of the ellipse (proven in unit tests).
            cap_h = max(r.height(), r.width() * 1.1)
        else:
            tw    = max(40, r.width() - 24)
            v_pad = 24
            cap_h = max(r.height(), DEFAULT_H * 5)

        self._text_item.setTextWidth(tw)
        opt = self._text_item.document().defaultTextOption()
        opt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_item.document().setDefaultTextOption(opt)

        th       = self._text_item.boundingRect().height()
        needed_h = th + v_pad

        # Font shrink: only fires when text would push bubble past its cap.
        if needed_h > cap_h:
            font = QFont(self._text_item.font())
            while font.pointSize() > 7 and needed_h > cap_h:
                font.setPointSize(font.pointSize() - 1)
                self._text_item.setFont(font)
                self._text_item.setTextWidth(tw)
                th       = self._text_item.boundingRect().height()
                needed_h = th + v_pad

        # Primary behaviour: grow the bubble body to fit the text.
        if r.height() < needed_h:
            self.prepareGeometryChange()
            cx, cy = r.center().x(), r.center().y()
            self._body_rect = QRectF(r.left(), cy - needed_h / 2,
                                     r.width(), needed_h)
            r = self._body_rect
            self._update_handle_positions()

        # Centre text horizontally and vertically within the body rect.
        self._text_item.setPos(
            r.left() + (r.width() - tw) / 2,
            r.top()  + (r.height() - th) / 2,
        )

    def _on_text_contents_changed(self):
        """Called whenever the text document changes (typing or paste).

        Re-runs layout so the bubble grows or shrinks font in real time.
        """
        self._reposition_text()
        self.update()

    def _update_handle_positions(self):
        r  = self._body_rect
        cx, cy = r.center().x(), r.center().y()
        l, t, ri, b = r.left(), r.top(), r.right(), r.bottom()
        for anchor, (x, y) in {
            "TL":(l,t),"TC":(cx,t),"TR":(ri,t),
            "ML":(l,cy),            "MR":(ri,cy),
            "BL":(l,b),"BC":(cx,b),"BR":(ri,b),
        }.items():
            self._handles[anchor].setPos(x, y)

    # ------------------------------------------------------------------
    # QGraphicsItem overrides
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE + 2
        r   = self._body_rect.adjusted(-pad, -pad, pad, pad)
        if self._style in ("text", "scrim", "caption"):
            return r
        tip = self._tail.pos()
        tip_r = QRectF(tip.x()-TAIL_DOT_R, tip.y()-TAIL_DOT_R,
                       TAIL_DOT_R*2, TAIL_DOT_R*2)
        return r.united(tip_r)

    def shape(self) -> QPainterPath:
        if self._style in ("text", "rect", "scrim", "caption"):
            p = QPainterPath()
            p.addRect(self._body_rect)
            return p
        body = self._build_body_path()
        if self._style == "cloud":
            return body
        tail = self._triangle_tail_path(self._tail.pos())
        return body.united(tail)

    def paint(self, painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget | None = None):

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._style == "text":
            # No body — just show selection indicator when selected
            if self.isSelected():
                painter.setPen(QPen(QColor(80, 130, 230), 1.5,
                                    Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(self._body_rect.adjusted(2, 2, -2, -2))
            return

        if self._style == "caption":
            # Stroke text overlay: optional background rect, then outline
            # (8-direction shadow using _border_color + _border_width as offset),
            # then text fill (_text_item.defaultTextColor).
            # _text_item is hidden; everything is painted manually here.
            text = self._text_item.toPlainText()
            if text:
                painter.setFont(self._text_item.font())
                tp    = self._text_item.pos()
                tw    = self._text_item.textWidth()
                th    = self._text_item.boundingRect().height()
                tr    = QRectF(tp.x(), tp.y(), tw, th)
                flags = (int(Qt.AlignmentFlag.AlignCenter) |
                         int(Qt.TextFlag.TextWordWrap))
                # Background rect — only drawn when fill has any opacity
                if self._fill_color.alpha() > 0:
                    pad = 6
                    painter.fillRect(tr.adjusted(-pad, -pad, pad, pad),
                                     self._fill_color)
                # Outline via 8-direction offset; thickness controlled by border_width
                off = max(1, round(self._border_width)) if self._border_width > 0 else 0
                if off > 0:
                    painter.setPen(self._border_color)
                    for ox, oy in [(-off,-off),(0,-off),(off,-off),
                                   (-off,  0),          (off,  0),
                                   (-off, off),(0, off),(off, off)]:
                        painter.drawText(tr.adjusted(ox, oy, ox, oy), flags, text)
                # Text colour fill on top
                painter.setPen(self._text_item.defaultTextColor())
                painter.drawText(tr, flags, text)
            if self.isSelected():
                painter.setPen(QPen(QColor(80, 130, 230), 1.5,
                                    Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(self._body_rect.adjusted(2, 2, -2, -2))
            return

        pen   = QPen(self._border_color, self._border_width,
                     Qt.PenStyle.SolidLine,
                     Qt.PenCapStyle.RoundCap,
                     Qt.PenJoinStyle.RoundJoin)
        brush = QBrush(self._fill_color)
        tip   = self._tail.pos()

        if self._style == "cloud":
            # Cloud body and thought dots drawn separately (dots are distinct circles)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawPath(self._cloud_path(self._body_rect))

            # Thought dots: same fill, same border
            painter.drawPath(self._thought_dots_path(tip))

        elif self._style == "rect":
            # Caption bar — no tail; just fill the rounded rectangle
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawPath(self._build_body_path())

        elif self._style == "scrim":
            # Dark semi-transparent horizontal strip — full-width, no tail
            painter.setBrush(brush)
            painter.setPen(pen if self._border_width > 0
                           else QPen(Qt.PenStyle.NoPen))
            painter.drawPath(self._build_body_path())

        else:
            # Oval / spiky:
            # Unite body + tail into ONE path → border is ONE seamless outline
            body   = self._build_body_path()
            tail   = self._triangle_tail_path(tip)
            merged = body.united(tail)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawPath(merged)

        # Selection dashed rectangle
        if self.isSelected():
            painter.setPen(QPen(QColor(80, 130, 230), 1.5,
                                Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._body_rect)

    # ------------------------------------------------------------------
    # Shape builders
    # ------------------------------------------------------------------

    def _build_body_path(self) -> QPainterPath:
        r = self._body_rect
        path = QPainterPath()
        if self._style == "oval":
            path = self._organic_oval_path(r)
        elif self._style == "rect":
            path.addRoundedRect(r, 16, 16)
        elif self._style == "cloud":
            path = self._cloud_path(r)
        elif self._style == "spiky":
            path = self._spiky_path(r)
        elif self._style == "scrim":
            path.addRect(r)   # sharp corners — Instagram/Snapchat look
        else:
            path.addEllipse(r)
        return path

    def _organic_oval_path(self, r: QRectF) -> QPainterPath:
        """
        Smooth oval using cubic bezier curves — more organic than addEllipse.
        Classic comics/manga speech bubble shape.
        """
        cx, cy = r.center().x(), r.center().y()
        w2, h2 = r.width() / 2, r.height() / 2
        # Bezier "magic number" for approximating an ellipse with cubics
        k = 0.5523

        path = QPainterPath()
        path.moveTo(cx, cy - h2)                               # top centre
        path.cubicTo(cx + w2*k, cy - h2,                      # top-right
                     cx + w2,   cy - h2*k,
                     cx + w2,   cy)
        path.cubicTo(cx + w2,   cy + h2*k,                    # bottom-right
                     cx + w2*k, cy + h2,
                     cx,        cy + h2)
        path.cubicTo(cx - w2*k, cy + h2,                      # bottom-left
                     cx - w2,   cy + h2*k,
                     cx - w2,   cy)
        path.cubicTo(cx - w2,   cy - h2*k,                    # top-left
                     cx - w2*k, cy - h2,
                     cx,        cy - h2)
        path.closeSubpath()
        return path

    def _triangle_tail_path(self, tip: QPointF) -> QPainterPath:
        """
        Triangular wedge from bubble centre to tip.
        When united() with the body, only the exterior part is visible —
        a narrow, sharp manga-style tail emerging from the bubble edge.
        """
        r  = self._body_rect
        cx, cy = r.center().x(), r.center().y()
        dx = tip.x() - cx
        dy = tip.y() - cy
        dist = math.hypot(dx, dy) or 1
        # Perpendicular unit vector
        nx, ny = dy / dist, -dx / dist
        HALF = 13   # half-width at the base; tapers to a point at the tip

        path = QPainterPath()
        path.moveTo(cx + nx * HALF, cy + ny * HALF)
        path.lineTo(tip)
        path.lineTo(cx - nx * HALF, cy - ny * HALF)
        path.closeSubpath()
        return path

    def _cloud_edge_distance(self, tip: QPointF) -> float:
        """
        Binary-search for the distance from the body centre at which the ray
        toward 'tip' exits the cloud body path.  This is direction-aware, so
        the thought dots always start just outside the cloud regardless of
        which way the tail is pointing.
        """
        r  = self._body_rect
        cx, cy = r.center().x(), r.center().y()
        dx = tip.x() - cx
        dy = tip.y() - cy
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist

        cloud = self._cloud_path(r)
        max_search = min(dist, max(r.width(), r.height()))

        lo, hi = 0.0, max_search
        for _ in range(20):          # 20 iterations → sub-pixel precision
            mid = (lo + hi) / 2.0
            if cloud.contains(QPointF(cx + ux * mid, cy + uy * mid)):
                lo = mid             # still inside cloud → go further out
            else:
                hi = mid             # already outside → pull back
        return hi + 6               # 6 px gap so the first dot is clearly outside

    def _thought_dots_path(self, tip: QPointF) -> QPainterPath:
        """
        Thought-bubble dot chain from the cloud edge toward the tip.

        Dots scale in both size and spacing with the available tail length,
        so a short tail shows 2 small dots and a long tail shows up to 5
        larger ones — the tail visually "grows" as the user drags the red dot.
        """
        r  = self._body_rect
        cx, cy = r.center().x(), r.center().y()
        dx = tip.x() - cx
        dy = tip.y() - cy
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist

        edge      = self._cloud_edge_distance(tip)
        available = max(0.0, dist - edge - 8)   # usable space; 8 px margin before tip

        if available < 10:
            return QPainterPath()   # tail too short for any dots

        # Scale factor: 1.0 at 60 px of tail, up to 2.2 at ≥ 240 px
        scale = min(2.2, max(0.7, available / 60.0))

        # Dot specs: (fraction_of_available_length, base_radius)
        # Fractions spread dots evenly; radii shrink toward the tip
        dot_specs = [(0.12, 11), (0.38, 8), (0.60, 6)]
        if available > 80:
            dot_specs.append((0.75, 4))
        if available > 140:
            dot_specs.append((0.87, 3))

        path = QPainterPath()
        for frac, base_r in dot_specs:
            rad = max(2, int(base_r * scale))
            d   = edge + frac * available
            if d + rad > dist - 5:      # don't overlap tip
                break
            path.addEllipse(QPointF(cx + ux * d, cy + uy * d), rad, rad)
        return path

    def _cloud_path(self, r: QRectF) -> QPainterPath:
        """
        Thought-cloud: 9 circles united into ONE path so the border traces the
        outer silhouette only — no internal rings (Audi logo effect).
        """
        w, h = r.width(), r.height()
        # (fraction-x, fraction-y, radius-fraction-of-min-dimension)
        bumps = [
            (0.14, 0.62, 0.22),
            (0.28, 0.42, 0.28),
            (0.48, 0.34, 0.31),
            (0.68, 0.42, 0.28),
            (0.84, 0.62, 0.22),
            (0.80, 0.78, 0.23),
            (0.62, 0.84, 0.26),
            (0.38, 0.84, 0.26),
            (0.18, 0.78, 0.21),
        ]
        # Start with the first bump and progressively unite the rest.
        # united() merges all circles into a single outline with no inner borders.
        path = QPainterPath()
        for fx, fy, fr in bumps:
            bx   = r.left() + fx * w
            by   = r.top()  + fy * h
            brad = fr * min(w, h)
            bump = QPainterPath()
            bump.addEllipse(QPointF(bx, by), brad, brad)
            path = path.united(bump)
        return path

    def _spiky_path(self, r: QRectF) -> QPainterPath:
        """
        Dramatic starburst / shout bubble with 18 spikes of varying height.
        """
        cx, cy = r.center().x(), r.center().y()
        rx, ry = r.width() / 2, r.height() / 2
        spikes = 18
        path   = QPainterPath()

        for i in range(spikes * 2):
            angle = math.pi * i / spikes - math.pi / 2
            if i % 2 == 0:
                # Spike tip — vary outer radius for an organic, energetic look
                variation = 1.0 + 0.22 * math.sin(i * 1.9 + 0.8)
                px = cx + math.cos(angle) * rx * variation
                py = cy + math.sin(angle) * ry * variation
            else:
                # Valley between spikes
                px = cx + math.cos(angle) * rx * 0.64
                py = cy + math.sin(angle) * ry * 0.64
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        path.closeSubpath()
        return path

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Clamp so the bubble body cannot be dragged outside the canvas.
            scene = self.scene()
            if scene:
                sr = scene.sceneRect()
                r  = self._body_rect
                # r edges are in local coords; item pos is the local origin in scene.
                x = max(sr.left() - r.left(),
                        min(value.x(), sr.right()  - r.right()))
                y = max(sr.top()  - r.top(),
                        min(value.y(), sr.bottom() - r.bottom()))
                return QPointF(x, y)

        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            selected = bool(value)
            for h in self._handles.values():
                h.setVisible(selected)
            self._tail.setVisible(
                selected and self._style not in ("text", "rect", "scrim", "caption"))
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Snapshot text before editing so we can push an undo command later
            self._text_before_edit = self.get_text()
            self._is_editing = True
            if self._style == "caption":
                # Temporarily show text item so the user can see what they type
                self._text_item.setVisible(True)
            self._text_item.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction)
            self._text_item.setFocus()
            cursor = self._text_item.textCursor()
            cursor.select(cursor.SelectionType.Document)
            self._text_item.setTextCursor(cursor)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        self._stop_editing()
        # Record position before a potential drag so MoveBubbleCommand can
        # capture the start state.
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            old = self._drag_start_pos
            new = self.pos()
            # Only push a move command if the bubble actually moved
            if old is not None and (old - new).manhattanLength() > 1:
                stack = self._undo_stack()
                if stack:
                    from undo_commands import MoveBubbleCommand
                    stack.push(MoveBubbleCommand(self, old, new))
            self._drag_start_pos = None

    def _stop_editing(self):
        """Stop text editing; push TextChangeCommand if text was modified."""
        before = self._text_before_edit
        self._is_editing = False
        self._text_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction)
        self._text_item.clearFocus()
        if self._style == "caption":
            self._text_item.setVisible(False)   # paint() takes over again
        if before is not None:
            after = self.get_text()
            if after != before:
                stack = self._undo_stack()
                if stack:
                    from undo_commands import TextChangeCommand
                    stack.push(TextChangeCommand(self, before, after))
            self._text_before_edit = None

    def _undo_stack(self):
        """Return the scene's QUndoStack if available, else None."""
        scene = self.scene()
        return getattr(scene, 'undo_stack', None) if scene else None

    def _snap_to_edge(self, edge: str):
        """Snap this rect bubble so it spans the full photo width and sits
        flush against the top or bottom edge of the image.

        This is the "caption bar" behaviour described in the spec (§8).
        """
        scene = self.scene()
        if not scene or not hasattr(scene, 'has_photo') or not scene.has_photo():
            return
        sr   = scene.sceneRect()
        w    = sr.width()
        h    = self._body_rect.height()   # keep current height

        # body_rect is in local coordinates, centred on the item's pos().
        new_rect = QRectF(-w / 2, -h / 2, w, h)
        self.set_body_rect(new_rect)

        if edge == "top":
            self.setPos(sr.center().x(), sr.top() + h / 2)
        else:
            self.setPos(sr.center().x(), sr.bottom() - h / 2)

    def _snap_to_scrim(self):
        """Expand to full scene width, keeping current vertical position."""
        scene = self.scene()
        if not scene or not hasattr(scene, 'has_photo') or not scene.has_photo():
            return
        sr = scene.sceneRect()
        w  = sr.width()
        h  = self._body_rect.height()
        self.set_body_rect(QRectF(-w / 2, -h / 2, w, h))
        self.setPos(sr.center().x(), self.pos().y())

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        menu = QMenu()
        act_del   = menu.addAction("Delete")
        act_dup   = menu.addAction("Duplicate")
        menu.addSeparator()
        menu.addSection("Change Style")
        act_oval    = menu.addAction("Oval  — speech bubble")
        act_cloud   = menu.addAction("Cloud — thought bubble")
        act_rect    = menu.addAction("Rectangle — caption bar")
        act_spiky   = menu.addAction("Spiky — shout / explosion")
        act_text    = menu.addAction("Text only — no bubble")
        act_scrim   = menu.addAction("Scrim — dark text strip")
        act_caption = menu.addAction("Caption — stroke text overlay")
        menu.addSeparator()
        act_front = menu.addAction("Bring to Front")
        act_back  = menu.addAction("Send to Back")

        # Snap options per style
        act_snap_top = act_snap_bot = act_snap_full = None
        if self._style in ("rect", "scrim"):
            menu.addSeparator()
            act_snap_top  = menu.addAction("Snap to Top Edge")
            act_snap_bot  = menu.addAction("Snap to Bottom Edge")
        if self._style == "scrim":
            act_snap_full = menu.addAction("Snap to Full Width")

        # Mark current style
        for act, s in [(act_oval,"oval"),(act_cloud,"cloud"),
                       (act_rect,"rect"),(act_spiky,"spiky"),
                       (act_text,"text"),(act_scrim,"scrim"),
                       (act_caption,"caption")]:
            act.setCheckable(True)
            act.setChecked(self._style == s)

        chosen = menu.exec(event.screenPos())
        if   chosen == act_del:     self._delete()
        elif chosen == act_dup:     self._duplicate()
        elif chosen == act_oval:    self.set_style("oval")
        elif chosen == act_cloud:   self.set_style("cloud")
        elif chosen == act_rect:    self.set_style("rect")
        elif chosen == act_spiky:   self.set_style("spiky")
        elif chosen == act_text:    self.set_style("text")
        elif chosen == act_scrim:   self.set_style("scrim")
        elif chosen == act_caption: self.set_style("caption")
        elif chosen == act_front: self.setZValue(self.zValue() + 1)
        elif chosen == act_back:  self.setZValue(max(0, self.zValue() - 1))
        elif act_snap_top  and chosen == act_snap_top:  self._snap_to_edge("top")
        elif act_snap_bot  and chosen == act_snap_bot:  self._snap_to_edge("bottom")
        elif act_snap_full and chosen == act_snap_full: self._snap_to_scrim()

    def _delete(self):
        if not self.scene():
            return
        stack = self._undo_stack()
        if stack:
            from undo_commands import DeleteBubbleCommand
            stack.push(DeleteBubbleCommand(self.scene(), self))
        else:
            self.scene().removeItem(self)

    def _duplicate(self):
        if not self.scene():
            return
        nb = BubbleItem(self.scenePos().x() + 25,
                        self.scenePos().y() + 25,
                        style=self._style)
        nb.set_text(self.get_text())
        nb._fill_color   = QColor(self._fill_color)
        nb._border_color = QColor(self._border_color)
        nb._border_width = self._border_width
        nb.set_font(self.get_font())
        # Caption needs explicit post-init state (not applied by __init__)
        if self._style == "caption":
            nb._text_item.setDefaultTextColor(
                QColor(self._text_item.defaultTextColor()))
            nb._text_item.setVisible(False)
        stack = self._undo_stack()
        if stack:
            from undo_commands import AddBubbleCommand
            stack.push(AddBubbleCommand(self.scene(), nb))
        else:
            self.scene().addItem(nb)
