"""
Native file dialog helpers.

Qt falls back to its own QFileDialog when native dialogs are disabled or no
platform portal is available. Keep the calls centralized so open/import flows
all ask for the OS file picker first.
"""

from PyQt6.QtWidgets import QFileDialog


def open_file(parent, title: str, file_filter: str, directory: str = "") -> str:
    options = QFileDialog.Option(0)
    options &= ~QFileDialog.Option.DontUseNativeDialog
    path, _ = QFileDialog.getOpenFileName(
        parent,
        title,
        directory,
        file_filter,
        options=options,
    )
    return path
