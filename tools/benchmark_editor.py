"""Repeatable source benchmark; run from the repository root with Python.

Uses offscreen Qt by default. Times real scene rendering, not a mocked paint
method. Output is JSON; compare on the same machine and dependency versions.
"""
import json
import os
from pathlib import Path
import statistics
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SBE_DISABLE_SAVED_COLLAGE_DEFAULTS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
start = time.perf_counter()

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFontDatabase, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet((ROOT / "theme/dark.qss").read_text())
from main_window import MainWindow

window = MainWindow()
window.show()
app.processEvents()
first_paint = time.perf_counter() - start
for font in sorted((ROOT / "fonts").glob("*.ttf")):
    QFontDatabase.addApplicationFont(str(font))
app.processEvents()
ready = time.perf_counter() - start

from media_item import MediaItem
photo = QPixmap(3840, 2160)
photo.fill(QColor("#63758a"))
item = MediaItem(photo)
window.scene._photo_item = item
window.scene.addItem(item)
window.scene.setSceneRect(QRectF(photo.rect()))
styles = ("oval", "cloud", "wobbly", "burst")
for n in range(16):
    bubble = window.controller.add_bubble(450 + (n % 4) * 900,
                                          260 + (n // 4) * 530,
                                          style=styles[n % len(styles)])
    bubble.set_text("A speech bubble")
window.scene.clearSelection()
window.view.fit_photo()
app.processEvents()

image = QImage(1280, 720, QImage.Format.Format_ARGB32_Premultiplied)

def render():
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    window.scene.render(painter, QRectF(image.rect()), window.scene.sceneRect())
    painter.end()

render()
samples = []
for _ in range(30):
    tick = time.perf_counter()
    render()
    samples.append((time.perf_counter() - tick) * 1000)

print(json.dumps({
    "platform": sys.platform,
    "qt_platform": app.platformName(),
    "first_paint_ms": round(first_paint * 1000, 2),
    "fonts_ready_ms": round(ready * 1000, 2),
    "scene_render_median_ms": round(statistics.median(samples), 2),
    "scene_render_max_ms": round(max(samples), 2),
    "scene": "4K photo, 16 bubbles, 1280x720 render, 30 repaints",
    "video_imported_on_launch": "cv2" in sys.modules,
}, indent=2))
window.close()
