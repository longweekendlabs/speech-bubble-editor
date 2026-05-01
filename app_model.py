"""
app_model.py — Project state (no Qt dependency).
"""

from dataclasses import dataclass


@dataclass
class AppModel:
    """Current project state. No Qt imports."""
    media_path:       str  = ""
    media_path_right: str  = ""
    is_dual:          bool = False
    is_meme:          bool = False
