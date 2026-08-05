"""Focused regression tests for the experimental Manga Maker mode."""

import os
import random
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SBE_DISABLE_SAVED_COLLAGE_DEFAULTS", "1")

from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from canvas import PhotoScene, PhotoView
from collage_maker import (
    ASPECT_RATIOS, COLLAGE_COUNTS, LAYOUT_TYPES, generate_collage_layout,
)
from manga_maker import PAGE_HEIGHT, PAGE_WIDTH, PANEL_COUNTS, generate_layout
from inspector_dock import (
    CollageTemplateStrip, InspectorDock, OptionButtonGrid, PhotoCountStepper,
)
from main_window import MainWindow
from tool_sidebar import ToolSidebar
from speedlines import SpeedLinesItem
from redaction import RedactionItem


class MangaLayoutTests(unittest.TestCase):

    def test_seeded_layouts_stay_on_page_and_do_not_overlap(self):
        for count in PANEL_COUNTS:
            for seed in range(50):
                rects, _, actual = generate_layout(count, random.Random(seed))
                self.assertEqual(actual, count)
                self.assertEqual(len(rects), count)
                for index, rect in enumerate(rects):
                    self.assertGreaterEqual(rect.left(), 0)
                    self.assertGreaterEqual(rect.top(), 0)
                    self.assertLessEqual(rect.right(), PAGE_WIDTH + 0.01)
                    self.assertLessEqual(rect.bottom(), PAGE_HEIGHT + 0.01)
                    for other in rects[index + 1:]:
                        self.assertFalse(rect.intersects(other))

    def test_shape_options_control_composition_and_reading_order(self):
        options = {
            "composition": "Balanced",
            "margin": 40,
            "row_gutter": 24,
            "column_gutter": 12,
            "variation": 20,
            "reading_direction": "Right to left",
        }
        rects, name, count = generate_layout(
            6, random.Random(7), options=options)
        self.assertEqual(count, 6)
        self.assertIn("balanced", name)
        self.assertAlmostEqual(min(rect.left() for rect in rects), 40)
        # Balanced six-panel pages resolve to 2–2–2; right panel is first.
        self.assertGreater(rects[0].left(), rects[1].left())


class MangaSceneTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_regeneration_preserves_loaded_images(self):
        scene = PhotoScene()
        self.assertTrue(scene.load_photo("icons/icon_512.png"))
        source = scene._photo_item
        scene.enable_manga_mode()
        self.assertTrue(scene.is_manga_mode())
        self.assertFalse(source.isVisible())

        for index in range(len(scene._manga_panels)):
            self.assertTrue(scene.load_manga_panel(index, "icons/icon_256.png"))
        loaded = len(scene._manga_panels)

        for _ in range(12):
            scene.regenerate_manga_layout()
            self.assertGreaterEqual(len(scene._manga_panels), loaded)
            self.assertEqual(
                sum(panel.has_image() for panel in scene._manga_panels), loaded)

        scene.disable_manga_mode()
        self.assertFalse(scene.is_manga_mode())
        self.assertTrue(source.isVisible())

    def test_blank_page_entry_scale_and_theme(self):
        scene = PhotoScene()
        scene.enable_manga_mode()
        self.assertTrue(scene.is_manga_mode())
        self.assertIsNone(scene._photo_item)
        self.assertIn(len(scene._manga_panels), PANEL_COUNTS)

        self.assertTrue(scene.load_manga_panel(0, "icons/icon_512.png"))
        scene._manga_panels[0].set_zoom_percent(100)
        scene._manga_panels[0].zoom_image(1 / 1.10)
        self.assertLess(scene._manga_panels[0].zoom_percent(), 100)
        scene.set_selected_manga_zoom(175)
        self.assertEqual(scene._manga_panels[0].zoom_percent(), 175)
        scene.set_selected_manga_zoom(35)
        self.assertEqual(scene._manga_panels[0].zoom_percent(), 35)
        scene.fit_selected_manga_panel()
        self.assertLessEqual(scene._manga_panels[0].zoom_percent(), 100)
        scene.set_manga_style("image_background", "solid")
        self.assertEqual(scene.manga_style()["image_background"], "solid")
        self.assertFalse(scene._manga_panels[0]._blurred_background().isNull())

        scene.apply_manga_theme("Noir")
        self.assertEqual(scene.manga_style()["page_color"].name(), "#171717")
        scene.disable_manga_mode()
        self.assertFalse(scene.has_photo())

    def test_layout_settings_and_safe_panel_count(self):
        scene = PhotoScene()
        scene.enable_manga_mode()
        scene.set_manga_layout_setting("panel_count", 6)
        scene.set_manga_layout_setting("composition", "Feature")
        scene.set_manga_layout_setting("show_numbers", True)
        scene.regenerate_manga_layout()
        self.assertEqual(len(scene._manga_panels), 6)
        self.assertTrue(all(panel._show_number for panel in scene._manga_panels))

        before = [panel.pos().x() for panel in scene._manga_panels]
        scene.set_manga_layout_setting("column_gutter", 55)
        after = [panel.pos().x() for panel in scene._manga_panels]
        self.assertNotEqual(before, after)

        for index in range(6):
            self.assertTrue(scene.load_manga_panel(index, "icons/icon_256.png"))
        scene.set_manga_layout_setting("panel_count", 4)
        scene.regenerate_manga_layout()
        self.assertEqual(len(scene._manga_panels), 6)
        self.assertEqual(sum(panel.has_image() for panel in scene._manga_panels), 6)


