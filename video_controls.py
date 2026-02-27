"""
video_controls.py — VideoControls: scrubber + playback + trim/cut/reverse UI.

Supports dual video: a Left/Right toggle appears when a right player is set.
Playback always advances both players in sync (left drives timing).
Trim/Cut/Reverse operate on whichever side is currently selected.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon

from video_player import VideoPlayer


# ---------------------------------------------------------------------------
# VideoScrubber
# ---------------------------------------------------------------------------

class VideoScrubber(QWidget):
    position_changed = pyqtSignal(int)
    trim_in_dragged  = pyqtSignal(int)   # emitted while dragging the in-marker
    trim_out_dragged = pyqtSignal(int)   # emitted while dragging the out-marker

    _MARKER_H    = 10
    _MARKER_GRAB = 14   # px radius around a triangle that counts as a hit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._frame_count  = 0
        self._current      = 0
        self._trim_in      = 0
        self._trim_out     = 0
        self._cuts: list[tuple[int, int]] = []
        self._dragging     = False
        self._trim_drag    = None   # "in" | "out" | None
        self._last_emitted = -1

    # ------------------------------------------------------------------

    def set_player(self, player: VideoPlayer | None):
        if player is None or not player.is_loaded():
            self._frame_count = 0
        else:
            self._frame_count = player.frame_count
            self._trim_in     = player.trim_in
            self._trim_out    = player.trim_out
            self._cuts        = player.cuts
        self._current = 0
        self.update()

    def set_current_frame(self, frame: int):
        self._current = frame
        self.update()

    def sync_from_player(self, player: VideoPlayer):
        self._trim_in  = player.trim_in
        self._trim_out = player.trim_out
        self._cuts     = player.cuts
        self.update()

    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(40, 40, 40))
        if self._frame_count <= 0:
            return

        track_y = self._MARKER_H + 2
        track_h = h - track_y - 2

        painter.fillRect(0, track_y, w, track_h, QColor(80, 80, 80))

        in_x  = self._f2x(self._trim_in)
        out_x = self._f2x(self._trim_out)
        painter.fillRect(in_x, track_y, out_x - in_x, track_h,
                         QColor(59, 130, 246, 200))

        for cs, ce in self._cuts:
            cx = self._f2x(cs)
            cw = self._f2x(ce) - cx
            painter.fillRect(cx, track_y, cw, track_h, QColor(220, 50, 50, 200))

        painter.setBrush(QColor(34, 197, 94))
        painter.setPen(Qt.PenStyle.NoPen)
        ix = in_x
        painter.drawPolygon(QPolygon([
            QPoint(ix, 0), QPoint(ix + self._MARKER_H, 0), QPoint(ix, self._MARKER_H),
        ]))

        painter.setBrush(QColor(249, 115, 22))
        ox = out_x
        painter.drawPolygon(QPolygon([
            QPoint(ox, 0), QPoint(ox - self._MARKER_H, 0), QPoint(ox, self._MARKER_H),
        ]))

        px = self._f2x(self._current)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(px, 0, px, h)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x = event.position().x()
        y = event.position().y()

        # Check if the click lands on or near a trim triangle (top strip)
        if self._frame_count > 0 and y <= self._MARKER_H + 4:
            in_x  = self._f2x(self._trim_in)
            out_x = self._f2x(self._trim_out)
            if abs(x - in_x) <= self._MARKER_GRAB:
                self._trim_drag = "in"
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                event.accept()
                return
            if abs(x - out_x) <= self._MARKER_GRAB:
                self._trim_drag = "out"
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                event.accept()
                return

        # Default: seek playhead
        self._trim_drag = None
        self._dragging  = True
        self._seek(x)

    def mouseMoveEvent(self, event):
        x = event.position().x()

        if self._trim_drag == "in":
            frame = self._x2f(x)
            frame = max(0, min(frame, self._trim_out - 1))
            self._trim_in = frame
            self.update()
            self.trim_in_dragged.emit(frame)
        elif self._trim_drag == "out":
            frame = self._x2f(x)
            frame = max(self._trim_in + 1, min(frame, self._frame_count - 1))
            self._trim_out = frame
            self.update()
            self.trim_out_dragged.emit(frame)
        elif self._dragging:
            self._seek(x)

    def mouseReleaseEvent(self, event):
        if self._trim_drag in ("in", "out"):
            # Emit final position to sync player's trim value
            if self._trim_drag == "in":
                self.trim_in_dragged.emit(self._trim_in)
            else:
                self.trim_out_dragged.emit(self._trim_out)
            self._trim_drag = None
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._dragging:
            self._dragging = False
            if self._current != self._last_emitted:
                self._last_emitted = self._current
                self.position_changed.emit(self._current)

    # ------------------------------------------------------------------

    def _f2x(self, frame: int) -> int:
        if self._frame_count <= 1:
            return 0
        return int(frame / (self._frame_count - 1) * self.width())

    def _x2f(self, x: float) -> int:
        if self.width() == 0 or self._frame_count <= 1:
            return 0
        t = max(0.0, min(1.0, x / self.width()))
        return int(round(t * (self._frame_count - 1)))

    def _seek(self, x: float):
        frame = self._x2f(x)
        if frame == self._current:
            return
        self._current = frame
        self.update()
        if not self._dragging or abs(frame - self._last_emitted) >= 4:
            self._last_emitted = frame
            self.position_changed.emit(frame)


# ---------------------------------------------------------------------------
# VideoControls
# ---------------------------------------------------------------------------

class VideoControls(QWidget):
    """
    Control bar shown below the canvas whenever a video is loaded.

    Signals:
        frame_changed(int)          — left/active-left frame changed
        right_frame_changed(int)    — right player frame (synced during playback)
        trim_in_changed(int)        — Set In clicked on active player
        trim_out_changed(int)       — Set Out clicked on active player
        cut_requested()
        cuts_cleared()
        reverse_toggled()
    """

    frame_changed       = pyqtSignal(int)
    right_frame_changed = pyqtSignal(int)
    trim_in_changed     = pyqtSignal(int)
    trim_out_changed    = pyqtSignal(int)
    cut_requested       = pyqtSignal()
    cuts_cleared        = pyqtSignal()
    reverse_toggled     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player:        VideoPlayer | None = None
        self._player_right:  VideoPlayer | None = None
        self._active_side    = "left"   # "left" | "right"
        self._current_frame  = 0
        self._playing        = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)

        self._build()
        self.setVisible(False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_player(self, player: VideoPlayer | None):
        """Bind the LEFT player (or None to hide controls)."""
        self._stop_playback()
        self._player = player
        self._current_frame = 0
        if self._active_side == "left":
            self._scrubber.set_player(player)

        if player and player.is_loaded():
            self._update_time_label(0)
            self._btn_reverse.setChecked(player.is_reversed)
            self.setVisible(True)
        else:
            # Hide only if right player also absent
            if not (self._player_right and self._player_right.is_loaded()):
                self.setVisible(False)

        self._update_side_toggle_visibility()

    def set_right_player(self, player: VideoPlayer | None):
        """Bind the RIGHT player. Shows the L/R toggle."""
        self._player_right = player
        has_left = self._player is not None and self._player.is_loaded()

        if player and player.is_loaded():
            if not has_left:
                # Left is a photo (no video) — auto-select the right side
                self._active_side = "right"
                self._btn_left.setChecked(False)
                self._btn_right_side.setChecked(True)

            if self._active_side == "right":
                self._scrubber.set_player(player)
                self._btn_reverse.setChecked(player.is_reversed)
                self._update_time_label_for(player, 0)

            self.setVisible(True)
        else:
            # Player removed — switch back to left side if needed
            if self._active_side == "right":
                self._active_side = "left"
                self._btn_left.setChecked(True)
                self._btn_right_side.setChecked(False)
                self._scrubber.set_player(self._player)
                if self._player and self._player.is_loaded():
                    self._btn_reverse.setChecked(self._player.is_reversed)
            if not has_left:
                self.setVisible(False)

        self._update_side_toggle_visibility()

    def set_current_frame(self, frame: int):
        self._current_frame = frame
        if self._active_side == "left":
            self._scrubber.set_current_frame(frame)
            self._update_time_label(frame)

    def sync_markers(self):
        player = self._active_player
        if player:
            self._scrubber.sync_from_player(player)
            frame = (self._current_frame if self._active_side == "left"
                     else min(self._current_frame, player.frame_count - 1))
            self._update_time_label_for(player, frame)

    @property
    def active_side(self) -> str:
        return self._active_side

    @property
    def _active_player(self) -> VideoPlayer | None:
        if self._active_side == "right" and self._player_right:
            return self._player_right
        return self._player

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        # Left/Right toggle (hidden when only one player)
        self._btn_left = QPushButton("L")
        self._btn_left.setFixedSize(26, 26)
        self._btn_left.setCheckable(True)
        self._btn_left.setChecked(True)
        self._btn_left.setToolTip("Edit left media")
        self._btn_left.clicked.connect(lambda: self._switch_side("left"))
        btn_row.addWidget(self._btn_left)

        self._btn_right_side = QPushButton("R")
        self._btn_right_side.setFixedSize(26, 26)
        self._btn_right_side.setCheckable(True)
        self._btn_right_side.setToolTip("Edit right media")
        self._btn_right_side.clicked.connect(lambda: self._switch_side("right"))
        btn_row.addWidget(self._btn_right_side)

        self._side_toggle_sep = QPushButton("|")
        self._side_toggle_sep.setFixedSize(10, 26)
        self._side_toggle_sep.setEnabled(False)
        self._side_toggle_sep.setStyleSheet("border: none; color: #555;")
        btn_row.addWidget(self._side_toggle_sep)

        # Initially hide L/R controls
        for w in (self._btn_left, self._btn_right_side, self._side_toggle_sep):
            w.setVisible(False)

        def _sbtn(text, tip, slot):
            b = QPushButton(text)
            b.setFixedSize(28, 26)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
            return b

        _sbtn("|◀", "First frame",         self._on_first_frame)
        _sbtn("◀",  "Step back 1 frame",   self._on_step_back)

        self._btn_play = QPushButton("▶")
        self._btn_play.setFixedWidth(36)
        self._btn_play.setFixedHeight(26)
        self._btn_play.setToolTip("Play / Pause")
        self._btn_play.clicked.connect(self._toggle_play)
        btn_row.addWidget(self._btn_play)

        _sbtn("▶",  "Step forward 1 frame", self._on_step_forward)
        _sbtn("▶|", "Last frame",            self._on_last_frame)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setFixedWidth(116)
        btn_row.addWidget(self._time_label)

        btn_row.addStretch()

        def _btn(label, tip, slot, checkable=False):
            b = QPushButton(label)
            b.setToolTip(tip)
            b.setFixedHeight(26)
            b.setCheckable(checkable)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
            return b

        _btn("[ In",     "Set trim-in to current frame",       self._on_set_in)
        _btn("Out ]",    "Set trim-out to current frame",      self._on_set_out)
        _btn("✂ Cut",   "Cut the selected trim range",         self._on_cut)
        _btn("✕ Cuts",  "Clear all cuts",                      self._on_clear_cuts)
        self._btn_reverse = _btn(
            "⟳ Reverse", "Toggle playback / export reversal",
            self._on_reverse, checkable=True,
        )

        layout.addLayout(btn_row)

        self._scrubber = VideoScrubber()
        self._scrubber.position_changed.connect(self._on_scrub)
        # Dragging a trim triangle emits these; route straight to parent signals
        self._scrubber.trim_in_dragged.connect(self.trim_in_changed)
        self._scrubber.trim_out_dragged.connect(self.trim_out_changed)
        layout.addWidget(self._scrubber)

    def _update_side_toggle_visibility(self):
        """Show L/R toggle only when both players are loaded."""
        has_left  = self._player is not None and self._player.is_loaded()
        has_right = self._player_right is not None and self._player_right.is_loaded()
        show = has_left and has_right
        for w in (self._btn_left, self._btn_right_side, self._side_toggle_sep):
            w.setVisible(show)

    def _switch_side(self, side: str):
        self._active_side = side
        self._btn_left.setChecked(side == "left")
        self._btn_right_side.setChecked(side == "right")

        player = self._active_player
        self._scrubber.set_player(player)
        if player and player.is_loaded():
            self._btn_reverse.setChecked(player.is_reversed)
            frame = self._current_frame if side == "left" \
                else min(self._current_frame, player.frame_count - 1)
            self._update_time_label_for(player, frame)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _toggle_play(self):
        active = self._active_player
        if not active or not active.is_loaded():
            return
        self._playing = not self._playing
        self._btn_play.setText("⏸" if self._playing else "▶")
        if self._playing:
            # Snap playhead to the correct end of the trim range if outside it.
            if (self._current_frame < active.trim_in
                    or self._current_frame > active.trim_out):
                start = active.trim_out if active.is_reversed else active.trim_in
                self._current_frame = start
                self._scrubber.set_current_frame(self._current_frame)
            ms = max(1, int(1000 / active.fps))
            self._timer.start(ms)
        else:
            self._timer.stop()

    def _stop_playback(self):
        self._playing = False
        self._timer.stop()
        self._btn_play.setText("▶")

    def _advance_frame(self):
        active = self._active_player
        if not active:
            return
        rev = active.is_reversed
        nxt = self._current_frame - 1 if rev else self._current_frame + 1

        # Skip over cut ranges (jump past in the direction of playback).
        while True:
            jumped = False
            for cs, ce in active.cuts:
                if cs <= active.trim_in and ce >= active.trim_out:
                    continue   # safety: cut spans whole trim range — ignore
                if cs <= nxt <= ce:
                    nxt = cs - 1 if rev else ce + 1
                    jumped = True
                    break
            if not jumped:
                break

        # Clamp to trim range and loop.
        if rev:
            if nxt < active.trim_in:
                nxt = active.trim_out   # loop: rewind wraps back to out-point
            if nxt > active.trim_out:
                nxt = active.trim_out
        else:
            if nxt < active.trim_in:
                nxt = active.trim_in
            if nxt > active.trim_out:
                nxt = active.trim_in    # loop: forward wraps back to in-point
        self._current_frame = nxt

        if self._active_side == "right":
            # Right player is the sole or active driver
            self._scrubber.set_current_frame(nxt)
            self._update_time_label_for(active, nxt)
            self.right_frame_changed.emit(nxt)
        else:
            # Left player drives; sync right to same frame index
            self._scrubber.set_current_frame(nxt)
            self._update_time_label(nxt)
            self.frame_changed.emit(nxt)
            if self._player_right and self._player_right.is_loaded():
                right_nxt = min(nxt, self._player_right.frame_count - 1)
                self.right_frame_changed.emit(right_nxt)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_scrub(self, frame: int):
        if self._active_side == "right":
            # Track position so playback resumes from here
            self._current_frame = frame
            self.right_frame_changed.emit(frame)
            if self._player_right:
                self._update_time_label_for(self._player_right, frame)
        else:
            self._current_frame = frame
            self._update_time_label(frame)
            self.frame_changed.emit(frame)

    def _on_set_in(self):
        frame = self._active_frame()
        self.trim_in_changed.emit(frame)

    def _on_set_out(self):
        frame = self._active_frame()
        self.trim_out_changed.emit(frame)

    def _on_cut(self):
        self.cut_requested.emit()

    def _on_clear_cuts(self):
        self.cuts_cleared.emit()

    def _on_reverse(self):
        self.reverse_toggled.emit()

    def _on_first_frame(self):
        self._go_to_frame(0)

    def _on_last_frame(self):
        active = self._active_player
        if active:
            self._go_to_frame(active.frame_count - 1)

    def _on_step_back(self):
        self._go_to_frame(max(0, self._current_frame - 1))

    def _on_step_forward(self):
        active = self._active_player
        if active:
            self._go_to_frame(min(active.frame_count - 1, self._current_frame + 1))

    def _go_to_frame(self, frame: int):
        """Seek to an exact frame, update scrubber and time label."""
        active = self._active_player
        if not active:
            return
        self._current_frame = frame
        self._scrubber.set_current_frame(frame)
        if self._active_side == "right":
            self._update_time_label_for(active, frame)
            self.right_frame_changed.emit(frame)
        else:
            self._update_time_label(frame)
            self.frame_changed.emit(frame)

    def _active_frame(self) -> int:
        if self._active_side == "right" and self._player_right:
            return min(self._current_frame,
                       self._player_right.frame_count - 1)
        return self._current_frame

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_time_label(self, frame: int):
        if self._player:
            self._update_time_label_for(self._player, frame)

    def _update_time_label_for(self, player: VideoPlayer, frame: int):
        fps = player.fps or 25.0
        # When a selection is active, show its range instead of current/total
        if player.trim_in > 0 or player.trim_out < player.frame_count - 1:
            in_s  = player.trim_in  / fps
            out_s = player.trim_out / fps
            self._time_label.setText(f"{self._fmt(in_s)}–{self._fmt(out_s)}")
        else:
            curr  = frame / fps
            total = player.frame_count / fps
            self._time_label.setText(f"{self._fmt(curr)} / {self._fmt(total)}")

    @staticmethod
    def _fmt(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"
