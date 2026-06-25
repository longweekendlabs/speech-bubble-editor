"""
editor_controller.py — EditorController: coordinates AppModel and PhotoScene.

Processes user actions, pushes undo commands, and keeps AppModel in sync.
MainWindow calls controller methods instead of talking to PhotoScene directly.
"""

import os

from PyQt6.QtCore import QObject, pyqtSignal

from app_model import AppModel
from constants import VIDEO_EXTENSIONS
from canvas import PhotoScene
from bubble import BubbleItem
from undo_commands import AddBubbleCommand, AddOverlayCommand


class EditorController(QObject):
    """
    Mediates between MainWindow (UI) and PhotoScene (data/rendering).

    Owns the AppModel and updates it on every state change.
    Emits coarse signals so MainWindow can update toolbar and panels
    without knowing scene internals.
    """

    media_loaded       = pyqtSignal(str, bool)   # path, is_video
    right_media_loaded = pyqtSignal(str, bool)   # path, is_video

    def __init__(self, scene: PhotoScene, parent=None):
        super().__init__(parent)
        self._model = AppModel()
        self._scene = scene

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model(self) -> AppModel:
        return self._model

    @property
    def scene(self) -> PhotoScene:
        return self._scene

    @property
    def undo_stack(self):
        return self._scene.undo_stack

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    def open_media(self, path: str) -> bool:
        """Load photo or video (auto-detected). Returns True on success."""
        is_video = os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS
        ok = self._scene.load_video(path) if is_video else self._scene.load_photo(path)
        if ok:
            if self._scene._photo_item is not None:
                self._scene._photo_item._source_path = path
            self._model.media_path       = path
            self._model.media_path_right = ""
            self._model.is_dual  = False
            self._model.is_meme  = False
            self.media_loaded.emit(path, is_video)
        return ok

    def open_right_media(self, path: str) -> bool:
        """Load the right-panel photo or video. Returns True on success."""
        is_video = os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS
        ok = (self._scene.load_right_video(path) if is_video
              else self._scene.load_right_photo(path))
        if ok:
            self._model.media_path_right = path
            self.right_media_loaded.emit(path, is_video)
        return ok

    def reset_project(self):
        """Return the editor to a blank launch state."""
        self._scene.reset_project()
        self._model = AppModel()

    # ------------------------------------------------------------------
    # Bubbles & overlays
    # ------------------------------------------------------------------

    def add_bubble(self, x: float, y: float, style: str = "oval") -> BubbleItem:
        """Create a bubble at (x, y) and push it onto the undo stack."""
        bubble = BubbleItem(x, y, style=style)
        self._scene.undo_stack.push(AddBubbleCommand(self._scene, bubble))
        self._scene.clearSelection()
        bubble.setSelected(True)
        return bubble

    def add_overlay(self, path: str):
        """Create an overlay from path and push it onto the undo stack.

        Returns the new MediaItem, or None if the file cannot be opened.
        """
        item = self._scene.create_overlay_item(path)
        if item is None:
            return None
        self._scene.undo_stack.push(AddOverlayCommand(self._scene, item))
        return item

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------

    def set_meme_mode(self, enabled: bool):
        if enabled:
            self._scene.enable_meme_mode()
        else:
            self._scene.disable_meme_mode()
        self._model.is_meme = enabled

    def set_dual_mode(self, enabled: bool):
        if enabled:
            self._scene.enable_dual_mode()
        else:
            self._scene.disable_dual_mode()
        self._model.is_dual = enabled