class CollageLayoutTests(unittest.TestCase):

    def test_every_layout_count_and_aspect_stays_inside_canvas(self):
        for layout_type in LAYOUT_TYPES:
            for aspect_name in ASPECT_RATIOS:
                for count in COLLAGE_COUNTS:
                    rects, _, page_size = generate_collage_layout(
                        count, layout_type,
                        {"aspect_ratio": aspect_name, "margin": 28, "gap": 18},
                        random.Random(19),
                    )
                    self.assertEqual(len(rects), count)
                    width, height = page_size
                    for index, rect in enumerate(rects):
                        self.assertGreater(rect.width(), 0)
                        self.assertGreater(rect.height(), 0)
                        self.assertGreaterEqual(rect.left(), 27.99)
                        self.assertGreaterEqual(rect.top(), 27.99)
                        self.assertLessEqual(rect.right(), width - 27.99)
                        self.assertLessEqual(rect.bottom(), height - 27.99)
                        for other in rects[index + 1:]:
                            self.assertFalse(rect.intersects(other))


class CollageSceneTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_blank_entry_live_layout_and_primary_colors(self):
        scene = PhotoScene()
        scene.enable_collage_mode()
        self.assertTrue(scene.is_collage_mode())
        self.assertFalse(scene.is_manga_mode())
        self.assertEqual(len(scene._manga_panels), 4)
        self.assertEqual(scene.collage_style()["page_color"].name(), "#111318")

        scene.set_collage_layout_setting("aspect_ratio", "Portrait · 4:5")
        self.assertAlmostEqual(scene.sceneRect().width() / scene.sceneRect().height(),
                               4 / 5, places=3)
        before = [panel.sceneBoundingRect() for panel in scene._manga_panels]
        scene.set_collage_layout_setting("gap", 70)
        after = [panel.sceneBoundingRect() for panel in scene._manga_panels]
        self.assertNotEqual(before, after)

        scene.apply_collage_theme("Midnight")
        self.assertEqual(scene.collage_style()["page_color"].name(), "#111318")
        scene.set_collage_style("border_color", "#ff3366")
        scene.set_collage_style("border_width", 12)
        self.assertEqual(scene.collage_style()["border_color"].name(), "#ff3366")
        self.assertEqual(scene.collage_style()["border_width"], 12)

    def test_count_change_and_regenerate_preserve_loaded_images(self):
        scene = PhotoScene()
        scene.enable_collage_mode()
        for index in range(4):
            self.assertTrue(scene.load_manga_panel(index, "icons/icon_256.png"))
        scene.set_collage_layout_setting("photo_count", 7)
        self.assertEqual(len(scene._manga_panels), 7)
        self.assertEqual(sum(panel.has_image() for panel in scene._manga_panels), 4)
        scene.set_collage_layout_setting("photo_count", 2)
        self.assertEqual(len(scene._manga_panels), 4)
        self.assertEqual(scene.collage_layout_settings()["photo_count"], 4)
        self.assertEqual(sum(panel.has_image() for panel in scene._manga_panels), 4)
        scene.regenerate_collage_layout()
        self.assertEqual(sum(panel.has_image() for panel in scene._manga_panels), 4)

    def test_shuffle_changes_template_and_preserves_loaded_images(self):
        scene = PhotoScene()
        scene.enable_collage_mode()
        for index in range(4):
            self.assertTrue(scene.load_manga_panel(index, "icons/icon_256.png"))
        before = scene.collage_layout_settings()["layout_type"]
        scene.shuffle_collage_layout()
        self.assertNotEqual(scene.collage_layout_settings()["layout_type"],
                            before)
        self.assertEqual(sum(panel.has_image() for panel in scene._manga_panels),
                         4)


class PageOptionButtonTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_page_choices_are_buttons_and_update_live_modes(self):
        scene = PhotoScene()
        inspector = InspectorDock()
        inspector.set_scene(scene)

        scene.enable_collage_mode()
        inspector.show_manga_settings()
        self.assertIsInstance(inspector._collage_layout_type,
                              CollageTemplateStrip)
        inspector._collage_layout_type.option_button("Hero").click()
        inspector._collage_orientation.click()
        self.assertEqual(scene.collage_layout_settings()["layout_type"], "Hero")
        self.assertEqual(scene.collage_layout_settings()["aspect_ratio"],
                         "Landscape · 16:9")

        scene.disable_collage_mode()
        scene.enable_manga_mode()
        inspector.show_manga_settings()
        self.assertIsInstance(inspector._manga_composition, OptionButtonGrid)
        inspector._manga_composition.option_button("Action").click()
        inspector._manga_direction.option_button("Left to right").click()
        self.assertEqual(scene.manga_layout_settings()["composition"], "Action")
        self.assertEqual(scene.manga_layout_settings()["reading_direction"],
                         "Left to right")

    def test_comic_palette_stays_on_fx_and_random_controls_are_not_duplicated(self):
        scene = PhotoScene()
        inspector = InspectorDock()
        inspector.set_scene(scene)
        scene.enable_manga_mode()
        inspector.show_manga_settings()

        inspector._show_tab(inspector.FX_TAB)
        inspector._manga_theme.option_button("Noir").click()
        self.assertEqual(inspector._tabs.currentIndex(), inspector.FX_TAB)
        self.assertEqual(scene.manga_style()["page_color"].name(), "#171717")
        self.assertIsNone(inspector._manga_panel_count.option_button("Random"))
        self.assertIsNone(inspector._manga_composition.option_button("Random"))
        self.assertEqual(
            inspector._comic_quick_preset.option_button("mixed").text(),
            "Mixed page")

    def test_start_here_controls_work_without_opening_fine_tune(self):
        scene = PhotoScene()
        inspector = InspectorDock()
        inspector.set_scene(scene)

        scene.enable_collage_mode()
        inspector.show_manga_settings()
        self.assertIsInstance(inspector._collage_count, PhotoCountStepper)
        inspector._collage_orientation.click()
        inspector._collage_count.setValue(7)
        self.assertEqual(scene.collage_layout_settings()["aspect_ratio"],
                         "Landscape · 16:9")
        self.assertEqual(scene.collage_layout_settings()["photo_count"], 7)

        scene.disable_collage_mode()
        scene.enable_manga_mode()
        inspector.show_manga_settings()
        self.assertTrue(inspector._manga_advanced.isHidden())
        inspector._comic_quick_preset.option_button("classic").click()
        self.assertEqual(scene.manga_layout_settings()["panel_count"], 6)
        self.assertEqual(scene.manga_layout_settings()["composition"],
                         "Balanced")

    def test_left_tool_is_named_comic(self):
        sidebar = ToolSidebar()
        self.assertEqual(sidebar._buttons["manga"].text(), "Comic")

    def test_collage_changes_always_refit_the_whole_page(self):
        window = MainWindow()
        window.resize(1200, 720)
        window.show()
        self.app.processEvents()
        try:
            window.tool_sidebar._buttons["collage"].click()
            window.props._collage_orientation.click()
            window.props._collage_count.setValue(9)
            window.props._collage_layout_type.option_button("Filmstrip").click()
            self.app.processEvents()

            mapped = window.view.mapFromScene(
                window.scene.sceneRect()).boundingRect()
            viewport = window.view.viewport().rect()
            self.assertTrue(window.view._fit_to_window)
            self.assertLessEqual(mapped.width(), viewport.width() + 2)
            self.assertLessEqual(mapped.height(), viewport.height() + 2)
        finally:
            window.close()


class PageMouseInteractionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _solid_pixmap(color: str) -> QPixmap:
        pixmap = QPixmap(80, 60)
        pixmap.fill(QColor(color))
        return pixmap

    def test_magnetic_drag_swaps_images_and_is_undoable_in_both_modes(self):
        for mode in ("comic", "collage"):
            scene = PhotoScene()
            if mode == "comic":
                scene.enable_manga_mode()
            else:
                scene.enable_collage_mode()
            source, target = scene._manga_panels[:2]
            source.set_pixmap(self._solid_pixmap("#ff0000"))
            target.set_pixmap(self._solid_pixmap("#0000ff"))

            self.assertEqual(scene.page_drag_mode(), "auto")
            self.assertFalse(scene.should_begin_panel_reorder(
                source, source.sceneBoundingRect().center()))
            outside = source.sceneBoundingRect().bottomRight() + QPointF(80, 80)
            self.assertTrue(scene.should_begin_panel_reorder(source, outside))
            self.assertTrue(scene.begin_panel_reorder(
                source, source.sceneBoundingRect().center()))
            scene.update_panel_reorder(
                source, target.sceneBoundingRect().center())
            self.assertTrue(target._drop_target)
            self.assertTrue(scene.finish_panel_reorder(
                source, target.sceneBoundingRect().center()))

            source_color = source.pixmap().toImage().pixelColor(0, 0).name()
            target_color = target.pixmap().toImage().pixelColor(0, 0).name()
            self.assertEqual((source_color, target_color),
                             ("#0000ff", "#ff0000"))
            self.assertEqual(scene.active_page_panel().index, target.index)
            scene.undo_stack.undo()
            self.assertEqual(source.pixmap().toImage().pixelColor(0, 0).name(),
                             "#ff0000")

            scene.set_page_drag_mode("crop")
            self.assertFalse(scene.begin_panel_reorder(
                source, source.sceneBoundingRect().center()))

    def test_one_mouse_gesture_crops_inside_then_reorders_outside(self):
        scene = PhotoScene()
        scene._collage_layout_settings["layout_type"] = "Grid"
        scene.enable_collage_mode()
        source, target = scene._manga_panels[:2]
        source.set_pixmap(self._solid_pixmap("#ff0000"))
        target.set_pixmap(self._solid_pixmap("#0000ff"))
        source.set_zoom_percent(200)

        view = PhotoView(scene)
        view.resize(900, 700)
        view.show()
        view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.app.processEvents()

        start_scene = source.sceneBoundingRect().center()
        crop_scene = start_scene + QPointF(source.boundingRect().width() * 0.12, 0)
        start = view.mapFromScene(start_scene)
        crop = view.mapFromScene(crop_scene)
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(view.viewport(), crop, delay=10)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=crop)
        self.assertNotEqual(source._offset, QPointF())
        self.assertIsNone(scene._panel_drag_preview)

        start = view.mapFromScene(source.sceneBoundingRect().center())
        destination = view.mapFromScene(target.sceneBoundingRect().center())
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(view.viewport(), destination, delay=10)
        QTest.mouseRelease(
            view.viewport(), Qt.MouseButton.LeftButton, pos=destination)
        self.assertEqual(source.pixmap().toImage().pixelColor(0, 0).name(),
                         "#0000ff")
        self.assertEqual(target.pixmap().toImage().pixelColor(0, 0).name(),
                         "#ff0000")
        view.close()

    def test_lines_attach_to_active_frame_and_follow_live_layout(self):
        from main_window import MainWindow

        window = MainWindow()
        window._on_manga_toggled(True)
        scene = window.scene
        scene.set_active_page_panel(1)
        active = scene.active_page_panel()
        window._on_add_speedlines()
        effects = [item for item in scene.items()
                   if isinstance(item, SpeedLinesItem)]
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        self.assertEqual(effect._page_panel_index, 1)
        self.assertEqual(effect.frame_rect(), active.sceneBoundingRect())
        self.assertTrue(active._active_frame)

        old_frame = effect.frame_rect()
        scene.set_manga_layout_setting("margin", 68)
        self.assertNotEqual(effect.frame_rect(), old_frame)
        self.assertEqual(effect.frame_rect(),
                         scene.active_page_panel().sceneBoundingRect())
        self.assertEqual(window.props._tabs.currentIndex(),
                         window.props.FX_TAB)
        window.close()

    def test_blur_and_pixelate_sample_and_follow_active_collage_frame(self):
        from main_window import MainWindow

        window = MainWindow()
        window._on_collage_toggled(True)
        scene = window.scene
        self.assertTrue(scene.load_manga_panel(0, "icons/icon_256.png"))
        scene.set_active_page_panel(0)
        window._on_add_redaction("pixelate")
        effect = next(item for item in scene.items()
                      if isinstance(item, RedactionItem))
        self.assertEqual(effect._page_panel_index, 0)
        self.assertIsNotNone(effect._sample_source())
        self.assertFalse(effect._sample_source().isNull())
        self.assertEqual(window.props._tabs.currentIndex(),
                         window.props.FX_TAB)

        old_frame = QRectF(effect._page_frame)
        scene.set_collage_layout_setting("gap", 63)
        self.assertNotEqual(effect._page_frame, old_frame)
        window.props._refresh_layers()
        labels = [window.props._layers_list.item(index).text()
                  for index in range(window.props._layers_list.count())]
        self.assertIn("Frame 1 · Pixelate", labels)
        self.assertFalse(hasattr(window.props, "_collage_empty_btn"))
        window.props._show_tab(window.props.LAYERS_TAB)
        window.props._on_layer_selection()
        self.assertEqual(window.props._tabs.currentIndex(),
                         window.props.FX_TAB)
        window.close()


if __name__ == "__main__":
    unittest.main()
