"""
constants.py — Shared constants for Speech Bubble Editor.

Single source of truth for file-extension lists, undo merge IDs,
and other values referenced across multiple modules.
"""

# ---------------------------------------------------------------------------
# File extensions
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv',
                    '.m4v', '.flv', '.wmv', '.ts', '.mts')

ALL_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

# ---------------------------------------------------------------------------
# QUndoCommand merge IDs
# ---------------------------------------------------------------------------

MERGE_ID_MOVE_BUBBLE = 42
MERGE_ID_MOVE_MEDIA  = 43
MERGE_ID_STYLE       = 44
MERGE_ID_FONT        = 45
MERGE_ID_FILL_COLOR  = 46
MERGE_ID_BORDER_COLOR = 47
MERGE_ID_BORDER_WIDTH = 48
MERGE_ID_TEXT_COLOR  = 49
MERGE_ID_OPACITY     = 50
MERGE_ID_TEXT_ALIGNMENT = 51
MERGE_ID_TAIL_POSITION = 52
MERGE_ID_TAIL_WIDTH = 53
MERGE_ID_SHADOW = 54
MERGE_ID_Z_VALUE = 55
