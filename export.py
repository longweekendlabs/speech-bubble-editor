"""
export.py — Export logic for both photos and videos.

Photo export:  renders bubbles at full source resolution → PNG/JPEG/WebP.
Video export:  renders each export frame with bubbles via OpenCV, then
               muxes original audio back in with FFmpeg (if available).
"""

import os
import shutil
import subprocess
from datetime import datetime

import cv2
import numpy as np

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QApplication

from video_player import VideoPlayer


# ---------------------------------------------------------------------------
# Photo export
# ---------------------------------------------------------------------------

def export_photo(parent, scene, photo_item, right_photo_item=None, is_dual=False):
    """
    Export the current scene to a full-resolution image file.

    In single mode: renders left photo at full resolution with bubbles.
    In dual mode:   side-by-side composite of left + right at their native sizes.
    """
    if photo_item is None or photo_item.pixmap().isNull():
        QMessageBox.warning(parent, "Export", "No photo loaded.")
        return

    src_path = getattr(photo_item, '_source_path', '')
    base = os.path.splitext(os.path.basename(src_path))[0] if src_path else "photo"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_name = f"{base}-{timestamp}.png"

    path, _ = QFileDialog.getSaveFileName(
        parent, "Export Photo", default_name,
        "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp)"
    )
    if not path:
        return

    if is_dual and right_photo_item and not right_photo_item.pixmap().isNull():
        _export_dual_photo(parent, scene, photo_item, right_photo_item, path)
    else:
        _export_single_photo(parent, scene, photo_item, path)


def _export_single_photo(parent, scene, photo_item, path):
    # Use display dimensions (WYSIWYG)
    W = int(photo_item.display_w)
    H = int(photo_item.display_h)

    image = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    scene_rect = photo_item.sceneBoundingRect()
    scene.render(painter, QRectF(0, 0, W, H), scene_rect)
    painter.end()

    _save_image(parent, image, path)


def _export_dual_photo(parent, scene, left_item, right_item, path):
    LW = int(left_item.display_w)
    LH = int(left_item.display_h)
    RW = int(right_item.display_w)
    RH = int(right_item.display_h)
    W  = LW + RW
    H  = max(LH, RH)

    image = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    lr = left_item.sceneBoundingRect()
    scene.render(painter, QRectF(0, 0, LW, LH), lr)
    rr = right_item.sceneBoundingRect()
    scene.render(painter, QRectF(LW, 0, RW, RH), rr)

    painter.end()
    _save_image(parent, image, path)


def _save_image(parent, image: QImage, path: str):
    ext = os.path.splitext(path)[1].lower()
    quality = -1
    if ext in ('.jpg', '.jpeg'):
        quality = 95
    ok = image.save(path, quality=quality)
    if ok:
        QMessageBox.information(parent, "Export", f"Saved to:\n{path}")
    else:
        QMessageBox.critical(parent, "Export", f"Failed to save:\n{path}")


# ---------------------------------------------------------------------------
# Video export
# ---------------------------------------------------------------------------

