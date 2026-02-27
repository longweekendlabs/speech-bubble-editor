"""
canvas.py — Photo/video canvas using QGraphicsScene and QGraphicsView.

Supports both images (QPixmap) and videos (VideoPlayer frame-by-frame).
Dual mode shows two media items side by side.
ZoomBar lives below the view.
"""

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsTextItem,
    QWidget, QHBoxLayout, QLabel, QPushButton, QSlider,
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QUndoStack, QFont, QPen,
    QFontMetrics, QTransform, QBrush,
)

from video_player import VideoPlayer, VIDEO_EXTENSIONS
from media_item import MediaItem

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')
ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

_BAR_FRACTION  = 0.065  # caption bar height as fraction of photo height
_DUAL_GAP      = 4      # pixel gap between left and right media
_ZOOM_STEP_IN  = 1.25
_ZOOM_STEP_OUT = 0.80
_MIN_SCALE     = 0.05
_MAX_SCALE     = 10.0


# ---------------------------------------------------------------------------
# MemeBarItem
# ---------------------------------------------------------------------------

class MemeBarItem(QGraphicsItem):
    """Full-width black caption bar (unchanged from v1)."""

    def __init__(self, x, y, width, height, default_text):
        super().__init__()
        self._rect    = QRectF(x, y, width, height)
        self._editing = False

        self._font = QFont("Anton")
        self._font.setPixelSize(max(14, int(height * 0.62)))
        self._font.setCapitalization(QFont.Capitalization.AllUppercase)

        edit_font = QFont(self._font)
        edit_font.setPixelSize(max(11, int(height * 0.52)))
        self._text_item = QGraphicsTextItem(self)
        self._text_item.setPlainText(default_text)
        self._text_item.setDefaultTextColor(QColor(255, 255, 255))
        self._text_item.setFont(edit_font)
        self._text_item.setTextWidth(width - 32)
        self._text_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction)
        self._text_item.setVisible(False)
        self._center_text_item()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setZValue(0.5)

    @property
    def is_editing(self):
        return self._editing

    def text(self):
        return self._text_item.toPlainText()

    def start_editing(self):
        self._editing = True
        self._center_text_item()
        self._text_item.setVisible(True)
        self._text_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction)
        self._text_item.setFocus()
        cur = self._text_item.textCursor()
        cur.select(cur.SelectionType.Document)
        self._text_item.setTextCursor(cur)
        self.update()

    def stop_editing(self):
        if not self._editing:
            return
        self._editing = False
        self._text_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction)
        self._text_item.clearFocus()
        self._text_item.setVisible(False)
        self.update()

    def boundingRect(self):
        return QRectF(self._rect)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark scrim — Instagram/Snapchat style
        painter.fillRect(self._rect, QColor(0, 0, 0, 205))

        if self._editing:
            return

        text      = (self.text() or " ").upper()
        # Tighter vertical padding so text fills the slim bar naturally
        text_rect = self._rect.adjusted(20, 4, -20, -4)
        flags     = (int(Qt.AlignmentFlag.AlignHCenter) |
                     int(Qt.AlignmentFlag.AlignVCenter) |
                     int(Qt.TextFlag.TextWordWrap))

        font   = QFont(self._font)
        min_px = max(10, font.pixelSize() // 4)
        while font.pixelSize() > min_px:
            fm = QFontMetrics(font)
            if fm.boundingRect(text_rect.toRect(), flags, text).height() \
                    <= text_rect.height():
                break
            font.setPixelSize(font.pixelSize() - 2)

        painter.setFont(font)

        # Subtle drop shadow (1 px offset) instead of heavy 8-direction stroke
        painter.setPen(QPen(QColor(0, 0, 0, 160)))
        painter.drawText(text_rect.adjusted(1, 1, 1, 1), flags, text)

        # White text on top
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(text_rect, flags, text)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_editing()
            event.accept()
        else:
            event.ignore()

    def _center_text_item(self):
        th = self._text_item.boundingRect().height()
        self._text_item.setPos(
            self._rect.left() + 10,
            self._rect.center().y() - th / 2,
        )


# ---------------------------------------------------------------------------
# RightMediaPlaceholder
# ---------------------------------------------------------------------------

class RightMediaPlaceholder(QGraphicsItem):
    """Drop-zone shown on the right in dual mode before media is loaded."""

    def __init__(self, x, y, w, h):
        super().__init__()
        self._rect = QRectF(x, y, w, h)
        self.setZValue(-0.9)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)

    def boundingRect(self):
        return QRectF(self._rect)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self._rect, QColor(55, 55, 55))

        pen = QPen(QColor(160, 160, 160))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self._rect.adjusted(12, 12, -12, -12))

        font = QFont()
        font.setPixelSize(max(14, int(self._rect.height() * 0.035)))
        painter.setFont(font)
        painter.setPen(QPen(QColor(190, 190, 190)))
        painter.drawText(
            self._rect,
            int(Qt.AlignmentFlag.AlignHCenter) |
            int(Qt.AlignmentFlag.AlignVCenter) |
            int(Qt.TextFlag.TextWordWrap),
            "Double-click to open photo or video\n"
            "or drop a file here",
        )

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            sc = self.scene()
            if sc is not None:
                sc.open_right_media_requested.emit()
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# PhotoScene
# ---------------------------------------------------------------------------

