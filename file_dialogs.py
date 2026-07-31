"""
Native file dialog helpers.

Qt falls back to its own QFileDialog when native dialogs are disabled or no
platform portal is available. Keep the calls centralized so open/import flows
all ask for the OS file picker first — and so they all remember the last folder
the user browsed to.
"""

import os
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QSettings

_SETTINGS_ORG = "LongWeekendLabs"
_SETTINGS_APP = "SpeechBubbleEditor"
_LAST_DIR_KEY = "dialogs/last_open_dir"


def _settings() -> QSettings:
    return QSettings(_SETTINGS_ORG, _SETTINGS_APP)


def _last_dir() -> str:
    d = _settings().value(_LAST_DIR_KEY, "", type=str)
    return d if d and os.path.isdir(d) else ""


def _remember_dir(path: str) -> None:
    if path:
        _settings().setValue(_LAST_DIR_KEY, os.path.dirname(path))


def open_file(parent, title: str, file_filter: str, directory: str = "") -> str:
    options = QFileDialog.Option(0)
    options &= ~QFileDialog.Option.DontUseNativeDialog
    # Fall back to the last folder the user opened from when no explicit
    # directory is given, so the picker doesn't reset every time.
    start_dir = directory or _last_dir()
    path, _ = QFileDialog.getOpenFileName(
        parent,
        title,
        start_dir,
        file_filter,
        options=options,
    )
    _remember_dir(path)
    return path
