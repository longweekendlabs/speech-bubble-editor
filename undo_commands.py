"""
undo_commands.py — QUndoCommand subclasses for the undo/redo stack.

Commands implemented:
  AddBubbleCommand    — redo = add item,    undo = remove item
  DeleteBubbleCommand — redo = remove item, undo = add item back
  MoveBubbleCommand   — redo = move to new_pos, undo = move to old_pos
                        (consecutive moves of the same bubble are merged)
  TextChangeCommand   — redo = new text, undo = old text
"""

from PyQt6.QtGui import QUndoCommand
from PyQt6.QtCore import QPointF, QRectF


class AddBubbleCommand(QUndoCommand):
    def __init__(self, scene, bubble):
        super().__init__("Add Bubble")
        self._scene  = scene
        self._bubble = bubble

    def redo(self):
        self._scene.addItem(self._bubble)
        self._scene.clearSelection()
        self._bubble.setSelected(True)

    def undo(self):
        self._scene.removeItem(self._bubble)


class DeleteBubbleCommand(QUndoCommand):
    def __init__(self, scene, bubble):
        super().__init__("Delete Bubble")
        self._scene  = scene
        self._bubble = bubble

    def redo(self):
        self._scene.removeItem(self._bubble)

    def undo(self):
        self._scene.addItem(self._bubble)
        self._scene.clearSelection()
        self._bubble.setSelected(True)


class MoveBubbleCommand(QUndoCommand):
    # All move commands share the same id so Qt can merge consecutive moves
    _ID = 42

    def __init__(self, bubble, old_pos: QPointF, new_pos: QPointF):
        super().__init__("Move Bubble")
        self._bubble  = bubble
        self._old_pos = QPointF(old_pos)
        self._new_pos = QPointF(new_pos)

    def id(self) -> int:
        return self._ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge a later move of the same bubble — keeps only start→end."""
        if isinstance(other, MoveBubbleCommand) and other._bubble is self._bubble:
            self._new_pos = QPointF(other._new_pos)
            return True
        return False

    def redo(self):
        self._bubble.setPos(self._new_pos)

    def undo(self):
        self._bubble.setPos(self._old_pos)


class ResizeBubbleCommand(QUndoCommand):
    def __init__(self, bubble, old_rect: QRectF, new_rect: QRectF):
        super().__init__("Resize Bubble")
        self._bubble   = bubble
        self._old_rect = QRectF(old_rect)
        self._new_rect = QRectF(new_rect)

    def redo(self):
        self._bubble.set_body_rect(self._new_rect)

    def undo(self):
        self._bubble.set_body_rect(self._old_rect)


class TextChangeCommand(QUndoCommand):
    def __init__(self, bubble, old_text: str, new_text: str):
        super().__init__("Edit Text")
        self._bubble   = bubble
        self._old_text = old_text
        self._new_text = new_text

    def redo(self):
        self._bubble.set_text(self._new_text)

    def undo(self):
        self._bubble.set_text(self._old_text)


class MoveMediaCommand(QUndoCommand):
    """Undo/redo for dragging a MediaItem to a new position."""
    _ID = 43

    def __init__(self, scene, item, old_pos: QPointF, new_pos: QPointF):
        super().__init__("Move Media")
        self._scene   = scene
        self._item    = item
        self._old_pos = QPointF(old_pos)
        self._new_pos = QPointF(new_pos)

    def id(self) -> int:
        return self._ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if isinstance(other, MoveMediaCommand) and other._item is self._item:
            self._new_pos = QPointF(other._new_pos)
            return True
        return False

    def redo(self):
        self._item.setPos(self._new_pos)
        if hasattr(self._scene, 'fit_scene_to_media'):
            self._scene.fit_scene_to_media()

    def undo(self):
        self._item.setPos(self._old_pos)
        if hasattr(self._scene, 'fit_scene_to_media'):
            self._scene.fit_scene_to_media()


class ResizeMediaCommand(QUndoCommand):
    """Undo/redo for resizing a MediaItem via corner handles."""

    def __init__(self, scene, item,
                 old_pos: QPointF, old_w: float, old_h: float,
                 new_pos: QPointF, new_w: float, new_h: float):
        super().__init__("Resize Media")
        self._scene = scene
        self._item  = item
        self._old_pos = QPointF(old_pos)
        self._old_w, self._old_h = old_w, old_h
        self._new_pos = QPointF(new_pos)
        self._new_w, self._new_h = new_w, new_h

    def redo(self):
        self._item.set_display_size(self._new_w, self._new_h)
        self._item.setPos(self._new_pos)
        if hasattr(self._scene, 'fit_scene_to_media'):
            self._scene.fit_scene_to_media()

    def undo(self):
        self._item.set_display_size(self._old_w, self._old_h)
        self._item.setPos(self._old_pos)
        if hasattr(self._scene, 'fit_scene_to_media'):
            self._scene.fit_scene_to_media()
