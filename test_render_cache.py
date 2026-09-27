"""Cached drawing must stay pixel-identical through edit/undo-style mutations."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QImage, QPainter, QPainterPath
from PyQt6.QtWidgets import QApplication, QStyleOptionGraphicsItem
from bubble import BubbleItem, TAILED_STYLES, build_body_path, ink_stroke


class RenderCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def draw(self, bubble):
        image = QImage(640, 640, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.translate(320, 260)
        bubble.paint(painter, QStyleOptionGraphicsItem())
        painter.end()
        return image

    def assert_matches_uncached(self, bubble):
        actual = self.draw(bubble)
        with patch.object(bubble, '_build_body_path', side_effect=lambda:
                          build_body_path(bubble._style, bubble._body_rect,
                                          bubble._ink_seed)), \
             patch.object(bubble, '_outline_path',
                          side_effect=bubble._build_outline_path), \
             patch.object(bubble, '_cached_ink_stroke', side_effect=ink_stroke):
            expected = self.draw(bubble)
        self.assertEqual(actual, expected)

    def test_all_styles_and_tails_match_original_vectors_after_edits(self):
        bubble = BubbleItem(0, 0)
        for style in TAILED_STYLES:
            bubble.set_style(style)
            for tail in ('wedge', 'curved', 'line', 'dots', 'none'):
                with self.subTest(style=style, tail=tail):
                    bubble.set_tail_shape(tail)
                    bubble.set_tail_count(3)
                    self.assert_matches_uncached(bubble)
                    bubble._tail.setPos(130, 145)
                    bubble.set_tail_width(27)
                    bubble.set_border_width(4.5)
                    bubble.set_body_rect(QRectF(-125, -80, 250, 160))
                    self.assert_matches_uncached(bubble)
                    bubble._tail.setPos(-100, 160)
                    bubble.set_body_rect(QRectF(-110, -65, 220, 130))
                    bubble.set_tail_width(40)
                    bubble.set_border_width(2)
                    self.assert_matches_uncached(bubble)

    def test_unchanged_repaints_do_not_rebuild_paths(self):
        bubble = BubbleItem(0, 0, style='cloud')
        self.draw(bubble)
        with patch('bubble.build_body_path', wraps=build_body_path) as body, \
             patch('bubble.ink_stroke', wraps=ink_stroke) as stroke:
            for _ in range(10):
                self.draw(bubble)
            body.assert_not_called()
            stroke.assert_not_called()
        for width in range(1, 20):
            bubble.set_border_width(width)
            self.draw(bubble)
        self.assertLessEqual(len(bubble._ink_path_cache), 4)

    def test_returned_paths_cannot_mutate_cache(self):
        bubble = BubbleItem(0, 0)
        for build in (bubble._build_body_path, bubble._outline_path):
            original = build()
            changed = build()
            changed.addRect(QRectF(1000, 1000, 50, 50))
            self.assertEqual(build(), original)
            self.assertNotEqual(build(), changed)

    def test_mouse_tail_drag_resize_and_undo_keep_drawing_current(self):
        from PyQt6.QtTest import QTest
        from canvas import PhotoScene, PhotoView
        from editor_controller import EditorController
        scene = PhotoScene()
        self.assertTrue(scene.load_photo('icons/icon_512.png'))
        scene.setSceneRect(QRectF(0, 0, 800, 600))
        controller = EditorController(scene)
        bubble = controller.add_bubble(400, 280, style='oval')
        view = PhotoView(scene)
        view.resize(900, 700)
        view.show()
        self.app.processEvents()
        try:
            def drag(handle):
                start = view.mapFromScene(handle.scenePos())
                end = start + QPoint(35, 25)
                QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
                QTest.mouseMove(view.viewport(), end, delay=20)
                QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
                self.app.processEvents()

            original = self.draw(bubble)
            tail = bubble._tail.pos()
            drag(bubble._tail)
            self.assertNotEqual(bubble._tail.pos(), tail)
            self.assertNotEqual(self.draw(bubble), original)
            self.assert_matches_uncached(bubble)
            rectangle = QRectF(bubble.body_rect)
            drag(bubble._handles['BR'])
            self.assertNotEqual(bubble.body_rect, rectangle)
            self.assert_matches_uncached(bubble)
            scene.undo_stack.undo()
            self.assertEqual(bubble.body_rect, rectangle)
            self.assert_matches_uncached(bubble)
            scene.undo_stack.redo()
            self.assert_matches_uncached(bubble)
        finally:
            view.close()


if __name__ == '__main__':
    unittest.main()