class PhotoScene(QGraphicsScene):
    """
    Scene holding photo/video background(s) and bubble items.

    Signals:
        double_clicked_on_canvas(float, float)  — add a bubble here
        bubble_changed(object)                  — bubble appearance changed
        open_right_media_requested()            — user wants to pick right media
    """

    double_clicked_on_canvas   = pyqtSignal(float, float)
    bubble_changed             = pyqtSignal(object)
    open_right_media_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._photo_item:        MediaItem | None = None
        self._photo_item_right:  MediaItem | None = None
        self._right_placeholder: RightMediaPlaceholder | None = None
        self._video_player:       VideoPlayer | None = None
        self._video_player_right: VideoPlayer | None = None

        self.undo_stack  = QUndoStack(self)
        self._meme_top:  MemeBarItem | None = None
        self._meme_bot:  MemeBarItem | None = None
        self._dual_mode  = False
        self._fitting    = False   # re-entrancy guard for fit_scene_to_media

    # ------------------------------------------------------------------
    # Media loading
    # ------------------------------------------------------------------

    def load_photo(self, file_path: str) -> bool:
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            return False
        self._reset_all()
        self._photo_item = MediaItem(pixmap)
        self._photo_item.setPos(0, 0)
        self.addItem(self._photo_item)
        self.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
        return True

    def load_video(self, file_path: str) -> bool:
        player = VideoPlayer()
        if not player.load(file_path):
            return False
        first = player.get_frame_pixmap(0)
        if first is None:
            player.release()
            return False
        self._reset_all()
        self._video_player = player
        self._photo_item = MediaItem(first)
        self._photo_item.setPos(0, 0)
        self.addItem(self._photo_item)
        self.setSceneRect(QRectF(0, 0, float(player.width), float(player.height)))
        return True

    def _reset_all(self):
        """Release all media and reset modes."""
        self._remove_meme_bars()
        self._clear_dual_state()
        if self._video_player is not None:
            self._video_player.release()
            self._video_player = None
        if self._photo_item is not None:
            self.removeItem(self._photo_item)
            self._photo_item = None

    # ------------------------------------------------------------------
    # Video frame update (called from MainWindow when scrubber moves)
    # ------------------------------------------------------------------

    def update_frame(self, frame_idx: int):
        """Refresh the background pixmap(s) to the given video frame."""
        if self._video_player is not None and self._photo_item is not None:
            px = self._video_player.get_frame_pixmap(frame_idx)
            if px is not None:
                self._photo_item.set_pixmap(px)

        if self._dual_mode and self._video_player_right is not None \
                and self._photo_item_right is not None:
            right_idx = min(frame_idx,
                            self._video_player_right.frame_count - 1)
            px = self._video_player_right.get_frame_pixmap(right_idx)
            if px is not None:
                self._photo_item_right.set_pixmap(px)

    def update_right_frame(self, frame_idx: int):
        """Update only the right media frame (for independent right-player scrubbing)."""
        if self._dual_mode and self._video_player_right is not None \
                and self._photo_item_right is not None:
            right_idx = min(frame_idx,
                            self._video_player_right.frame_count - 1)
            px = self._video_player_right.get_frame_pixmap(right_idx)
            if px is not None:
                self._photo_item_right.set_pixmap(px)

    # ------------------------------------------------------------------
    # Meme mode
    # ------------------------------------------------------------------

    def enable_meme_mode(self):
        if self._meme_top is not None or not self.has_photo():
            return
        px    = self._photo_item.pos().x()
        py    = self._photo_item.pos().y()
        # Use full canvas width so bars span both panels in dual mode
        w     = self.sceneRect().width()
        ph    = self._photo_item.display_h
        bar_h = ph * _BAR_FRACTION
        top_y = py - bar_h
        bot_y = py + ph
        self.setSceneRect(QRectF(px, top_y, w, ph + 2 * bar_h))
        self._meme_top = MemeBarItem(px, top_y, w, bar_h, "TOP TEXT")
        self._meme_bot = MemeBarItem(px, bot_y, w, bar_h, "BOTTOM TEXT")
        self.addItem(self._meme_top)
        self.addItem(self._meme_bot)

    def _update_meme_bar_layout(self):
        """Resize meme bars to span the current canvas width.

        Call this after any operation that changes the canvas dimensions
        (fit_scene_to_media, _install_right_media, disable_dual_mode).
        """
        if self._meme_top is None or not self.has_photo():
            return
        sr    = self.sceneRect()
        w     = sr.width()
        px    = self._photo_item.pos().x()
        py    = self._photo_item.pos().y()
        ph    = self._photo_item.display_h
        bar_h = max(1.0, ph * _BAR_FRACTION)
        top_y = py - bar_h
        bot_y = py + ph
        # Expand scene rect vertically to include bars
        self.setSceneRect(QRectF(sr.x(), top_y, w, ph + 2 * bar_h))
        # Update each bar's geometry in place (preserves editing state and text)
        for bar, y in ((self._meme_top, top_y), (self._meme_bot, bot_y)):
            bar.prepareGeometryChange()   # must precede rect change so Qt clears old area
            bar._rect = QRectF(sr.x(), y, w, bar_h)
            bar._text_item.setTextWidth(w - 32)
            bar._center_text_item()
            bar.update()

    def disable_meme_mode(self):
        self._remove_meme_bars()
        if self.has_photo():
            self.fit_scene_to_media()

    def _remove_meme_bars(self):
        for bar in (self._meme_top, self._meme_bot):
            if bar is not None:
                self.removeItem(bar)
        self._meme_top = None
        self._meme_bot = None

    def is_meme_mode(self): return self._meme_top is not None
    def toggle_meme_mode(self):
        self.disable_meme_mode() if self.is_meme_mode() else self.enable_meme_mode()

    # ------------------------------------------------------------------
    # Dual mode
    # ------------------------------------------------------------------

    def enable_dual_mode(self):
        if self._dual_mode or not self.has_photo():
            return
        self._dual_mode = True
        lx = self._photo_item.pos().x()
        ly = self._photo_item.pos().y()
        lw = self._left_width()
        lh = self._left_height()
        snap_x = lx + lw + _DUAL_GAP
        self.setSceneRect(QRectF(lx, ly, lw * 2 + _DUAL_GAP, lh))
        self._right_placeholder = RightMediaPlaceholder(
            snap_x, ly, lw, lh)
        self.addItem(self._right_placeholder)
        # Expand meme bars to span both panels if meme mode is active
        self._update_meme_bar_layout()

    def disable_dual_mode(self):
        if not self._dual_mode:
            return
        self._clear_dual_state()
        if self.has_photo():
            self.fit_scene_to_media()
            # Shrink meme bars back to single-panel width if meme mode is active
            self._update_meme_bar_layout()

    def _clear_dual_state(self):
        self._dual_mode = False
        if self._right_placeholder is not None:
            self.removeItem(self._right_placeholder)
            self._right_placeholder = None
        if self._photo_item_right is not None:
            self.removeItem(self._photo_item_right)
            self._photo_item_right = None
        if self._video_player_right is not None:
            self._video_player_right.release()
            self._video_player_right = None

    def is_dual_mode(self): return self._dual_mode
    def toggle_dual_mode(self):
        self.disable_dual_mode() if self._dual_mode else self.enable_dual_mode()

    def load_right_photo(self, file_path: str) -> bool:
        if not self._dual_mode or not self.has_photo():
            return False
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            return False
        return self._install_right_media(pixmap)

    def load_right_video(self, file_path: str) -> bool:
        if not self._dual_mode or not self.has_photo():
            return False
        player = VideoPlayer()
        if not player.load(file_path):
            return False
        first = player.get_frame_pixmap(0)
        if first is None:
            player.release()
            return False
        if self._video_player_right is not None:
            self._video_player_right.release()
        self._video_player_right = player
        return self._install_right_media(first)

    def _install_right_media(self, pixmap: QPixmap) -> bool:
        """
        Place the right media, scaled so its HEIGHT matches the left media height.
        This avoids letterboxing/pillarboxing — both sides share the same height.
        """
        if self._right_placeholder is not None:
            self.removeItem(self._right_placeholder)
            self._right_placeholder = None
        if self._photo_item_right is not None:
            self.removeItem(self._photo_item_right)
            self._photo_item_right = None

        lx = self._photo_item.pos().x()
        ly = self._photo_item.pos().y()
        lw = self._left_width()
        lh = self._left_height()

        # Scale right media to match left HEIGHT (no black bars)
        native_h = float(pixmap.height()) or 1.0
        scale    = lh / native_h
        right_w  = max(1.0, float(pixmap.width()) * scale)
        right_h  = lh

        media = MediaItem(pixmap)
        media.set_display_size(right_w, right_h)
        media.setPos(lx + lw + _DUAL_GAP, ly)
        self._photo_item_right = media
        self.addItem(self._photo_item_right)

        # Expand scene to fit both sides
        self.setSceneRect(QRectF(lx, ly, lw + _DUAL_GAP + right_w, lh))
        # Expand meme bars if active
        self._update_meme_bar_layout()
        return True

    # ------------------------------------------------------------------
    # Helpers / properties
    # ------------------------------------------------------------------

    def _left_width(self) -> float:
        return self._photo_item.display_w if self._photo_item else 0.0

    def _left_height(self) -> float:
        return self._photo_item.display_h if self._photo_item else 0.0

    def _snap_right_to_left(self):
        """
        Move the right panel (media item or placeholder) flush against the
        left without changing the sceneRect.  Safe to call every mouse-move
        during a drag because it never triggers viewport scroll or BSP-tree
        rebuilds.
        """
        if self._fitting or not self._dual_mode or not self._photo_item:
            return
        if not self._photo_item_right and not self._right_placeholder:
            return
        self._fitting = True
        try:
            snap_x = (self._photo_item.pos().x()
                      + self._photo_item.display_w + _DUAL_GAP)
            snap_y = self._photo_item.pos().y()
            if self._photo_item_right:
                self._photo_item_right.setPos(snap_x, snap_y)
            else:
                ph = self._right_placeholder
                pw = ph._rect.width()
                pht = ph._rect.height()
                ph.prepareGeometryChange()
                ph._rect = QRectF(snap_x, snap_y, pw, pht)
                ph.update()
        finally:
            self._fitting = False

    def fit_scene_to_media(self):
        """Recompute scene rect to fit all media items tightly.

        In dual mode the right item is always snapped to the left item's
        right edge so no gap can appear after resizing or moving.
        """
        if not self._photo_item or self._fitting:
            return
        self._fitting = True
        try:
            lx = self._photo_item.pos().x()
            ly = self._photo_item.pos().y()
            lw = self._photo_item.display_w
            lh = self._photo_item.display_h

            if self._dual_mode and self._photo_item_right:
                # Snap right item flush to the left item (no gap drift)
                snap_x = lx + lw + _DUAL_GAP
                self._photo_item_right.setPos(snap_x, ly)

                rw = self._photo_item_right.display_w
                rh = self._photo_item_right.display_h
                total_w = snap_x + rw
                total_h = max(lh, rh)
            elif self._dual_mode and self._right_placeholder:
                # No right media yet — keep placeholder snapped to left image
                snap_x = lx + lw + _DUAL_GAP
                ph = self._right_placeholder
                pw = ph._rect.width()
                ph.prepareGeometryChange()
                ph._rect = QRectF(snap_x, ly, pw, lh)
                ph.update()
                total_w = snap_x + pw
                total_h = lh
            else:
                total_w = lx + lw
                total_h = ly + lh

            self.setSceneRect(QRectF(lx, ly, total_w - lx, total_h - ly))
            # Keep meme bars spanning the full canvas if meme mode is active
            self._update_meme_bar_layout()
        finally:
            self._fitting = False

    @property
    def photo_pixmap(self):
        return self._photo_item.pixmap() if self._photo_item else None

    @property
    def video_player(self) -> VideoPlayer | None:
        return self._video_player

    @property
    def video_player_right(self) -> VideoPlayer | None:
        return self._video_player_right

    def has_photo(self) -> bool:
        return self._photo_item is not None

    def has_video(self) -> bool:
        return self._video_player is not None

    def has_right_media(self) -> bool:
        return self._photo_item_right is not None

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        pos = event.scenePos()
        for bar in (self._meme_top, self._meme_bot):
            if bar and bar.is_editing:
                if not bar.boundingRect().contains(pos):
                    bar.stop_editing()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            t = self.views()[0].transform() if self.views() else QTransform()
            item = self.itemAt(event.scenePos(), t)
            # MediaItem and its resize handle children are background
            is_bg = (item is None or
                     isinstance(item, MediaItem) or
                     (item is not None and isinstance(item.parentItem(), MediaItem)))
            # Only add bubbles when media is actually loaded
            if is_bg and self.has_photo():
                self.double_clicked_on_canvas.emit(
                    event.scenePos().x(), event.scenePos().y())
                return
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
# PhotoView
# ---------------------------------------------------------------------------

