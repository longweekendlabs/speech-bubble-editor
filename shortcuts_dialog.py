"""
shortcuts_dialog.py — Keyboard shortcuts reference dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QWidget,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


SHORTCUT_GROUPS = [
    (
        "Project",
        [
            ("Open media", "Ctrl+O"),
            ("Export", "Ctrl+E"),
            ("Reset project", "Ctrl+N"),
            ("Show keyboard shortcuts", "Ctrl+/"),
        ],
    ),
    (
        "Editing",
        [
            ("Undo", "Ctrl+Z"),
            ("Redo", "Ctrl+Y or Ctrl+Shift+Z"),
            ("Add speech bubble", "Ctrl+B"),
            ("Add text", "T"),
            ("Add image or video layer", "Ctrl+L"),
            ("Delete selected item", "Delete"),
        ],
    ),
    (
        "Tools",
        [
            ("Select tool", "V"),
            ("Move tool", "M"),
        ],
    ),
    (
        "Video",
        [
            ("Play or pause", "Space"),
            ("Step back one frame", "Left Arrow"),
            ("Step forward one frame", "Right Arrow"),
            ("Go to first frame", "Home"),
            ("Go to last frame", "End"),
            ("Set trim in", "["),
            ("Set trim out", "]"),
            ("Toggle fullscreen window", "F"),
        ],
    ),
]


class ShortcutsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setFixedWidth(640)
        self.setModal(True)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Keyboard Shortcuts")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        subtitle = QLabel("Quick actions available while editing.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        subtitle.setStyleSheet("color: #8a95aa; font-size: 11px;")
        layout.addWidget(subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        groups = QGridLayout()
        groups.setContentsMargins(0, 0, 0, 0)
        groups.setHorizontalSpacing(24)
        groups.setVerticalSpacing(14)
        for index, (group_name, rows) in enumerate(SHORTCUT_GROUPS):
            groups.addWidget(
                self._group_widget(group_name, rows),
                index // 2,
                index % 2,
            )
        layout.addLayout(groups)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setToolTip("Close keyboard shortcuts")
        close_btn.clicked.connect(self.accept)

        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(close_btn)
        h.addStretch()
        layout.addLayout(h)

    def _group_widget(self, group_name: str, rows: list[tuple[str, str]]) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(7)

        group_label = QLabel(group_name.upper())
        group_label.setObjectName("ShortcutsGroupLabel")
        group_label.setStyleSheet(
            "color: #9fb0cf; font-size: 10px; font-weight: 700; "
            "letter-spacing: 1px;"
        )
        panel_layout.addWidget(group_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(7)

        for row, (action, keys) in enumerate(rows):
            action_label = QLabel(action)
            action_label.setStyleSheet("color: #d8deea;")
            key_label = QLabel(keys)
            key_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            key_label.setStyleSheet(
                "color: #46ddcb; font-weight: 700; "
                "font-family: monospace;"
            )
            grid.addWidget(action_label, row, 0)
            grid.addWidget(key_label, row, 1)

        grid.setColumnStretch(0, 1)
        panel_layout.addLayout(grid)
        panel_layout.addStretch()
        return panel
