"""
main_window.py — MainWindow: v4 layout with TopBar, ContextToolbar,
                 ToolSidebar, CanvasArea, InspectorDock, and StatusBar.
"""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QKeySequence, QShortcut

from canvas import PhotoScene, PhotoView, ZoomBar
from top_bar import TopBar
from tool_sidebar import ToolSidebar
from context_toolbar import ContextToolbar
from inspector_dock import InspectorDock
from video_controls import VideoControls
from bubble import BubbleItem
from media_item import MediaItem
from editor_controller import EditorController
from version import __version__, __app_name__
from constants import VIDEO_EXTENSIONS, ALL_EXTENSIONS
from about_dialog import AboutDialog

import export as exporter


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1180, 720)
        self.resize(1440, 900)
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.scene          = PhotoScene()
        self.controller     = EditorController(self.scene)
        self.view           = PhotoView(self.scene)
        self.zoom_bar       = ZoomBar(self.view)
        self.video_controls = VideoControls()

        self.top_bar      = TopBar(self)
        self.ctx_toolbar  = ContextToolbar(self)
        self.tool_sidebar = ToolSidebar(self)
        self.inspector    = InspectorDock(self)
        self.props        = self.inspector.props
        self.props.set_scene(self.scene)
        self.props.set_undo_stack(self.controller.undo_stack)

        # Canvas area: view + video controls
        canvas_widget = QWidget()
        canvas_widget.setObjectName("CanvasArea")
        canvas_vbox = QVBoxLayout(canvas_widget)
        canvas_vbox.setContentsMargins(0, 0, 0, 0)
        canvas_vbox.setSpacing(0)
        canvas_vbox.addWidget(self.view, stretch=1)
        canvas_vbox.addWidget(self.video_controls)
        self.zoom_bar.setVisible(False)   # zoom lives in TopBar only

        # Content row: sidebar | canvas | inspector (no splitter — inspector is fixed width)
        self.inspector.setFixedWidth(300)
        content = QWidget()
        content_hbox = QHBoxLayout(content)
        content_hbox.setContentsMargins(0, 0, 0, 0)
        content_hbox.setSpacing(0)
        content_hbox.addWidget(self.tool_sidebar)
        content_hbox.addWidget(canvas_widget, stretch=1)
        content_hbox.addWidget(self.inspector)

        # Main layout: TopBar → ContextToolbar → content
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self.top_bar)
        vbox.addWidget(self.ctx_toolbar)
        vbox.addWidget(content, stretch=1)

        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        tb  = self.top_bar
        sb  = self.tool_sidebar
        ctx = self.ctx_toolbar
        sc  = self.scene
        vc  = self.video_controls

        # TopBar
        tb.open_media_requested.connect(self._on_open_media)
        tb.export_requested.connect(self._on_export)
        tb.undo_requested.connect(self.controller.undo_stack.undo)
        tb.redo_requested.connect(self.controller.undo_stack.redo)
        tb.about_requested.connect(self._on_about)
        tb.zoom_changed.connect(self._on_zoom_level)
        tb.theme_change_requested.connect(self._apply_theme)

        # ToolSidebar
        sb.add_bubble_requested.connect(self._on_add_bubble_clicked)
        sb.add_layer_requested.connect(self._on_add_layer)
        sb.meme_toggled.connect(self._on_meme_toggled)
        sb.dual_toggled.connect(self._on_dual_toggled)

        # ContextToolbar
        ctx.align_requested.connect(self._on_context_align)
        ctx.z_requested.connect(self._on_context_z)
        ctx.delete_requested.connect(self._on_context_delete)
        # flip signals are connected but have no-op handlers (unimplemented)
        ctx.flip_h_requested.connect(lambda: None)
        ctx.flip_v_requested.connect(lambda: None)

        # Undo/Redo state
        self.controller.undo_stack.canUndoChanged.connect(tb.set_undo_enabled)
        self.controller.undo_stack.canRedoChanged.connect(tb.set_redo_enabled)
        self.controller.media_loaded.connect(self._on_media_loaded)

        # Canvas
        sc.double_clicked_on_canvas.connect(self._on_canvas_double_click)
        sc.bubble_changed.connect(self.props.update_for_bubble)
        sc.open_right_media_requested.connect(self._on_open_right_media)
        sc.selectionChanged.connect(self._on_selection_changed)

        # View
        self.view.zoom_changed.connect(self.zoom_bar.update_zoom)
        self.view.zoom_changed.connect(self.top_bar.update_zoom)
        self.view.open_media_requested.connect(self._show_open_dialog)
        self.view.photo_dropped.connect(self._on_open_media)
        self.view.right_media_dropped.connect(self._on_right_media_dropped)

        # VideoControls
        vc.frame_changed.connect(self._on_frame_changed)
        vc.right_frame_changed.connect(self._on_right_frame_changed)
        vc.trim_in_changed.connect(self._on_trim_in)
        vc.trim_out_changed.connect(self._on_trim_out)
        vc.cut_requested.connect(self._on_cut)
        vc.cuts_cleared.connect(self._on_clear_cuts)
        vc.reverse_toggled.connect(self._on_reverse)

        # Inspector dual settings
        self.props.dual_gap_changed.connect(self.scene.set_dual_gap)
        self.props.dual_border_changed.connect(self.scene.set_dual_border)
        self.props.dual_feather_changed.connect(self.scene.set_dual_feather)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(
            self.controller.undo_stack.redo
        )
        QShortcut(QKeySequence("Delete"), self).activated.connect(
            self._on_context_delete
        )

    # ------------------------------------------------------------------
    # Media loading
    # ------------------------------------------------------------------

    def _on_open_media(self, path: str):
        if not self.controller.open_media(path):
            QMessageBox.warning(self, "Open", f"Cannot open:\n{path}")

    def _on_media_loaded(self, path: str, is_video: bool):
        self.top_bar.set_media_loaded(True)
        self.tool_sidebar.set_media_loaded(True)
        self.tool_sidebar.set_meme_checked(False)
        self.tool_sidebar.set_dual_checked(False)
        self.tool_sidebar.set_meme_enabled(True)
        self.tool_sidebar.set_dual_enabled(True)

        if is_video:
            self.video_controls.set_player(self.scene.video_player)
            self.video_controls.set_right_player(None)
        else:
            self.video_controls.set_player(None)
            self.video_controls.set_right_player(None)

        self.props.clear()
        self.ctx_toolbar.hide_toolbar()
        self.view.fit_photo()
        self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.statusBar().showMessage(os.path.basename(path))

    # ------------------------------------------------------------------
    # Right media (dual mode)
    # ------------------------------------------------------------------

    def _on_open_right_media(self):
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Right Media", "",
            f"All supported media ({ext_list})"
        )
        if path:
            self._on_right_media_dropped(path)

    def _on_right_media_dropped(self, path: str):
        ok = self.controller.open_right_media(path)
        if not ok:
            QMessageBox.warning(self, "Open Right Media", f"Cannot open:\n{path}")
        else:
            if os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS:
                self.video_controls.set_right_player(self.scene.video_player_right)
            self.view.fit_photo()

    # ------------------------------------------------------------------
    # Overlay layers
    # ------------------------------------------------------------------

    def _on_add_layer(self):
        if not self.scene.has_photo():
            return
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Layer", "",
            f"All supported media ({ext_list})"
        )
        if not path:
            return
        item = self.controller.add_overlay(path)
        if item is None:
            QMessageBox.warning(self, "Add Layer", f"Cannot open:\n{path}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export(self):
        self.video_controls.stop()
        has_left_video  = self.scene.has_video()
        has_right_video = (self.scene.video_player_right is not None
                           and self.scene.video_player_right.is_loaded())

        if has_left_video or has_right_video:
            exporter.export_video(
                self, self.scene,
                self.scene._photo_item,
                self.scene.video_player,
                right_photo_item=self.scene._photo_item_right,
                right_player=self.scene.video_player_right,
                is_dual=self.scene.is_dual_mode(),
            )
        else:
            exporter.export_photo(
                self, self.scene,
                self.scene._photo_item,
                right_photo_item=self.scene._photo_item_right,
                is_dual=self.scene.is_dual_mode(),
            )

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _on_zoom_level(self, key: str):
        if key in ("fit_width", "fit-width"):
            self.view.fit_width()
        elif key in ("fit_window", "fit-window"):
            self.view.fit_photo()
        else:
            try:
                self.view.set_zoom_percent(int(key))
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------

    def _on_meme_toggled(self, enabled: bool):
        self.controller.set_meme_mode(enabled)
        self.view.fit_photo()

    def _on_dual_toggled(self, enabled: bool):
        self.controller.set_dual_mode(enabled)
        if enabled:
            if not self.scene.selectedItems():
                self.props.show_dual_settings()
        else:
            self.video_controls.set_right_player(None)
        self.view.fit_photo()

    # ------------------------------------------------------------------
    # Video controls
    # ------------------------------------------------------------------

    def _on_frame_changed(self, frame: int):
        self.scene.update_frame(frame)
        self.video_controls.set_current_frame(frame)

    def _on_right_frame_changed(self, frame: int):
        self.scene.update_right_frame(frame)

    def _on_trim_in(self, frame: int):
        player = self._active_player()
        if player:
            player.set_trim_in(frame)
            self.video_controls.sync_markers()

    def _on_trim_out(self, frame: int):
        player = self._active_player()
        if player:
            player.set_trim_out(frame)
            self.video_controls.sync_markers()

    def _on_cut(self):
        player = self._active_player()
        if not player:
            return
        s, e = player.trim_in, player.trim_out
        if s >= e:
            return
        player.add_cut(s, e)
        player.set_trim_in(0)
        player.set_trim_out(player.frame_count - 1)
        self.video_controls.sync_markers()
        cur = self.video_controls.current_frame
        if s <= cur <= e:
            next_frame = e + 1
            if next_frame > player.frame_count - 1:
                next_frame = 0
            self.video_controls._current_frame = next_frame
            self._on_frame_changed(next_frame)

    def _on_clear_cuts(self):
        player = self._active_player()
        if player:
            player.clear_cuts()
            self.video_controls.sync_markers()

    def _on_reverse(self):
        player = self._active_player()
        if player:
            player.toggle_reverse()

    def _active_player(self):
        if self.video_controls.active_side == "right":
            return self.scene.video_player_right
        return self.scene.video_player

    # ------------------------------------------------------------------
    # Canvas interactions
    # ------------------------------------------------------------------

    def _show_open_dialog(self):
        ext_list = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            f"All supported media ({ext_list})"
        )
        if path:
            self._on_open_media(path)

    def _on_add_bubble_clicked(self):
        if not self.scene.has_photo():
            return
        c = self.scene.sceneRect().center()
        self._on_canvas_double_click(c.x(), c.y())

    def _on_add_bubble_with_style(self, style: str):
        if not self.scene.has_photo():
            return
        c = self.scene.sceneRect().center()
        bubble = self.controller.add_bubble(c.x(), c.y(), style=style)
        self.props.update_for_bubble(bubble)
        self.ctx_toolbar.show_for_bubble()

    def _on_canvas_double_click(self, x: float, y: float):
        bubble = self.controller.add_bubble(x, y)
        self.props.update_for_bubble(bubble)
        self.ctx_toolbar.show_for_bubble()

    # ------------------------------------------------------------------
    # Selection → inspector + ContextToolbar
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        selected = self.scene.selectedItems()
        bubbles  = [i for i in selected if isinstance(i, BubbleItem)]
        media    = [i for i in selected if isinstance(i, MediaItem)]
        if bubbles:
            self.props.update_for_bubble(bubbles[0])
            self.ctx_toolbar.show_for_bubble()
        elif media:
            self.props.update_for_media(media[0])
            self.ctx_toolbar.show_for_media()
        elif self.scene.is_dual_mode():
            self.props.show_dual_settings()
            self.ctx_toolbar.hide_toolbar()
        else:
            self.props.clear()
            self.ctx_toolbar.hide_toolbar()

    # ------------------------------------------------------------------
    # ContextToolbar actions
    # ------------------------------------------------------------------

    def _on_context_align(self, mode: str):
        selected = self.scene.selectedItems()
        if not selected:
            return
        item = selected[0]
        if not isinstance(item, BubbleItem):
            return
        sr  = self.scene.sceneRect()
        r   = item.body_rect
        pos = item.pos()
        new_pos = QPointF(pos)
        if mode == "left":
            new_pos.setX(sr.left() - r.left())
        elif mode == "hcenter":
            new_pos.setX(sr.center().x())
        elif mode == "right":
            new_pos.setX(sr.right() - r.right())
        elif mode == "top":
            new_pos.setY(sr.top() - r.top())
        elif mode == "vcenter":
            new_pos.setY(sr.center().y())
        elif mode == "bottom":
            new_pos.setY(sr.bottom() - r.bottom())
        if (new_pos - pos).manhattanLength() > 0.5:
            from undo_commands import MoveBubbleCommand
            self.controller.undo_stack.push(MoveBubbleCommand(item, pos, new_pos))

    def _on_context_z(self, mode: str):
        selected = self.scene.selectedItems()
        if not selected:
            return
        item = selected[0]
        old  = item.zValue()
        if mode == "front":
            new = old + 10.0
        elif mode == "forward":
            new = old + 1.0
        elif mode == "backward":
            new = max(0.0, old - 1.0)
        elif mode == "back":
            new = max(0.0, old - 10.0)
        else:
            return
        if abs(old - new) > 0.01:
            from undo_commands import ZValueChangeCommand
            self.controller.undo_stack.push(ZValueChangeCommand(item, old, new))

    def _on_context_delete(self):
        selected = self.scene.selectedItems()
        if not selected:
            return
        item = selected[0]
        if isinstance(item, BubbleItem):
            item._delete()
        elif isinstance(item, MediaItem) and getattr(item, "_is_overlay", False):
            from undo_commands import RemoveOverlayCommand
            self.controller.undo_stack.push(RemoveOverlayCommand(self.scene, item))

    # ------------------------------------------------------------------
    # Theme switching
    # ------------------------------------------------------------------

    _THEME_OVERRIDES = {
        "dark": "",   # base QSS is the dark theme — no overrides needed
        "oled": """
            QWidget                  { background-color: #000000; }
            QMainWindow, QDialog     { background-color: #000000; }
            #TopBar                  { background-color: #0a0a0a; border-bottom: 1px solid #1a1a1a; }
            #InspectorDock           { background-color: #0a0a0a; border-left: 1px solid #1a1a1a; }
            #ToolSidebar             { background-color: #0a0a0a; border-right: 1px solid #1a1a1a; }
            #CanvasArea, QGraphicsView { background-color: #000000; }
            #InspectorPage, #InspectorSection, #InspectorSectionHeader,
            #InspectorSectionBody    { background-color: #0a0a0a; }
            QScrollArea              { background-color: #000000; }
            QComboBox, QFontComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
            QSlider::groove:horizontal { background-color: #111111; }
            #StyleButton, #AlignButton, #ArrangeButton { background-color: #111111; }
        """,
        "blue": """
            QWidget                  { background-color: #0f172a; color: #e2e8f0; }
            QMainWindow, QDialog     { background-color: #0f172a; }
            #TopBar                  { background-color: #1e293b; border-bottom: 1px solid #334155; }
            #InspectorDock           { background-color: #1e293b; border-left: 1px solid #334155; }
            #ToolSidebar             { background-color: #1e293b; border-right: 1px solid #334155; }
            #CanvasArea, QGraphicsView { background-color: #0b1120; }
            #InspectorPage, #InspectorSection, #InspectorSectionHeader,
            #InspectorSectionBody    { background-color: #1e293b; }
            QScrollArea              { background-color: #0f172a; }
            QComboBox, QFontComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { background-color: #334155; border-color: #475569; }
            QSlider::groove:horizontal { background-color: #334155; }
            QSlider::handle:horizontal { background-color: #38bdf8; }
            QSlider::sub-page:horizontal { background-color: #38bdf8; }
            #StyleButton, #AlignButton, #ArrangeButton { background-color: #334155; border-color: #475569; }
            #StyleButton:checked { background-color: rgba(56,189,248,0.15); border-color: #38bdf8; color: #38bdf8; }
            #ContextToolbar          { background-color: #1e293b; border-bottom: 1px solid rgba(56,189,248,0.3); }
            #ContextChip             { background-color: rgba(56,189,248,0.12); border-color: rgba(56,189,248,0.4); color: #38bdf8; }
            #BtnExport               { background-color: #0284c7; }
            #BtnExport:hover         { background-color: #0ea5e9; }
        """,
    }

    def _apply_theme(self, name: str):
        base_path = os.path.join(os.path.dirname(__file__), "theme", "dark.qss")
        with open(base_path) as f:
            base_qss = f.read()
        override = self._THEME_OVERRIDES.get(name, "")
        QApplication.instance().setStyleSheet(base_qss + override)

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _on_about(self):
        AboutDialog(self).exec()
