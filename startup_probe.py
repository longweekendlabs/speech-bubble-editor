"""Opt-in first-paint measurement for source and frozen launch comparisons."""
import json
import os
from pathlib import Path
import sys
import time

from PyQt6.QtCore import QObject, QEvent, QTimer


class StartupProbe(QObject):
    def __init__(self, app, window, report_path):
        super().__init__(window)
        self.app, self.window = app, window
        self.report_path = report_path
        self.done = False
        window.installEventFilter(self)
        QTimer.singleShot(15000, self._timeout)

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QEvent.Type.Paint and not self.done:
            self.done = True
            # Return to the event loop after painting, then record completion.
            QTimer.singleShot(0, self._complete)
        return False

    def _complete(self):
        painted = time.perf_counter_ns()
        launched = os.environ.get('SBE_LAUNCH_STARTED_NS')
        data = {'ok': True, 'qt_platform': self.app.platformName(),
                'launch_to_first_paint_ms': ((painted - int(launched)) / 1e6
                                              if launched else None),
                'video_imported_on_launch': 'cv2' in sys.modules}
        Path(self.report_path).write_text(json.dumps(data, indent=2), encoding='utf-8')
        self.window.close()
        self.app.exit(0)

    def _timeout(self):
        if not self.done:
            self.app.exit(1)
