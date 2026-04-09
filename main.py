"""
main.py — Entry point for Speech Bubble Editor v3.
"""

import os
import sys

_singleton_server = None  # module-level — prevents GC of the QLocalServer


def _resource_path(relative: str) -> str:
    """Return absolute path to a bundled resource (PyInstaller-aware)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


def _apply_system_theme(app):
    """Apply the OS dark/light theme to the Qt application.

    On Windows, reads AppsUseLightTheme from the registry.
    Dark mode → Fusion style + dark palette (Qt's native Windows style
    does not reliably handle dark mode before Qt 6.7).
    Light mode → native windowsvista style for proper Windows chrome.
    On macOS, Qt6 reads the system appearance automatically; we use
    Fusion for consistent custom-colour rendering.
    On Linux/other Qt picks up the system theme automatically.
    """
    if sys.platform == "win32":
        from PyQt6.QtGui import QPalette, QColor

        dark_mode = False
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            dark_mode = not bool(use_light)
        except Exception:
            pass  # registry read failed — fall through to light mode

        if dark_mode:
            app.setStyle("Fusion")
            p = QPalette()
            bg      = QColor(30,  30,  30)
            panel   = QColor(45,  45,  45)
            ctrl    = QColor(53,  53,  53)
            fg      = QColor(220, 220, 220)
            hi      = QColor(42,  130, 218)
            hi_text = QColor(255, 255, 255)
            p.setColor(QPalette.ColorRole.Window,          bg)
            p.setColor(QPalette.ColorRole.WindowText,      fg)
            p.setColor(QPalette.ColorRole.Base,            panel)
            p.setColor(QPalette.ColorRole.AlternateBase,   ctrl)
            p.setColor(QPalette.ColorRole.ToolTipBase,     ctrl)
            p.setColor(QPalette.ColorRole.ToolTipText,     fg)
            p.setColor(QPalette.ColorRole.Text,            fg)
            p.setColor(QPalette.ColorRole.Button,          ctrl)
            p.setColor(QPalette.ColorRole.ButtonText,      fg)
            p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 80, 80))
            p.setColor(QPalette.ColorRole.Link,            hi)
            p.setColor(QPalette.ColorRole.Highlight,       hi)
            p.setColor(QPalette.ColorRole.HighlightedText, hi_text)
            # Dimmed disabled colours
            dim = QColor(110, 110, 110)
            p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       dim)
            p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, dim)
            p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, dim)
            app.setPalette(p)
        else:
            # Light mode: native Windows chrome (respects accent colour, etc.)
            app.setStyle("windowsvista")

    elif sys.platform == "darwin":
        # Qt6 on macOS reads the system appearance automatically.
        # Use Fusion style so custom colours render consistently.
        app.setStyle("Fusion")


def _setup_single_instance(window) -> bool:
    """Return True if this is the first instance. Side-effect: starts server."""
    global _singleton_server
    try:
        from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    except ImportError:
        return True

    SERVER_NAME = "SpeechBubbleEditorV3"

    # Check for existing instance
    probe = QLocalSocket()
    probe.connectToServer(SERVER_NAME)
    if probe.waitForConnected(400):
        probe.write(b"raise")
        probe.flush()
        probe.waitForBytesWritten(1000)
        probe.disconnectFromServer()
        return False   # another instance running

    # First instance — start server
    from PyQt6.QtCore import Qt
    _singleton_server = QLocalServer()
    QLocalServer.removeServer(SERVER_NAME)
    _singleton_server.listen(SERVER_NAME)

    def _on_connection():
        conn = _singleton_server.nextPendingConnection()
        if conn:
            def _read():
                data = bytes(conn.readAll()).decode("utf-8", errors="ignore")
                if "raise" in data:
                    window.setWindowState(
                        window.windowState() & ~Qt.WindowState.WindowMinimized
                        | Qt.WindowState.WindowActive
                    )
                    window.raise_()
                    window.activateWindow()
            conn.readyRead.connect(_read)

    _singleton_server.newConnection.connect(_on_connection)
    return True


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon, QFont, QFontDatabase

    app = QApplication(sys.argv)
    app.setApplicationName("Speech Bubble Editor")
    app.setOrganizationName("Long Weekend Labs")

    _apply_system_theme(app)

    # Load bundled fonts
    fonts_dir = _resource_path("fonts")
    if os.path.isdir(fonts_dir):
        for fname in os.listdir(fonts_dir):
            if fname.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(
                    os.path.join(fonts_dir, fname))

    # App icon
    icon_path = _resource_path(os.path.join("icons", "icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from main_window import MainWindow
    window = MainWindow()

    if not _setup_single_instance(window):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Already Running",
                                "Speech Bubble Editor is already open.")
        sys.exit(0)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