class PhotoView(QGraphicsView):
    """
    View that renders the PhotoScene with zoom, pan, and drop support.
    Accepts both image and video file drops.
    """

    open_media_requested = pyqtSignal()   # emitted when user clicks empty canvas
    photo_dropped        = pyqtSignal(str)
    right_media_dropped  = pyqtSignal(str)
    zoom_changed         = pyqtSignal(int)

    def __init__(self, scene: PhotoScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QColor(45, 45, 45))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setAcceptDrops(True)
        self._photo_scene   = scene
        self._fit_to_window = True
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)

    def fit_photo(self):
        if self._photo_scene.has_photo():
            self.fitInView(self._photo_scene.sceneRect(),
                           Qt.AspectRatioMode.KeepAspectRatio)
            self._fit_to_window = True
            self.zoom_changed.emit(self._zoom_percent())

    def fit_width(self):
        if not self._photo_scene.has_photo():
            return
        sw = self._photo_scene.sceneRect().width()
        vw = self.viewport().width()
        if sw > 0 and vw > 0:
            self.resetTransform()
            self.scale(vw / sw, vw / sw)
            self._fit_to_window = False
            self.zoom_changed.emit(self._zoom_percent())

    def zoom_100(self):
        self.resetTransform()
        self._fit_to_window = False
        self.zoom_changed.emit(100)

    def zoom_in(self):
        cur = self._current_scale()
        if cur >= _MAX_SCALE:
            return
        self.scale(min(_ZOOM_STEP_IN, _MAX_SCALE / cur),
                   min(_ZOOM_STEP_IN, _MAX_SCALE / cur))
        self._fit_to_window = False
        self.zoom_changed.emit(self._zoom_percent())

    def zoom_out(self):
        cur = self._current_scale()
        if cur <= _MIN_SCALE:
            return
        self.scale(max(_ZOOM_STEP_OUT, _MIN_SCALE / cur),
                   max(_ZOOM_STEP_OUT, _MIN_SCALE / cur))
        self._fit_to_window = False
        self.zoom_changed.emit(self._zoom_percent())

    def set_zoom_percent(self, percent: int):
        """Set an absolute zoom level (e.g. 100 = 1:1)."""
        target = percent / 100.0
        target = max(_MIN_SCALE, min(_MAX_SCALE, target))
        self.resetTransform()
        self.scale(target, target)
        self._fit_to_window = False
        self.zoom_changed.emit(self._zoom_percent())

    def _current_scale(self):
        return self.transform().m11()

    def _zoom_percent(self):
        return max(1, int(round(self._current_scale() * 100)))

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self._photo_scene.has_photo():
            # Welcome screen — draw in viewport coordinates so it's always centered
            painter.save()
            painter.resetTransform()
            vr = self.viewport().rect()

            # Icon area
            icon_size = 64
            ix = vr.center().x() - icon_size // 2
            iy = vr.center().y() - icon_size // 2 - 40
            painter.setBrush(QBrush(QColor(70, 70, 70)))
            painter.setPen(QPen(QColor(110, 110, 110), 2))
            painter.drawRoundedRect(ix, iy, icon_size, icon_size, 12, 12)
            painter.setPen(QPen(QColor(170, 170, 170), 3))
            painter.setFont(QFont("sans-serif", 28))
            painter.drawText(
                ix, iy, icon_size, icon_size,
                int(Qt.AlignmentFlag.AlignCenter), "+"
            )

            # Main message
            painter.setPen(QPen(QColor(200, 200, 200)))
            f1 = QFont()
            f1.setPixelSize(18)
            f1.setBold(True)
            painter.setFont(f1)
            painter.drawText(
                vr.left(), iy + icon_size + 18, vr.width(), 28,
                int(Qt.AlignmentFlag.AlignHCenter), "Open a photo or video to get started"
            )

            # Sub-message
            painter.setPen(QPen(QColor(130, 130, 130)))
            f2 = QFont()
            f2.setPixelSize(13)
            painter.setFont(f2)
            painter.drawText(
                vr.left(), iy + icon_size + 52, vr.width(), 22,
                int(Qt.AlignmentFlag.AlignHCenter),
                "Click anywhere here, drag & drop a file, or use  Open  above"
            )
            painter.drawText(
                vr.left(), iy + icon_size + 74, vr.width(), 22,
                int(Qt.AlignmentFlag.AlignHCenter),
                "Then double-click the canvas or use  + Bubble  to add speech bubbles"
            )
            painter.restore()

    def mousePressEvent(self, event):
        # When no media is loaded the canvas acts as a giant "open" button.
        if (event.button() == Qt.MouseButton.LeftButton
                and not self._photo_scene.has_photo()):
            self.open_media_requested.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_to_window:
            self.fit_photo()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(ALL_MEDIA_EXTENSIONS):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction() if event.mimeData().hasUrls() \
            else event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(ALL_MEDIA_EXTENSIONS):
                    if (self._photo_scene.is_dual_mode() and
                            self._photo_scene.has_photo()):
                        sp = self.mapToScene(event.position().toPoint())
                        lw = self._photo_scene._left_width()
                        if sp.x() > lw:
                            self.right_media_dropped.emit(path)
                            event.acceptProposedAction()
                            return
                    self.photo_dropped.emit(path)
                    event.acceptProposedAction()
                    return
        event.ignore()


