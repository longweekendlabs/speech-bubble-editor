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
from PyQt6.QtCore import Qt, QRectF, QPointF, QEvent, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QUndoStack, QFont, QPen,
    QFontMetrics, QTransform, QBrush, QImage,
)

from video_player import VideoPlayer, FrameDecodeWorker
from media_item import MediaItem
from constants import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

_BAR_FRACTION  = 0.065  # caption bar height as fraction of photo height
_DUAL_GAP      = 4      # pixel gap between left and right media (module-level fallback)
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
        self.setZValue(50)

        # Cache for the font-shrink result: (text, rect_w, rect_h) → pixel_size
        self._font_size_cache: tuple | None = None

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
        self._font_size_cache = None  # text may have changed
        self.update()

    def set_geometry(self, x: float, y: float, w: float, h: float):
        """Update position and size, resetting the font-shrink cache."""
        self.prepareGeometryChange()
        self._rect = QRectF(x, y, w, h)
        self._font_size_cache = None
        self._text_item.setTextWidth(w - 32)
        self._center_text_item()
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
        text_rect = self._rect.adjusted(20, 4, -20, -4)
        flags     = (int(Qt.AlignmentFlag.AlignHCenter) |
                     int(Qt.AlignmentFlag.AlignVCenter) |
                     int(Qt.TextFlag.TextWordWrap))

        # Use cached pixel size if the key matches, else recompute
        cache_key = (text, text_rect.width(), text_rect.height())
        if self._font_size_cache and self._font_size_cache[0] == cache_key:
            font = QFont(self._font)
            font.setPixelSize(self._font_size_cache[1])
        else:
            font   = QFont(self._font)
            min_px = max(10, font.pixelSize() // 4)
            while font.pixelSize() > min_px:
                fm = QFontMetrics(font)
                if fm.boundingRect(text_rect.toRect(), flags, text).height() \
                        <= text_rect.height():
                    break
                font.setPixelSize(font.pixelSize() - 2)
            self._font_size_cache = (cache_key, font.pixelSize())

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
        painter.fillRect(self._rect, QColor("#121212"))

        pen = QPen(QColor("#4a4a4a"))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self._rect.adjusted(12, 12, -12, -12))

        font = QFont()
        font.setPixelSize(max(14, int(self._rect.height() * 0.035)))
        painter.setFont(font)
        painter.setPen(QPen(QColor("#9a9a9a")))
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
# DualSeamItem
# ---------------------------------------------------------------------------

