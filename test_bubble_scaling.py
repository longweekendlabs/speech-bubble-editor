"""Regression tests for bubble sizing and zoom-independent edit handles."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication, QGraphicsItem

from canvas import PhotoScene
from editor_controller import EditorController
from main_window import MainWindow
from media_item import MediaItem
from top_bar import TopBar


_APP = QApplication.instance() or QApplication([])


class BubbleScalingTests(unittest.TestCase):

    def _bubble_for_canvas(self, width, height):
        scene = PhotoScene()
        scene.setSceneRect(QRectF(0, 0, width, height))
        controller = EditorController(scene)
        return controller.add_bubble(width / 2, height / 2, style="oval")

    def test_low_resolution_portrait_gets_compact_default_bubble(self):
        bubble = self._bubble_for_canvas(320, 400)
        self.assertLessEqual(bubble.body_rect.width() / 320, 0.25)
        self.assertLessEqual(bubble.body_rect.height() / 400, 0.18)

    def test_high_resolution_canvas_still_gets_visible_default_bubble(self):
        bubble = self._bubble_for_canvas(4000, 3000)
        self.assertGreaterEqual(bubble.body_rect.width() / 4000, 0.15)
        self.assertLessEqual(bubble.body_rect.width() / 4000, 0.21)

    def test_edit_handles_ignore_view_zoom(self):
        bubble = self._bubble_for_canvas(320, 400)
        flag = QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
        self.assertTrue(bubble._tail.flags() & flag)
        self.assertTrue(all(handle.flags() & flag
                            for handle in bubble._handles.values()))

    def test_brand_byline_cannot_compress_and_clip(self):
        top_bar = TopBar()
        required = top_bar._byline.fontMetrics().horizontalAdvance(
            top_bar._byline.text())
        self.assertGreaterEqual(top_bar._byline.minimumWidth(), required)

    def test_selection_does_not_resize_or_refit_canvas(self):
        window = MainWindow()
        window.resize(1280, 800)
        window.show()
        _APP.processEvents()

        pixmap = QPixmap(320, 400)
        pixmap.fill(QColor("#808080"))
        media = MediaItem(pixmap)
        window.scene._photo_item = media
        window.scene.addItem(media)
        window.scene.setSceneRect(QRectF(0, 0, 320, 400))
        window.view.fit_photo()
        _APP.processEvents()

        viewport_height = window.view.viewport().height()
        fitted_scale = window.view.transform().m11()
        window.controller.add_bubble(160, 200, style="oval")
        _APP.processEvents()
        self.assertTrue(window.ctx_toolbar.isVisible())
        self.assertEqual(window.view.viewport().height(), viewport_height)
        self.assertAlmostEqual(window.view.transform().m11(), fitted_scale)

        window.scene.clearSelection()
        _APP.processEvents()
        self.assertTrue(window.ctx_toolbar.isVisible())
        self.assertEqual(window.view.viewport().height(), viewport_height)
        self.assertAlmostEqual(window.view.transform().m11(), fitted_scale)
        window.close()


if __name__ == "__main__":
    unittest.main()
