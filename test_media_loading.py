"""Import responsiveness, ownership and stale-result regression checks."""
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from canvas import PhotoScene
from editor_controller import EditorController
from media_loader import MediaLoader, PreparedMedia, decode_media
from video_player import FrameDecodeWorker


class MediaLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp = tempfile.TemporaryDirectory()
        cls.photo = str(Path(cls.temp.name) / 'photo.png')
        image = QImage(1200, 800, QImage.Format.Format_RGB32)
        image.fill(QColor('#123456'))
        assert image.save(cls.photo)
        import cv2
        import numpy as np
        cls.video = str(Path(cls.temp.name) / 'video.mp4')
        writer = cv2.VideoWriter(cls.video, cv2.VideoWriter_fourcc(*'mp4v'), 10, (160, 120))
        assert writer.isOpened()
        for color in (50, 120, 220):
            writer.write(np.full((120, 160, 3), color, dtype=np.uint8))
        writer.release()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.scene = PhotoScene()
        self.controller = EditorController(self.scene)

    def tearDown(self):
        self.controller.shutdown()
        self.app.processEvents()
        self.scene.reset_project()

    def wait_for(self, predicate):
        deadline = time.monotonic() + 5
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(predicate(), 'Timed out waiting for worker completion')

    def test_photo_decodes_on_worker_and_installs_full_size_on_gui(self):
        workers, receivers = [], []
        def decode(path):
            workers.append(QThread.currentThread() != self.app.thread())
            return decode_media(path)
        self.controller.media_loaded.connect(
            lambda *_: receivers.append(QThread.currentThread() == self.app.thread()))
        with patch('media_loader.decode_media', side_effect=decode):
            self.controller.open_media_async(self.photo)
            self.wait_for(lambda: bool(receivers))
        self.assertEqual(workers, [True])
        self.assertEqual(receivers, [True])
        image = self.scene._photo_item.pixmap().toImage()
        self.assertEqual((image.width(), image.height()), (1200, 800))
        self.assertEqual(image.pixelColor(10, 10).name(), '#123456')

    def test_latest_request_wins_without_parallel_decoders(self):
        loader = MediaLoader()
        entered, release = threading.Event(), threading.Event()
        decoded, accepted, disposed = [], [], []
        class Player:
            def release(self):
                disposed.append(True)
        def decode(path):
            decoded.append(path)
            if path == 'first':
                entered.set()
                release.wait(5)
                return PreparedMedia(QImage(1, 1, QImage.Format.Format_RGB32), Player())
            return PreparedMedia(QImage(2, 2, QImage.Format.Format_RGB32))
        loader.ready.connect(lambda path, *_: accepted.append(path))
        try:
            with patch('media_loader.decode_media', side_effect=decode):
                loader.request('first')
                self.wait_for(entered.is_set)
                loader.request('middle')
                loader.request('latest')
                QTest.qWait(30)  # GUI events continue while the decoder waits.
                self.assertEqual(decoded, ['first'])
                release.set()
                self.wait_for(lambda: accepted == ['latest'])
                self.assertEqual(decoded, ['first', 'latest'])
                self.assertEqual(disposed, [True])
        finally:
            release.set()
            loader.shutdown()

    def test_failed_import_preserves_existing_photo(self):
        self.assertTrue(self.controller.open_media(self.photo))
        key = self.scene._photo_item.pixmap().cacheKey()
        errors = []
        self.controller.import_failed.connect(lambda *args: errors.append(args))
        self.controller.open_media_async(str(Path(self.temp.name) / 'missing.jpg'))
        self.wait_for(lambda: bool(errors))
        self.assertEqual(self.scene._photo_item.pixmap().cacheKey(), key)
        self.assertEqual(self.controller.model.media_path, self.photo)

    def test_reset_discards_late_import(self):
        entered, release = threading.Event(), threading.Event()
        def decode(path):
            entered.set()
            release.wait(5)
            return decode_media(path)
        try:
            with patch('media_loader.decode_media', side_effect=decode):
                self.controller.open_media_async(self.photo)
                self.wait_for(entered.is_set)
                self.controller.reset_project()
                release.set()
                self.wait_for(lambda: self.controller._loader._job is None)
                self.assertFalse(self.scene.has_photo())
        finally:
            release.set()

    def test_async_video_and_overlay_retain_editing_support(self):
        loaded, overlays = [], []
        self.controller.media_loaded.connect(lambda *args: loaded.append(args))
        self.controller.overlay_loaded.connect(overlays.append)
        self.controller.open_media_async(self.video)
        self.wait_for(lambda: bool(loaded))
        self.assertTrue(loaded[0][1])
        player = self.scene.video_player
        self.assertEqual(player.frame_count, 3)
        self.assertEqual((player.width, player.height), (160, 120))
        player.set_trim_in(1)
        player.toggle_reverse()
        self.assertEqual(player.get_export_frames(), [2, 1])
        self.controller.open_media_async(self.photo, 'overlay')
        self.wait_for(lambda: bool(overlays))
        self.assertIn(overlays[0], self.scene.items())
        self.scene.undo_stack.undo()
        self.assertIsNone(overlays[0].scene())
        self.scene.undo_stack.redo()
        self.assertIs(overlays[0].scene(), self.scene)

    def test_stale_frames_do_not_overwrite_replacement_media(self):
        self.assertTrue(self.scene.load_video(self.video))
        old_generation = self.scene._decode_gen_left
        self.assertTrue(self.scene.load_video(self.video))
        self.assertNotEqual(self.scene._decode_gen_left, old_generation)
        key = self.scene._photo_item.pixmap().cacheKey()
        self.scene._on_left_frame_ready(old_generation, 0, QImage(self.photo))
        self.assertEqual(self.scene._photo_item.pixmap().cacheKey(), key)
        self.assertTrue(self.scene.load_photo(self.photo))
        key = self.scene._photo_item.pixmap().cacheKey()
        self.scene._on_left_frame_ready(old_generation, 0, QImage(self.photo))
        self.assertEqual(self.scene._photo_item.pixmap().cacheKey(), key)
        self.scene.enable_dual_mode()
        self.assertTrue(self.scene.load_right_video(self.video))
        old_player = self.scene.video_player_right
        old_generation = self.scene._decode_gen_right
        self.assertTrue(self.scene.load_right_photo(self.photo))
        self.assertFalse(old_player.is_loaded())
        self.assertIsNone(self.scene.video_player_right)
        key = self.scene._photo_item_right.pixmap().cacheKey()
        self.scene._on_right_frame_ready(old_generation, 0, QImage(self.photo))
        self.assertEqual(self.scene._photo_item_right.pixmap().cacheKey(), key)

    def test_pause_waits_for_active_decode_not_just_empty_queue(self):
        entered, finish, paused = threading.Event(), threading.Event(), threading.Event()
        class Player:
            def _read_frame(self, _index):
                entered.set()
                finish.wait(5)
                return None
        worker = FrameDecodeWorker(Player())
        worker._latest_idx = 0
        worker._in_flight = 1
        worker._idle.clear()
        decoding = threading.Thread(target=worker._decode)
        pausing = threading.Thread(target=lambda: (worker.pause(), paused.set()))
        decoding.start()
        try:
            self.assertTrue(entered.wait(2))
            pausing.start()
            self.assertFalse(paused.wait(0.05))
            finish.set()
            self.assertTrue(paused.wait(2))
        finally:
            finish.set()
            decoding.join()
            if pausing.ident is not None:
                pausing.join()


if __name__ == '__main__':
    unittest.main()
