"""Measure import latency and UI heartbeat stalls for a real media file.

Use --synchronous to compare the original GUI-thread import path. Run each
sample in a fresh process to include first-use video dependency loading.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

parser = argparse.ArgumentParser()
parser.add_argument('path')
parser.add_argument('--synchronous', action='store_true')
args = parser.parse_args()
app = QApplication([])
window = MainWindow()
window.show()
last_tick = None
max_gap = 0.0
started = None
elapsed = None
error = None

def beat():
    global last_tick, max_gap
    now = time.perf_counter()
    if last_tick is not None:
        max_gap = max(max_gap, now - last_tick)
    last_tick = now

def finished(*_args):
    global elapsed
    elapsed = time.perf_counter() - started
    QTimer.singleShot(60, app.quit)

def failed(*details):
    global error
    error = str(details)
    finished()

def begin():
    global started, last_tick
    started = last_tick = time.perf_counter()
    if args.synchronous:
        if not window.controller.open_media(args.path):
            failed(window.controller.last_error)
    else:
        window.controller.import_failed.connect(failed)
        window.controller.open_media_async(args.path)

window.controller.media_loaded.connect(finished)
timer = QTimer()
timer.timeout.connect(beat)
timer.start(5)
QTimer.singleShot(400, begin)
QTimer.singleShot(30000, lambda: failed('import timed out'))
app.exec()
window.scene.reset_project()
window.close()
print(json.dumps({'path': args.path, 'synchronous': args.synchronous,
                  'import_ms': round(elapsed * 1000, 2) if elapsed else None,
                  'max_ui_heartbeat_gap_ms': round(max_gap * 1000, 2),
                  'error': error}, indent=2))
if error:
    raise SystemExit(1)