# ---------------------------------------------------------------------------
# ZoomBar
# ---------------------------------------------------------------------------

class ZoomBar(QWidget):
    """Thin bar with zoom controls shown below the canvas."""

    # Slider range: 5 % … 500 %  (log-ish feel via step mapping)
    _SLIDER_MIN = 5
    _SLIDER_MAX = 500

    def __init__(self, view: PhotoView, parent=None):
        super().__init__(parent)
        self._view = view
        self._updating = False
        self.setFixedHeight(34)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        def _btn(text, tip, slot, width=None):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFixedHeight(26)
            if width:
                b.setFixedWidth(width)
            b.clicked.connect(slot)
            layout.addWidget(b)
            return b

        layout.addStretch()
        _btn("Fit",   "Fit entire image/video to window", self._on_fit,   width=36)
        _btn("Width", "Fit width to viewport",            self._view.fit_width, width=48)
        _btn("100%",  "Actual pixel size (1:1)",          self._on_100,   width=44)

        layout.addSpacing(6)

        _btn("−", "Zoom out", self._view.zoom_out, width=26)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(self._SLIDER_MIN, self._SLIDER_MAX)
        self._slider.setValue(100)
        self._slider.setFixedWidth(160)
        self._slider.setFixedHeight(20)
        self._slider.setToolTip("Drag to zoom")
        self._slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self._slider)

        _btn("+", "Zoom in", self._view.zoom_in, width=26)

        layout.addSpacing(4)
        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(46)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._zoom_label)

        layout.addStretch()

    # ------------------------------------------------------------------

    def _on_fit(self):
        self._view.fit_photo()

    def _on_100(self):
        self._view.zoom_100()

    def _on_slider(self, value: int):
        if self._updating:
            return
        # Apply the zoom level from slider
        self._view.set_zoom_percent(value)

    def update_zoom(self, percent: int):
        self._zoom_label.setText(f"{percent}%")
        self._updating = True
        self._slider.setValue(max(self._SLIDER_MIN,
                                  min(self._SLIDER_MAX, percent)))
        self._updating = False
