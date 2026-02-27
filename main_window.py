"""
main_window.py — MainWindow: assembles toolbar, canvas, zoom bar,
                 properties panel, and video controls.
"""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from canvas import PhotoScene, PhotoView, ZoomBar
from toolbar import MainToolbar, ALL_EXTENSIONS
from properties_panel import PropertiesPanel
from video_controls import VideoControls
from bubble import BubbleItem
from media_item import MediaItem
from undo_commands import AddBubbleCommand, DeleteBubbleCommand
from version import __version__, __app_name__
from video_player import VIDEO_EXTENSIONS
from about_dialog import AboutDialog

import export as exporter

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(960, 640)
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.toolbar = MainToolbar(self)
        self.addToolBar(self.toolbar)

        self.scene = PhotoScene()
        self.view  = PhotoView(self.scene)
        self.zoom_bar = ZoomBar(self.view)
        self.video_controls = VideoControls()
        self.props = PropertiesPanel()

        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self.view, stretch=1)
        vbox.addWidget(self.zoom_bar)
        vbox.addWidget(self.video_controls)
        vbox.addWidget(self.props)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        tb = self.toolbar
        sc = self.scene
        vc = self.video_controls

        tb.open_media_requested.connect(self._on_open_media)
        tb.export_requested.connect(self._on_export)
        tb.undo_requested.connect(sc.undo_stack.undo)
        tb.redo_requested.connect(sc.undo_stack.redo)
        tb.add_bubble_requested.connect(self._on_add_bubble_clicked)
        tb.meme_toggled.connect(self._on_meme_toggled)
        tb.dual_toggled.connect(self._on_dual_toggled)
        tb.about_requested.connect(self._on_about)

        sc.undo_stack.canUndoChanged.connect(tb.set_undo_enabled)
        sc.undo_stack.canRedoChanged.connect(tb.set_redo_enabled)

        sc.double_clicked_on_canvas.connect(self._on_canvas_double_click)
        sc.bubble_changed.connect(self.props.update_for_bubble)
        sc.open_right_media_requested.connect(self._on_open_right_media)
        sc.selectionChanged.connect(self._on_selection_changed)

        self.view.zoom_changed.connect(self.zoom_bar.update_zoom)
        self.view.open_media_requested.connect(self._show_open_dialog)
        self.view.photo_dropped.connect(self._on_open_media)
        self.view.right_media_dropped.connect(self._on_right_media_dropped)

        vc.frame_changed.connect(self._on_frame_changed)
        vc.right_frame_changed.connect(self._on_right_frame_changed)
        vc.trim_in_changed.connect(self._on_trim_in)
        vc.trim_out_changed.connect(self._on_trim_out)
        vc.cut_requested.connect(self._on_cut)
        vc.cuts_cleared.connect(self._on_clear_cuts)
        vc.reverse_toggled.connect(self._on_reverse)

    # ------------------------------------------------------------------
    # Media loading — universal (photo or video, auto-detected)
    # ------------------------------------------------------------------

    def _on_open_media(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            self._load_video(path)
        else:
            self._load_photo(path)

    def _load_photo(self, path: str):
        if self.scene.load_photo(path):
            self._media_loaded(path, is_video=False)
        else:
            QMessageBox.warning(self, "Open", f"Cannot open:\n{path}")

    def _load_video(self, path: str):
        if self.scene.load_video(path):
            self._media_loaded(path, is_video=True)
        else:
            QMessageBox.warning(self, "Open", f"Cannot open:\n{path}")

    def _media_loaded(self, path: str, is_video: bool):
        if self.scene._photo_item is not None:
            self.scene._photo_item._source_path = path

        self.toolbar.set_media_loaded(True)
        self.toolbar.set_meme_checked(False)
        self.toolbar.set_dual_checked(False)
        self.toolbar.set_meme_enabled(True)
        self.toolbar.set_dual_enabled(True)

        if is_video:
            self.video_controls.set_player(self.scene.video_player)
            self.video_controls.set_right_player(None)
        else:
            self.video_controls.set_player(None)
            self.video_controls.set_right_player(None)

        self.props.clear()
        self.view.fit_photo()
        # Restore normal cursor once media is loaded
        self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------
    # Right media (dual mode)
    # ------------------------------------------------------------------

    def _on_open_right_media(self):
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Right Media", "",
            f"All supported media ({ext_list})"
        )
        if path:
            self._on_right_media_dropped(path)

    def _on_right_media_dropped(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            ok = self.scene.load_right_video(path)
            if ok:
                # Bind right player to video controls
                self.video_controls.set_right_player(
                    self.scene.video_player_right)
        else:
            ok = self.scene.load_right_photo(path)
        if not ok:
            QMessageBox.warning(self, "Open Right Media",
                                f"Cannot open:\n{path}")
        else:
            self.view.fit_photo()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export(self):
        self.video_controls._stop_playback()   # pause before export
        has_left_video  = self.scene.has_video()
        has_right_video = (self.scene.video_player_right is not None
                           and self.scene.video_player_right.is_loaded())

        if has_left_video or has_right_video:
            exporter.export_video(
                self, self.scene,
                self.scene._photo_item,
                self.scene.video_player,        # may be None if left=photo
                right_photo_item=self.scene._photo_item_right,
                right_player=self.scene.video_player_right,
                is_dual=self.scene.is_dual_mode(),
            )
        else:
            exporter.export_photo(
                self, self.scene,
                self.scene._photo_item,
                right_photo_item=self.scene._photo_item_right,
                is_dual=self.scene.is_dual_mode(),
            )

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------

    def _on_meme_toggled(self, enabled: bool):
        if enabled:
            self.scene.enable_meme_mode()
        else:
            self.scene.disable_meme_mode()
        self.view.fit_photo()

    def _on_dual_toggled(self, enabled: bool):
        if enabled:
            self.scene.enable_dual_mode()
        else:
            self.scene.disable_dual_mode()
            # Unbind right player from controls when leaving dual mode
            self.video_controls.set_right_player(None)
        self.view.fit_photo()

    # ------------------------------------------------------------------
    # Video controls
    # ------------------------------------------------------------------

    def _on_frame_changed(self, frame: int):
        self.scene.update_frame(frame)
        self.video_controls.set_current_frame(frame)

    def _on_right_frame_changed(self, frame: int):
        self.scene.update_right_frame(frame)

    def _on_trim_in(self, frame: int):
        player = self._active_player()
        if player:
            player.set_trim_in(frame)
            self.video_controls.sync_markers()

    def _on_trim_out(self, frame: int):
        player = self._active_player()
        if player:
            player.set_trim_out(frame)
            self.video_controls.sync_markers()

    def _on_cut(self):
        player = self._active_player()
        if not player:
            return
        s, e = player.trim_in, player.trim_out
        if s >= e:
            return
        player.add_cut(s, e)
        player.set_trim_in(0)
        player.set_trim_out(player.frame_count - 1)
        self.video_controls.sync_markers()
        # If the playhead is now inside the cut range, jump past it
        cur = self.video_controls._current_frame
        if s <= cur <= e:
            next_frame = e + 1
            if next_frame > player.frame_count - 1:
                next_frame = 0
            self.video_controls._current_frame = next_frame
            self._on_frame_changed(next_frame)

    def _on_clear_cuts(self):
        player = self._active_player()
        if player:
            player.clear_cuts()
            self.video_controls.sync_markers()

    def _on_reverse(self):
        player = self._active_player()
        if player:
            player.toggle_reverse()

    def _active_player(self):
        """Return the player that the video controls are currently editing."""
        if self.video_controls.active_side == "right":
            return self.scene.video_player_right
        return self.scene.video_player

    # ------------------------------------------------------------------
    # Canvas double-click → add bubble
    # ------------------------------------------------------------------

    def _show_open_dialog(self):
        """Open file dialog — called from toolbar button or canvas click."""
        from toolbar import ALL_EXTENSIONS
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            f"All supported media ({ext_list})"
        )
        if path:
            self._on_open_media(path)

    def _on_add_bubble_clicked(self):
        """Add a bubble at the centre of the current scene rect."""
        if not self.scene.has_photo():
            return
        c = self.scene.sceneRect().center()
        self._on_canvas_double_click(c.x(), c.y())

    def _on_canvas_double_click(self, x: float, y: float):
        bubble = BubbleItem(x, y)
        cmd = AddBubbleCommand(self.scene, bubble)
        self.scene.undo_stack.push(cmd)
        self.scene.clearSelection()
        bubble.setSelected(True)
        self.props.update_for_bubble(bubble)

    # ------------------------------------------------------------------
    # Selection → properties panel
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        selected = self.scene.selectedItems()
        bubbles = [i for i in selected if isinstance(i, BubbleItem)]
        media   = [i for i in selected if isinstance(i, MediaItem)]
        if bubbles:
            self.props.update_for_bubble(bubbles[0])
        elif media:
            self.props.update_for_media(media[0])
        else:
            self.props.clear()

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _on_about(self):
        AboutDialog(self).exec()