def export_video(parent, scene, photo_item, player: VideoPlayer,
                 right_photo_item=None, right_player: VideoPlayer | None = None,
                 is_dual=False):
    """
    Export the current video with speech bubbles rendered on each frame.
    Uses OpenCV for frame rendering and FFmpeg for audio muxing.
    """
    # At least one player must be loaded
    active = player if (player and player.is_loaded()) else right_player
    if active is None or not active.is_loaded():
        QMessageBox.warning(parent, "Export", "No video loaded.")
        return

    src_path = active.path
    base = os.path.splitext(os.path.basename(src_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_name = f"{base}-{timestamp}.mp4"

    out_path, _ = QFileDialog.getSaveFileName(
        parent, "Export Video", default_name,
        "MP4 (*.mp4);;AVI (*.avi);;MKV (*.mkv)"
    )
    if not out_path:
        return

    # Determine the "driver" player (the one that provides frame count / fps)
    driver = player if (player and player.is_loaded()) else right_player

    if is_dual and right_player and right_player.is_loaded():
        _export_dual_video(parent, scene, photo_item, player,
                           right_photo_item, right_player, out_path)
    elif driver and driver.is_loaded():
        _export_single_video(parent, scene, photo_item, driver, out_path)
    else:
        QMessageBox.warning(parent, "Export", "No video player available.")
        return


def _prerender_bubble_overlay(scene, photo_item, W: int, H: int) -> np.ndarray:
    """
    Render the bubble layer ONCE to a BGRA numpy array (H × W × 4, BGRA order).

    Bubbles are static — they don't change between video frames — so we render
    them a single time and reuse the result for every frame instead of calling
    QPainter+scene.render for every frame.
    """
    photo_item.setVisible(False)

    overlay = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    overlay.fill(0)
    painter = QPainter(overlay)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    scene.render(painter, QRectF(0, 0, W, H), photo_item.sceneBoundingRect())
    painter.end()

    photo_item.setVisible(True)

    overlay = overlay.convertToFormat(QImage.Format.Format_ARGB32)
    ptr = overlay.bits()
    ptr.setsize(H * W * 4)
    return np.frombuffer(ptr, dtype=np.uint8).reshape((H, W, 4)).copy()


def _composite(frame_bgr: np.ndarray, overlay_bgra: np.ndarray) -> np.ndarray:
    """Alpha-composite a pre-rendered bubble overlay onto a BGR video frame."""
    alpha      = overlay_bgra[:, :, 3:4] / 255.0
    overlay_bgr = overlay_bgra[:, :, :3].astype(np.float32)
    base_bgr    = frame_bgr.astype(np.float32)
    return (base_bgr * (1 - alpha) + overlay_bgr * alpha).clip(0, 255).astype(np.uint8)


def _export_single_video(parent, scene, photo_item, player: VideoPlayer, out_path: str):
    frames = player.get_export_frames()
    if not frames:
        QMessageBox.warning(parent, "Export", "No frames to export after trimming/cuts.")
        return

    # Use the canvas display dimensions for a WYSIWYG export.
    # Ensure codec-friendly even dimensions.
    W   = int(photo_item.display_w)
    H   = int(photo_item.display_h)
    W   = W if W % 2 == 0 else W + 1
    H   = H if H % 2 == 0 else H + 1
    fps = player.fps

    # Pre-render bubble overlay once — bubbles are static across all frames.
    bubble_overlay = _prerender_bubble_overlay(scene, photo_item, W, H)

    progress = QProgressDialog("Exporting video…", "Cancel", 0, len(frames), parent)
    progress.setWindowTitle("Exporting")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)

    tmp_video = out_path + ".tmp_noaudio.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(tmp_video, fourcc, fps, (W, H))

    cancelled = False
    try:
        for i, frame_idx in enumerate(frames):
            if progress.wasCanceled():
                cancelled = True
                break

            frame = player.get_frame_ndarray(frame_idx)
            if frame is not None:
                if frame.shape[1] != W or frame.shape[0] != H:
                    frame = cv2.resize(frame, (W, H))
                writer.write(_composite(frame, bubble_overlay))

            progress.setValue(i + 1)
            QApplication.processEvents()
    finally:
        writer.release()
        progress.close()

    if cancelled:
        _safe_remove(tmp_video)
        return

    _mux_audio(player.path, tmp_video, out_path, frames, fps)
    _safe_remove(tmp_video)

    QMessageBox.information(parent, "Export", f"Video saved to:\n{out_path}")


def _pixmap_to_bgr(pixmap, w: int, h: int) -> np.ndarray:
    """
    Scale a QPixmap to (w × h) and return as a BGR numpy array.
    Used when one side is a static photo during dual video export.
    """
    img = pixmap.scaled(w, h,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                        ).toImage()
    img = img.convertToFormat(QImage.Format.Format_RGB888)
    ptr = img.bits()
    ptr.setsize(h * w * 3)
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 3)).copy()
    return arr[:, :, ::-1]  # RGB → BGR