class DualSeamItem(QGraphicsItem):
    """Draws the gap/border/feather between dual panels."""

    def __init__(self, x, y, w, h):
        super().__init__()
        self._rect         = QRectF(x, y, w, h)
        self._gap_color    = QColor("#121212")
        self._border_color = QColor("#4a4a4a")
        self._border_width = 0.0
        self._feather      = 0
        self.setZValue(-0.5)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,    False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable,  False)

    def set_geometry(self, x, y, w, h):
        self.prepareGeometryChange()
        self._rect = QRectF(x, y, max(0.0, float(w)), float(h))
        self.update()

    def set_gap_color(self, color: QColor):
        self._gap_color = color
        self.update()

    def set_border(self, color: QColor, width: float):
        self._border_color = color
        self._border_width = width
        self.update()

    def set_feather(self, px: int):
        self._feather = max(0, px)
        self.update()

    def boundingRect(self):
        return QRectF(self._rect)

    def paint(self, painter, option, widget=None):
        if self._rect.width() <= 0:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self._rect, self._gap_color)
        if self._border_width > 0:
            pen = QPen(self._border_color, self._border_width)
            painter.setPen(pen)
            x, y, h = self._rect.x(), self._rect.y(), self._rect.height()
            painter.drawLine(QPointF(x, y), QPointF(x, y + h))
            rx = x + self._rect.width()
            painter.drawLine(QPointF(rx, y), QPointF(rx, y + h))
        if self._feather > 0:
            from PyQt6.QtGui import QLinearGradient
            f = self._feather
            x, y, h = self._rect.x(), self._rect.y(), self._rect.height()
            for gx, c0, c1 in [
                (x,             QColor(0,0,0,0), QColor(0,0,0,100)),
                (x + self._rect.width() - f, QColor(0,0,0,100), QColor(0,0,0,0)),
            ]:
                lg = QLinearGradient(gx, 0, gx + f, 0)
                lg.setColorAt(0.0, c0)
                lg.setColorAt(1.0, c1)
                painter.fillRect(QRectF(gx, y, f, h), QBrush(lg))


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
        overlay_added(object)                   — MediaItem added as overlay
        overlay_removed(object)                 — MediaItem removed as overlay
    """

    double_clicked_on_canvas   = pyqtSignal(float, float)
    bubble_changed             = pyqtSignal(object)
    open_right_media_requested = pyqtSignal()
    overlay_added              = pyqtSignal(object)   # MediaItem
    overlay_removed            = pyqtSignal(object)   # MediaItem
    lobe_edit_requested        = pyqtSignal(object, int)  # bubble, lobe index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._photo_item:        MediaItem | None = None
        self._photo_item_right:  MediaItem | None = None
        self._right_placeholder: RightMediaPlaceholder | None = None
        self._video_player:       VideoPlayer | None = None
        self._video_player_right: VideoPlayer | None = None

        # Background decode workers (one per player); None when no video loaded.
        self._decode_worker:       FrameDecodeWorker | None = None
        self._decode_thread:       QThread | None = None
        self._decode_worker_right: FrameDecodeWorker | None = None
        self._decode_thread_right: QThread | None = None
        # Generation counter per side: incremented on each new video load so
        # late-arriving results from old videos are silently discarded.
        self._decode_gen_left  = 0
        self._decode_gen_right = 0

        self.undo_stack  = QUndoStack(self)
        self._meme_top:  MemeBarItem | None = None
        self._meme_bot:  MemeBarItem | None = None
        self._dual_mode  = False
        self._fitting    = False   # re-entrancy guard for fit_scene_to_media

        self._overlay_layers: list = []            # list[MediaItem]
        self._dual_gap = _DUAL_GAP                 # instance copy of gap
        self._dual_seam: DualSeamItem | None = None
        self._dual_border_color = QColor("#4a4a4a")
        self._dual_border_width = 0.0

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
        self._decode_gen_left, self._decode_worker, self._decode_thread = \
            self._start_decode_worker(player, self._on_left_frame_ready)
        return True

    def _start_decode_worker(self, player: VideoPlayer, ready_slot) \
            -> tuple[int, FrameDecodeWorker, QThread]:
        """
        Create a FrameDecodeWorker for *player*, move it to a new QThread, and
        connect its frame_ready signal to *ready_slot*.

        Returns (generation, worker, thread).  The generation value is the
        initial stamp; callers should store it and compare against incoming
        frame_ready emissions to detect stale results.
        """
        worker = FrameDecodeWorker(player)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.frame_ready.connect(ready_slot)
        thread.start()
        return worker._generation, worker, thread

    @staticmethod
    def _stop_decode_worker(worker: FrameDecodeWorker | None,
                            thread: QThread | None) -> None:
        """Drain in-flight decodes, stop the thread, and schedule cleanup."""
        if worker is not None:
            worker.pause()           # wait for any running _decode to finish
            worker.frame_ready.disconnect()
        if thread is not None:
            thread.quit()
            thread.wait()
            thread.deleteLater()
        if worker is not None:
            worker.deleteLater()

    def _reset_all(self):
        """Release all media and reset modes."""
        self._remove_meme_bars()
        self._clear_overlays()
        self._clear_dual_state()
        # Stop left decode worker before releasing the player it wraps.
        self._stop_decode_worker(self._decode_worker, self._decode_thread)
        self._decode_worker = None
        self._decode_thread = None
        if self._video_player is not None:
            self._video_player.release()
            self._video_player = None
        if self._photo_item is not None:
            self.removeItem(self._photo_item)
            self._photo_item = None

    def reset_project(self):
        """Clear every project item and return the scene to its launch state."""
        self.undo_stack.clear()
        self._remove_meme_bars()
        self._clear_overlays()
        self._clear_dual_state()
        self._stop_decode_worker(self._decode_worker, self._decode_thread)
        self._decode_worker = None
        self._decode_thread = None
        self._decode_gen_left += 1
        self._decode_gen_right += 1
        if self._video_player is not None:
            self._video_player.release()
            self._video_player = None
        self.clear()
        self._photo_item = None
        self._photo_item_right = None
        self._right_placeholder = None
        self._meme_top = None
        self._meme_bot = None
        self._overlay_layers.clear()
        self._dual_mode = False
        self._dual_seam = None
        self.setSceneRect(QRectF(0, 0, 900, 600))

    # ------------------------------------------------------------------
    # Background decode callbacks (UI thread — auto QueuedConnection)
    # ------------------------------------------------------------------

    @pyqtSlot(int, int, QImage)
    def _on_left_frame_ready(self, gen: int, frame_idx: int, image: QImage):
        """Called on the UI thread when the left decode worker finishes a frame."""
        if gen != self._decode_gen_left:
            return  # stale result from a previous video — discard
        if self._photo_item is not None:
            self._photo_item.set_pixmap(QPixmap.fromImage(image))

    @pyqtSlot(int, int, QImage)
    def _on_right_frame_ready(self, gen: int, frame_idx: int, image: QImage):
        """Called on the UI thread when the right decode worker finishes a frame."""
        if gen != self._decode_gen_right:
            return
        if self._photo_item_right is not None:
            self._photo_item_right.set_pixmap(QPixmap.fromImage(image))

    # ------------------------------------------------------------------
    # Video frame update (called from MainWindow when scrubber moves)
    # ------------------------------------------------------------------

    def update_frame(self, frame_idx: int):
        """Request async refresh of the background pixmap(s) to the given video frame."""
        if self._video_player is not None and self._photo_item is not None:
            if self._decode_worker is not None:
                self._decode_worker.request(frame_idx)

        for item in self._overlay_layers:
            player = item.video_player() if hasattr(item, "video_player") else None
            if player is not None and player.is_loaded():
                idx = min(frame_idx, player.frame_count - 1)
                pix = player.get_frame_pixmap(idx)
                if pix is not None:
                    item.set_pixmap(pix)

        if self._dual_mode and self._video_player_right is not None \
                and self._photo_item_right is not None:
            right_idx = min(frame_idx,
                            self._video_player_right.frame_count - 1)
            if self._decode_worker_right is not None:
                self._decode_worker_right.request(right_idx)

    def update_right_frame(self, frame_idx: int):
        """Async update of only the right media frame (independent right-player scrubbing)."""
        if self._dual_mode and self._video_player_right is not None \
                and self._photo_item_right is not None:
            right_idx = min(frame_idx,
                            self._video_player_right.frame_count - 1)
            if self._decode_worker_right is not None:
                self._decode_worker_right.request(right_idx)

    def pause_decode_workers(self):
        """
        Block until all in-flight decodes complete and prevent new ones.
        Call before accessing players directly (e.g. at the start of export).
        """
        if self._decode_worker is not None:
            self._decode_worker.pause()
        if self._decode_worker_right is not None:
            self._decode_worker_right.pause()

    def resume_decode_workers(self):
        """Re-enable async decoding after a pause."""
        if self._decode_worker is not None:
            self._decode_worker.resume()
        if self._decode_worker_right is not None:
            self._decode_worker_right.resume()

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
            bar.set_geometry(sr.x(), y, w, bar_h)

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
        snap_x = lx + lw + self._dual_gap
        self.setSceneRect(QRectF(lx, ly, lw * 2 + self._dual_gap, lh))
        self._right_placeholder = RightMediaPlaceholder(
            snap_x, ly, lw, lh)
        self.addItem(self._right_placeholder)

        # Create the seam item
        self._dual_seam = DualSeamItem(lx + lw, ly, self._dual_gap, lh)
        self._dual_seam.set_border(self._dual_border_color, self._dual_border_width)
        self.addItem(self._dual_seam)

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
        # Stop right decode worker before releasing the player.
        self._stop_decode_worker(self._decode_worker_right, self._decode_thread_right)
        self._decode_worker_right = None
        self._decode_thread_right = None
        if self._video_player_right is not None:
            self._video_player_right.release()
            self._video_player_right = None
        if self._dual_seam is not None:
            if self._dual_seam.scene() is self:
                self.removeItem(self._dual_seam)
            self._dual_seam = None

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
        # Stop old right worker before replacing the player.
        self._stop_decode_worker(self._decode_worker_right, self._decode_thread_right)
        self._decode_worker_right = None
        self._decode_thread_right = None
        if self._video_player_right is not None:
            self._video_player_right.release()
        self._video_player_right = player
        self._decode_gen_right, self._decode_worker_right, self._decode_thread_right = \
            self._start_decode_worker(player, self._on_right_frame_ready)
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
        media.setPos(lx + lw + self._dual_gap, ly)
        self._photo_item_right = media
        self.addItem(self._photo_item_right)

        # Expand scene to fit both sides
        self.setSceneRect(QRectF(lx, ly, lw + self._dual_gap + right_w, lh))

        # Update seam position
        if self._dual_seam is not None:
            self._dual_seam.set_geometry(lx + lw, ly, self._dual_gap, lh)

        # Expand meme bars if active
        self._update_meme_bar_layout()
        return True

    # ------------------------------------------------------------------
    # Dual seam controls
    # ------------------------------------------------------------------

    def set_dual_gap(self, gap: int):
        self._dual_gap = max(0, int(gap))
        if self._dual_mode:
            self._relayout_dual()

    def set_dual_border(self, color: QColor, width: float):
        self._dual_border_color = color
        self._dual_border_width = width
        if self._dual_seam:
            self._dual_seam.set_border(color, width)

    def set_dual_feather(self, px: int):
        if self._dual_seam:
            self._dual_seam.set_feather(px)

    def _relayout_dual(self):
        """Recompute dual layout after gap change."""
        if not self._dual_mode or not self._photo_item:
            return
        lx = self._photo_item.pos().x()
        ly = self._photo_item.pos().y()
        lw = self._left_width()
        lh = self._left_height()
        snap_x = lx + lw + self._dual_gap
        if self._photo_item_right:
            self._photo_item_right.setPos(snap_x, ly)
            rw = self._photo_item_right.display_w
            self.setSceneRect(QRectF(lx, ly, lw + self._dual_gap + rw, lh))
        elif self._right_placeholder:
            ph = self._right_placeholder
            pw = ph._rect.width()
            ph.prepareGeometryChange()
            ph._rect = QRectF(snap_x, ly, pw, lh)
            ph.update()
            self.setSceneRect(QRectF(lx, ly, lw + self._dual_gap + pw, lh))
        # Update seam item
        if self._dual_seam:
            self._dual_seam.set_geometry(lx + lw, ly, self._dual_gap, lh)
        self._update_meme_bar_layout()

    # ------------------------------------------------------------------
    # Overlay layers
    # ------------------------------------------------------------------

    def create_overlay_item(self, file_path: str):
        """Create a configured overlay MediaItem (not yet added to scene).

        Returns a MediaItem ready to be pushed via AddOverlayCommand, or None
        if the file cannot be opened.
        """
        import os as _os
        ext = _os.path.splitext(file_path)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            p = VideoPlayer()
            if not p.load(file_path):
                return None
            px = p.get_frame_pixmap(0)
            if px is None:
                p.release()
                return None
        else:
            p = None
            px = QPixmap(file_path)
            if px.isNull():
                return None

        item = MediaItem(px, is_overlay=True)
        if p is not None:
            item.set_video_player(p)
        # Scale to ~35% of scene width
        sr = self.sceneRect()
        target_w = max(120.0, sr.width() * 0.35)
        scale = target_w / max(1, px.width())
        item.set_display_size(px.width() * scale, px.height() * scale)
        # Centre in scene
        cx = sr.center().x() - item.display_w / 2
        cy = sr.center().y() - item.display_h / 2
        item.setPos(cx, cy)
        # Newly added image layers join the shared stack on top.
        item.setZValue(self.next_stack_z())
        return item

    def stackable_items(self):
        """Every item that participates in layer ordering, bottom-up."""
        from bubble import BubbleItem
        from redaction import RedactionItem
        from speedlines import SpeedLinesItem
        out = []
        for item in self.items():
            if item.parentItem() is not None:
                continue
            if isinstance(item, (BubbleItem, RedactionItem, SpeedLinesItem)):
                out.append(item)
            elif isinstance(item, MediaItem) and getattr(item, "_is_overlay", False):
                out.append(item)
        return sorted(out, key=lambda i: i.zValue())

    def next_stack_z(self) -> float:
        """Z for a newly added item: above everything already stacked.

        All overlay types share ONE z space, so the most recently added item is
        always on top regardless of its kind, and the Layers list can reorder
        them freely.
        """
        items = self.stackable_items()
        top = max((i.zValue() for i in items), default=90.0)
        return max(100.0, top + 10.0)

    def remove_overlay(self, item):
        """Remove an overlay layer from the scene and the tracking list."""
        if item in self._overlay_layers:
            self._overlay_layers.remove(item)
            if hasattr(item, "video_player") and item.video_player() is not None:
                item.video_player().release()
            if item.scene() is self:
                self.removeItem(item)
            self.overlay_removed.emit(item)

    def get_overlay_layers(self) -> list:
        return list(self._overlay_layers)

    def _clear_overlays(self):
        for item in list(self._overlay_layers):
            if hasattr(item, "video_player") and item.video_player() is not None:
                item.video_player().release()
            if item.scene() is self:
                self.removeItem(item)
        self._overlay_layers.clear()
        if self._dual_seam is not None:
            if self._dual_seam.scene() is self:
                self.removeItem(self._dual_seam)
            self._dual_seam = None

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
                      + self._photo_item.display_w + self._dual_gap)
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
                snap_x = lx + lw + self._dual_gap
                self._photo_item_right.setPos(snap_x, ly)

                rw = self._photo_item_right.display_w
                rh = self._photo_item_right.display_h
                total_w = snap_x + rw
                total_h = max(lh, rh)
            elif self._dual_mode and self._right_placeholder:
                # No right media yet — keep placeholder snapped to left image
                snap_x = lx + lw + self._dual_gap
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

            # Update seam position if dual seam is active
            if self._dual_seam and self._dual_mode:
                self._dual_seam.set_geometry(lx + lw, ly, self._dual_gap, lh)

            # Keep meme bars spanning the full canvas if meme mode is active
            self._update_meme_bar_layout()
        finally:
            self._fitting = False

    @property
    def photo_pixmap(self):
        return self._photo_item.pixmap() if self._photo_item else None

    # ------------------------------------------------------------------
    # Crop (photos only)
    # ------------------------------------------------------------------

    def _photo_frame_rect(self):
        """Scene-space rect the base photo currently occupies."""
        it = self._photo_item
        from PyQt6.QtCore import QRectF as _QRectF
        if it is None:
            return _QRectF()
        return _QRectF(it.pos().x(), it.pos().y(), it.display_w, it.display_h)

    def _swap_photo_pixmap(self, pixmap, dx: float, dy: float):
        """Replace the base photo pixmap (native + display resize, keeping the
        current on-screen scale) and shift every overlay item by (dx, dy)."""
        from bubble import BubbleItem
        from redaction import RedactionItem
        from speedlines import SpeedLinesItem
        it = self._photo_item
        sx = it.display_w / it.pixmap().width()
        sy = it.display_h / it.pixmap().height()
        it.prepareGeometryChange()
        it._pixmap = pixmap
        it._native_w = float(pixmap.width())
        it._native_h = float(pixmap.height())
        it._display_w = pixmap.width() * sx
        it._display_h = pixmap.height() * sy
        it._update_handle_positions()
        it.update()
        for item in self.items():
            if item.parentItem() is not None or item is it:
                continue
            if isinstance(item, (BubbleItem, RedactionItem)) or (
                    isinstance(item, MediaItem) and getattr(item, "_is_overlay", False)):
                item.moveBy(dx, dy)
            elif isinstance(item, SpeedLinesItem):
                item.set_frame(self._photo_frame_rect())
        self.fit_scene_to_media()
        # Speed lines need the post-fit frame (fit may move nothing, but the
        # display size just changed) — refresh once more to be safe.
        for item in self.items():
            if isinstance(item, SpeedLinesItem):
                item.set_frame(self._photo_frame_rect())

    def apply_rotation(self, turns: int) -> bool:
        """Rotate the base photo by `turns` × 90° clockwise.

        Bubbles and overlays are repositioned so they stay on the same part of
        the picture, but are NOT themselves rotated — turning a photo sideways
        should not leave the lettering unreadable.
        """
        from PyQt6.QtGui import QTransform
        from bubble import BubbleItem
        from redaction import RedactionItem
        from speedlines import SpeedLinesItem

        turns %= 4
        if self._photo_item is None or turns == 0:
            return False
        if self._video_player is not None:
            return False

        it = self._photo_item
        pm = it.pixmap()
        rotated = pm.transformed(QTransform().rotate(90 * turns),
                                 Qt.TransformationMode.SmoothTransformation)
        old_dw, old_dh = float(it.display_w), float(it.display_h)
        px, py = it.pos().x(), it.pos().y()

        it.prepareGeometryChange()
        it._pixmap = rotated
        it._native_w = float(rotated.width())
        it._native_h = float(rotated.height())
        if turns % 2 == 1:
            it._display_w, it._display_h = old_dh, old_dw
        else:
            it._display_w, it._display_h = old_dw, old_dh
        it._update_handle_positions()
        it.update()
        # Resize the scene BEFORE moving anything: items clamp themselves to the
        # current sceneRect on setPos, so repositioning against the old (still
        # un-rotated) rect squashed them back inside the wrong bounds.
        self.fit_scene_to_media()

        def mapped(x: float, y: float):
            """Photo-relative point under the same rotation."""
            if turns == 1:      # 90° clockwise
                return old_dh - y, x
            if turns == 2:      # 180°
                return old_dw - x, old_dh - y
            return y, old_dw - x        # 270° clockwise (= 90° anticlockwise)

        for item in self.items():
            if item.parentItem() is not None or item is it:
                continue
            if isinstance(item, (BubbleItem, RedactionItem)) or (
                    isinstance(item, MediaItem)
                    and getattr(item, "_is_overlay", False)):
                nx, ny = mapped(item.pos().x() - px, item.pos().y() - py)
                item.setPos(px + nx, py + ny)

        self.fit_scene_to_media()
        for item in self.items():
            if isinstance(item, SpeedLinesItem):
                item.set_frame(self._photo_frame_rect())
        return True

    def apply_crop(self, rect) -> bool:
        """Crop the base photo to `rect` (native pixel coords)."""
        if self._photo_item is None or self._video_player is not None:
            return False
        pm = self._photo_item.pixmap()
        sx = self._photo_item.display_w / pm.width()
        sy = self._photo_item.display_h / pm.height()
        self._swap_photo_pixmap(pm.copy(rect), -rect.x() * sx, -rect.y() * sy)
        return True

    def restore_photo(self, pixmap, rect):
        """Undo a crop: restore the full pixmap and shift items back."""
        if self._photo_item is None:
            return
        cur = self._photo_item.pixmap()
        sx = self._photo_item.display_w / cur.width()
        sy = self._photo_item.display_h / cur.height()
        self._swap_photo_pixmap(pixmap, rect.x() * sx, rect.y() * sy)

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
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setAcceptDrops(True)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._photo_scene   = scene
        self._fit_to_window = True
        self._tool          = "select"   # "select" | "move" (hand/pan)
        self._panning       = False      # middle-button pan in progress
        self._pan_start     = QPointF()
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        # Set background brush using palette-aware logic
        self._update_background_brush()

    def _update_background_brush(self):
        """Keep the empty canvas aligned with the fixed v4 dark theme."""
        self.setBackgroundBrush(QColor("#121212"))

    # --- tools & cursor -----------------------------------------------------

    def set_tool(self, mode: str):
        """Switch between the Select (edit bubbles) and Move (hand/pan) tools."""
        self._tool = mode if mode in ("select", "move") else "select"
        if self._tool == "move":
            # Hand tool: left-drag pans the view; items aren't grabbed.
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._apply_idle_cursor()

    def _apply_idle_cursor(self):
        """Resting cursor for the current tool/state."""
        if not self._photo_scene.has_photo():
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._tool == "move":
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._update_background_brush()

    def fit_photo(self):
        if self._photo_scene.has_photo():
            self.fitInView(self._photo_scene.sceneRect(),
                           Qt.AspectRatioMode.KeepAspectRatio)
            self._fit_to_window = True
            self.zoom_changed.emit(self._zoom_percent())
            self._apply_idle_cursor()

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
            icon_bg_color     = QColor("#232323")
            icon_border_color = QColor("#4a4a4a")
            icon_plus_color   = QColor("#9a9a9a")
            main_text_color   = QColor("#e6e6e6")
            sub_text_color    = QColor("#9a9a9a")

            painter.save()
            painter.resetTransform()
            vr = self.viewport().rect()

            # Icon area
            icon_size = 64
            ix = vr.center().x() - icon_size // 2
            iy = vr.center().y() - icon_size // 2 - 40
            painter.setBrush(QBrush(icon_bg_color))
            painter.setPen(QPen(icon_border_color, 2))
            painter.drawRoundedRect(ix, iy, icon_size, icon_size, 12, 12)
            painter.setPen(QPen(icon_plus_color, 3))
            painter.setFont(QFont("sans-serif", 28))
            painter.drawText(
                ix, iy, icon_size, icon_size,
                int(Qt.AlignmentFlag.AlignCenter), "+"
            )

            # Main message
            painter.setPen(QPen(main_text_color))
            f1 = QFont()
            f1.setPixelSize(18)
            f1.setBold(True)
            painter.setFont(f1)
            painter.drawText(
                vr.left(), iy + icon_size + 18, vr.width(), 28,
                int(Qt.AlignmentFlag.AlignHCenter), "Open a photo or video to get started"
            )

            # Sub-message
            painter.setPen(QPen(sub_text_color))
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
        # Middle-button drag always pans, regardless of the active tool — the
        # quickest way to move a zoomed-in view to the area you want.
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning   = True
            self._pan_start = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            h = self.horizontalScrollBar()
            v = self.verticalScrollBar()
            h.setValue(h.value() - int(delta.x()))
            v.setValue(v.value() - int(delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning and event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._apply_idle_cursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_to_window:
            self.fit_photo()

    def wheelEvent(self, event):
        if not self._photo_scene.has_photo():
            event.ignore()
            return
        # Zoom toward the cursor so "zoom into this area" lands where you point.
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter)
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
        self.setVisible(False)   # hidden until media is loaded

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
