"""
media_item.py — MediaItem: resizable background media item (photo or video frame).

Click to select → 4 corner resize handles appear.
Drag a corner to resize.  Drag the body to move.
Both resize and move are fully undoable (Ctrl+Z / Ctrl+Y).
"""

from PyQt6.QtWidgets import (
    QGraphicsObject, QGraphicsRectItem, QGraphicsItem,
    QGraphicsSceneMouseEvent, QGraphicsSceneContextMenuEvent,
    QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPixmap, QPainter, QPen, QBrush, QColor, QCursor,
)

HANDLE_SIZE = 10
MIN_DISPLAY = 40.0


# ---------------------------------------------------------------------------
# MediaResizeHandle
# ---------------------------------------------------------------------------

class MediaResizeHandle(QGraphicsRectItem):
    """One corner resize handle on a MediaItem."""

    CURSORS = {
        "TL": Qt.CursorShape.SizeFDiagCursor,
        "TR": Qt.CursorShape.SizeBDiagCursor,
        "BL": Qt.CursorShape.SizeBDiagCursor,
        "BR": Qt.CursorShape.SizeFDiagCursor,
    }

    def __init__(self, corner: str, parent: "MediaItem"):
        s = HANDLE_SIZE
        super().__init__(-s / 2, -s / 2, s, s, parent)
        self._corner      = corner
        self._media       = parent
        self._dragging    = False
        self._start_mouse = QPointF()
        self._start_w     = 0.0
        self._start_h     = 0.0
        self._start_pos   = QPointF()

        self.setBrush(QBrush(QColor(59, 130, 246)))
        self.setPen(QPen(QColor(255, 255, 255), 1.5))
        self.setZValue(5)
        self.setCursor(QCursor(self.CURSORS[corner]))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging        = True
            self._media._resizing = True
            self._start_mouse     = event.scenePos()
            self._start_w         = self._media.display_w
            self._start_h         = self._media.display_h
            self._start_pos       = self._media.pos()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        delta = event.scenePos() - self._start_mouse
        c = self._corner

        # Step 1: compute unconstrained new size from drag delta
        new_w = self._start_w
        new_h = self._start_h
        if "R" in c:
            new_w = max(MIN_DISPLAY, self._start_w + delta.x())
        if "L" in c:
            new_w = max(MIN_DISPLAY, self._start_w - delta.x())
        if "B" in c:
            new_h = max(MIN_DISPLAY, self._start_h + delta.y())
        if "T" in c:
            new_h = max(MIN_DISPLAY, self._start_h - delta.y())

        # Step 2: constrain to aspect ratio when Shift held or lock is active
        shift = bool(QApplication.keyboardModifiers()
                     & Qt.KeyboardModifier.ShiftModifier)
        if (shift or self._media._lock_ratio) and self._start_h > 0:
            aspect = self._start_w / self._start_h
            if abs(delta.x()) >= abs(delta.y()):
                new_h = max(MIN_DISPLAY, new_w / aspect)
            else:
                new_w = max(MIN_DISPLAY, new_h * aspect)

        # Step 3: adjust top-left position for L/T anchored corners
        new_x = self._start_pos.x()
        new_y = self._start_pos.y()
        if "L" in c:
            new_x = self._start_pos.x() + (self._start_w - new_w)
        if "T" in c:
            new_y = self._start_pos.y() + (self._start_h - new_h)

        self._media.set_display_size(new_w, new_h)
        self._media.setPos(new_x, new_y)

        # In dual mode snap right panel live — position only, NO sceneRect change.
        # Changing sceneRect on every mouse move causes Qt to auto-scroll the
        # viewport, which makes bubbles "disappear" from the visible area.
        sc = self._media.scene()
        if sc and hasattr(sc, "_snap_right_to_left"):
            sc._snap_right_to_left()

        event.accept()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging        = False
            self._media._resizing = False
            sc      = self.scene()
            new_pos = self._media.pos()
            new_w   = self._media.display_w
            new_h   = self._media.display_h

            size_changed = (abs(new_w - self._start_w) > 0.5
                            or abs(new_h - self._start_h) > 0.5)
            pos_changed  = (new_pos - self._start_pos).manhattanLength() > 0.5

            if (size_changed or pos_changed) and sc and hasattr(sc, 'undo_stack'):
                from undo_commands import ResizeMediaCommand
                sc.undo_stack.push(ResizeMediaCommand(
                    sc, self._media,
                    self._start_pos, self._start_w, self._start_h,
                    new_pos, new_w, new_h,
                ))
                # push() immediately calls redo() which calls fit_scene_to_media()
                event.accept()
                return

            # No change, or no undo stack — still refresh scene rect
            if sc and hasattr(sc, "fit_scene_to_media"):
                sc.fit_scene_to_media()

        event.accept()