def _export_dual_video(parent, scene, left_item, left_player: VideoPlayer,
                       right_item, right_player: VideoPlayer, out_path: str):
    """
    Dual video export.  Either side may be a static photo (player=None).
    The video side (or left if both are video) drives the frame sequence.
    """
    left_has_video  = left_player is not None and left_player.is_loaded()
    right_has_video = right_player is not None and right_player.is_loaded()

    # Pick the driver: prefer left video, fall back to right video
    driver = left_player if left_has_video else right_player
    if driver is None or not driver.is_loaded():
        QMessageBox.warning(parent, "Export", "No video found for dual export.")
        return

    frames = driver.get_export_frames()
    if not frames:
        QMessageBox.warning(parent, "Export", "No frames to export.")
        return

    LW  = int(left_item.display_w)
    LH  = int(left_item.display_h)
    LW  = LW if LW % 2 == 0 else LW + 1
    LH  = LH if LH % 2 == 0 else LH + 1
    fps = driver.fps

    # Determine output dimensions for the right panel (WYSIWYG: use canvas display size)
    if right_has_video:
        RH_src = right_player.height   # only needed to fetch frames
        RW_src = right_player.width
    if right_item is not None:
        RW_out = int(right_item.display_w)
        RW_out = RW_out if RW_out % 2 == 0 else RW_out + 1
    elif right_has_video:
        scale  = LH / RH_src if RH_src else 1.0
        RW_out = max(1, int(RW_src * scale))
        RW_out = RW_out if RW_out % 2 == 0 else RW_out + 1
    else:
        RW_out = LW  # fallback

    W, H = LW + RW_out, LH

    # Pre-render static sides once (photo stays the same every frame)
    static_left_bgr  = None if left_has_video  else _pixmap_to_bgr(left_item.pixmap(),  LW, LH)
    static_right_bgr = None
    if not right_has_video and right_item is not None:
        raw = _pixmap_to_bgr(right_item.pixmap(),
                             int(right_item.display_w),
                             int(right_item.display_h))
        static_right_bgr = cv2.resize(raw, (RW_out, LH))

    # Pre-render bubble overlay for the left panel once (bubbles are static).
    left_overlay = _prerender_bubble_overlay(scene, left_item, LW, LH)

    progress = QProgressDialog("Exporting dual video…", "Cancel", 0, len(frames), parent)
    progress.setWindowTitle("Exporting")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)

    tmp_video = out_path + ".tmp_noaudio.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(tmp_video, fourcc, fps, (W, H))

    right_total = right_player.frame_count if right_has_video else 0

    cancelled = False
    try:
        for i, frame_idx in enumerate(frames):
            if progress.wasCanceled():
                cancelled = True
                break

            # --- Left panel ---
            if left_has_video:
                left_frame = left_player.get_frame_ndarray(frame_idx)
                if left_frame is None:
                    left_frame = np.zeros((LH, LW, 3), dtype=np.uint8)
                if left_frame.shape[1] != LW or left_frame.shape[0] != LH:
                    left_frame = cv2.resize(left_frame, (LW, LH))
                left_rendered = _composite(left_frame, left_overlay)
            else:
                left_rendered = _composite(static_left_bgr.copy(), left_overlay)

            # --- Right panel ---
            if right_has_video:
                right_idx   = min(frame_idx, right_total - 1)
                right_frame = right_player.get_frame_ndarray(right_idx)
                if right_frame is None:
                    right_frame = np.zeros((RH_src, RW_src, 3), dtype=np.uint8)
                right_scaled = cv2.resize(right_frame, (RW_out, LH))
            elif static_right_bgr is not None:
                right_scaled = static_right_bgr
            else:
                right_scaled = np.zeros((LH, RW_out, 3), dtype=np.uint8)

            writer.write(np.hstack([left_rendered, right_scaled]))
            progress.setValue(i + 1)
            QApplication.processEvents()
    finally:
        writer.release()
        progress.close()

    if cancelled:
        _safe_remove(tmp_video)
        return

    _mux_audio(driver.path, tmp_video, out_path, frames, fps)
    _safe_remove(tmp_video)

    QMessageBox.information(parent, "Export", f"Dual video saved to:\n{out_path}")


# ---------------------------------------------------------------------------
# FFmpeg audio muxing
# ---------------------------------------------------------------------------

def _mux_audio(src_video: str, rendered_video: str, out_path: str,
               export_frames: list[int], fps: float):
    """
    Attempt to mux audio from src_video into rendered_video → out_path.
    Falls back to just renaming rendered_video if FFmpeg is unavailable.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        shutil.move(rendered_video, out_path)
        return

    # Calculate start time offset based on first export frame
    start_frame = export_frames[0] if export_frames else 0
    start_time = start_frame / fps if fps else 0.0

    cmd = [
        ffmpeg, "-y",
        "-i", rendered_video,
        "-ss", str(start_time),
        "-i", src_video,
        "-map", "0:v:0",
        "-map", "1:a:0?",   # ? makes audio optional (no error if no audio stream)
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-shortest",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # FFmpeg failed — just use the video without audio
        shutil.move(rendered_video, out_path)


def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
