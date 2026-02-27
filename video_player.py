"""
video_player.py — VideoPlayer: thin wrapper around OpenCV VideoCapture.

Provides:
  • Frame access as QPixmap or BGR numpy array
  • Trim in/out points
  • Cut ranges (frame ranges excluded from export)
  • Reverse flag
  • Ordered export-frame list respecting all edits
"""

import cv2
import numpy as np
from collections import OrderedDict

from PyQt6.QtGui import QImage, QPixmap

# Video file extensions accepted by the open dialogs
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv',
                    '.m4v', '.flv', '.wmv', '.ts', '.mts')

# Memory budget for the frame cache across all sizes of video
_CACHE_BUDGET_MB = 256


class FrameCache:
    """
    LRU cache for decoded video frames (stored as BGR numpy arrays).

    Cache capacity is computed automatically from the frame dimensions so the
    total memory footprint stays within _CACHE_BUDGET_MB regardless of video
    resolution:
        • 4 K  (3840×2160) → ~11 frames  (~256 MB)
        • 1080p(1920×1080) → ~42 frames  (~252 MB)
        • 720p (1280× 720) → ~94 frames  (capped at 128 → ~349 MB*)
        • 480p ( 854× 480) → 128 frames  (~158 MB)
    (*) a hard cap of 128 frames prevents extreme caching on tiny resolutions.
    """

    def __init__(self, frame_w: int, frame_h: int):
        bytes_per_frame = max(1, frame_w * frame_h * 3)
        budget_bytes    = _CACHE_BUDGET_MB * 1024 * 1024
        self._max: int  = max(8, min(128, budget_bytes // bytes_per_frame))
        self._store: OrderedDict[int, np.ndarray] = OrderedDict()

    # ------------------------------------------------------------------

    def get(self, idx: int) -> "np.ndarray | None":
        frame = self._store.get(idx)
        if frame is not None:
            self._store.move_to_end(idx)   # mark as recently used
        return frame

    def put(self, idx: int, frame: np.ndarray):
        if idx in self._store:
            self._store.move_to_end(idx)
            return
        self._store[idx] = frame
        if len(self._store) > self._max:
            self._store.popitem(last=False)  # evict least-recently-used

    def clear(self):
        self._store.clear()


class VideoPlayer:
    """
    Wraps an OpenCV VideoCapture with editing metadata.

    Usage:
        p = VideoPlayer()
        if p.load("/path/to/clip.mp4"):
            pixmap = p.get_frame_pixmap(0)
    """

    def __init__(self):
        self._cap         = None
        self._path        = ""
        self._fps         = 25.0
        self._frame_count = 0
        self._width       = 0
        self._height      = 0
        self._trim_in     = 0
        self._trim_out    = 0
        self._cuts: list[tuple[int, int]] = []
        self._reversed    = False
        self._last_read   = -1   # track last frame read for sequential optimisation
        self._cache: FrameCache | None = None

    # ------------------------------------------------------------------
    # Load / release
    # ------------------------------------------------------------------

    def load(self, path: str) -> bool:
        """Open a video file.  Returns False if the file cannot be opened."""
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return False
        fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fc <= 0:
            cap.release()
            return False

        # Release any previously loaded video
        self.release()

        self._cap         = cap
        self._path        = path
        self._fps         = cap.get(cv2.CAP_PROP_FPS) or 25.0
        self._frame_count = fc
        self._width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._trim_in     = 0
        self._trim_out    = fc - 1
        self._cuts        = []
        self._reversed    = False
        self._last_read   = -1
        self._cache       = FrameCache(self._width, self._height)
        return True

    def release(self):
        """Release the underlying VideoCapture and drop the frame cache."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._last_read = -1
        if self._cache is not None:
            self._cache.clear()
            self._cache = None

    def is_loaded(self) -> bool:
        return self._cap is not None

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------

    def get_frame_pixmap(self, frame_idx: int) -> QPixmap | None:
        """Return frame_idx as a QPixmap (RGB), or None on error."""
        frame = self._read_frame(frame_idx)
        if frame is None:
            return None
        return self._bgr_to_pixmap(frame)

    def get_frame_ndarray(self, frame_idx: int) -> np.ndarray | None:
        """Return frame_idx as a BGR numpy array, or None on error."""
        return self._read_frame(frame_idx)

    def _read_frame(self, frame_idx: int) -> np.ndarray | None:
        if not self.is_loaded():
            return None
        frame_idx = max(0, min(frame_idx, self._frame_count - 1))

        # Cache hit — return immediately without touching OpenCV
        if self._cache is not None:
            cached = self._cache.get(frame_idx)
            if cached is not None:
                return cached

        # Cache miss — decode from disk
        # Skip the expensive seek when reading the next sequential frame
        if frame_idx != self._last_read + 1:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_idx))
        ret, frame = self._cap.read()
        self._last_read = frame_idx if ret else -1

        if ret and self._cache is not None:
            self._cache.put(frame_idx, frame)

        return frame if ret else None

    # ------------------------------------------------------------------
    # Properties (read-only)
    # ------------------------------------------------------------------

    @property
    def path(self) -> str:        return self._path
    @property
    def fps(self) -> float:       return self._fps
    @property
    def frame_count(self) -> int: return self._frame_count
    @property
    def width(self) -> int:       return self._width
    @property
    def height(self) -> int:      return self._height
    @property
    def trim_in(self) -> int:     return self._trim_in
    @property
    def trim_out(self) -> int:    return self._trim_out
    @property
    def is_reversed(self) -> bool: return self._reversed
    @property
    def cuts(self) -> list[tuple[int, int]]: return list(self._cuts)

    @property
    def original_fourcc(self) -> str:
        """Four-character codec string of the source video."""
        if not self.is_loaded():
            return 'mp4v'
        v = int(self._cap.get(cv2.CAP_PROP_FOURCC))
        return ''.join(chr((v >> i) & 0xFF) for i in (0, 8, 16, 24)).strip('\x00') or 'mp4v'

    def duration_seconds(self) -> float:
        return self._frame_count / self._fps if self._fps else 0.0

    # ------------------------------------------------------------------
    # Editing controls
    # ------------------------------------------------------------------

    def set_trim_in(self, frame: int):
        self._trim_in = max(0, min(frame, self._trim_out))

    def set_trim_out(self, frame: int):
        self._trim_out = max(self._trim_in, min(frame, self._frame_count - 1))

    def add_cut(self, start: int, end: int):
        """Mark the range [start, end] to be excluded from export."""
        self._cuts.append((min(start, end), max(start, end)))

    def clear_cuts(self):
        self._cuts.clear()

    def toggle_reverse(self):
        self._reversed = not self._reversed

    def reset_edits(self):
        """Reset trim, cuts, and reverse to defaults."""
        self._trim_in  = 0
        self._trim_out = self._frame_count - 1
        self._cuts.clear()
        self._reversed = False

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def get_export_frames(self) -> list[int]:
        """
        Return the ordered list of frame indices to render during export,
        after applying trim, cuts, and reverse.
        """
        cut_set: set[int] = set()
        for s, e in self._cuts:
            # Never let a single cut silently erase the entire video
            if (s <= self._trim_in and e >= self._trim_out):
                continue
            cut_set.update(range(s, e + 1))

        frames = [f for f in range(self._trim_in, self._trim_out + 1)
                  if f not in cut_set]
        if self._reversed:
            frames.reverse()
        return frames

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bgr_to_pixmap(frame: np.ndarray) -> QPixmap:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch  = frame_rgb.shape
        img = QImage(frame_rgb.tobytes(), w, h, ch * w,
                     QImage.Format.Format_RGB888)
        return QPixmap.fromImage(img)

    @staticmethod
    def qimage_to_bgr(img: QImage) -> np.ndarray:
        """Convert a QImage to a BGR numpy array for OpenCV."""
        img = img.convertToFormat(QImage.Format.Format_RGB888)
        w, h = img.width(), img.height()
        ptr  = img.bits()
        ptr.setsize(h * w * 3)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 3)).copy()
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