# ---------------------------------------------------------------------------
# MediaItem
# ---------------------------------------------------------------------------

class MediaItem(QGraphicsObject):
    """
    Background media (photo or video frame) with 4 corner resize handles.

    The pixmap is drawn stretched to (display_w × display_h).
    For video playback: call set_pixmap() each frame — display size stays fixed.

    Intentionally does NOT use ItemSendsGeometryChanges: that flag causes
    fit_scene_to_media() → setSceneRect() to fire on every drag pixel, which
    triggers Qt's scrollbar recalculation and auto-scrolls the viewport,
    making speech bubbles appear to "vanish" during resize.
    Instead, scene updates happen only on mouse release (via undo commands).
    """

    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self._pixmap    = pixmap
        self._display_w = float(pixmap.width())
        self._display_h = float(pixmap.height())
        self._native_w  = float(pixmap.width())
        self._native_h  = float(pixmap.height())

        # Drag-state
        self._resizing:       bool           = False   # True while handle active
        self._drag_start_pos: QPointF | None = None
        self._lock_ratio:     bool           = True    # constrain resize to aspect ratio

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        # NOTE: ItemSendsGeometryChanges deliberately omitted — see class docstring
        self.setZValue(-1)

        self._handles = {
            c: MediaResizeHandle(c, self) for c in ("TL", "TR", "BL", "BR")
        }
        self._update_handle_positions()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def display_w(self) -> float:
        return self._display_w

    @property
    def display_h(self) -> float:
        return self._display_h

    def pixmap(self) -> QPixmap:
        return self._pixmap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap):
        """Replace pixmap (next video frame). Display size unchanged."""
        self._pixmap = pixmap
        self.update()

    def set_display_size(self, w: float, h: float):
        self.prepareGeometryChange()
        self._display_w = max(MIN_DISPLAY, float(w))
        self._display_h = max(MIN_DISPLAY, float(h))
        self._update_handle_positions()
        self.update()

    def restore_native_size(self):
        """Reset to original pixel dimensions and position."""
        self.prepareGeometryChange()
        self._display_w = self._native_w
        self._display_h = self._native_h
        self._update_handle_positions()
        self.update()
        self.setPos(0, 0)

    # ------------------------------------------------------------------
    # QGraphicsItem overrides
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._display_w, self._display_h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(
            QRectF(0, 0, self._display_w, self._display_h),
            self._pixmap,
            QRectF(self._pixmap.rect()),
        )
        if self.isSelected():
            pen = QPen(QColor(59, 130, 246), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(1, 1, self._display_w - 2, self._display_h - 2))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            for h in self._handles.values():
                h.setVisible(bool(value))
        return super().itemChange(change, value)

    # ------------------------------------------------------------------
    # Mouse events — move with undo support
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._resizing:
            self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)   # Qt moves the item
        # Live snap in dual mode — position only, no sceneRect update
        sc = self.scene()
        if sc and hasattr(sc, "_snap_right_to_left"):
            sc._snap_right_to_left()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and not self._resizing:
            old = self._drag_start_pos
            new = self.pos()
            self._drag_start_pos = None

            if old is not None and (old - new).manhattanLength() > 1:
                sc = self.scene()
                if sc and hasattr(sc, 'undo_stack'):
                    from undo_commands import MoveMediaCommand
                    sc.undo_stack.push(MoveMediaCommand(sc, self, old, new))
                    # push() calls redo() immediately → fit_scene_to_media()
                    return
                elif sc and hasattr(sc, 'fit_scene_to_media'):
                    sc.fit_scene_to_media()
            else:
                # Click without move — still refresh scene rect
                sc = self.scene()
                if sc and hasattr(sc, 'fit_scene_to_media'):
                    sc.fit_scene_to_media()

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        menu = QMenu()
        act_lock = menu.addAction("Lock Aspect Ratio")
        act_lock.setCheckable(True)
        act_lock.setChecked(self._lock_ratio)
        act_lock.setToolTip("Hold Shift while dragging a corner to lock ratio temporarily")
        chosen = menu.exec(event.screenPos())
        if chosen == act_lock:
            self._lock_ratio = not self._lock_ratio
        event.accept()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_handle_positions(self):
        w, h = self._display_w, self._display_h
        for corner, handle in self._handles.items():
            x = w if "R" in corner else 0.0
            y = h if "B" in corner else 0.0
            handle.setPos(x, y)
