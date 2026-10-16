"""Explicit native Windows UI check without focus/clipboard/API changes."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.config import QuickUxSection
from app.services.window_service import WindowService
from app.ui.quick_popup import QuickTranslationPopup
from app.ui.quick_toolbar import QuickToolbar
from app.ui.theme import apply_theme


def main():
    if os.name != "nt":
        raise SystemExit("Windows required")
    app = QApplication([])
    if app.platformName() != "windows":
        raise SystemExit("Native Windows Qt platform required (unset QT_QPA_PLATFORM)")
    apply_theme(app)
    foreground = WindowService.get_foreground_window()
    toolbar = QuickToolbar(QuickUxSection())
    popup = QuickTranslationPopup(QuickUxSection())
    get_style = ctypes.windll.user32.GetWindowLongPtrW
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    try:
        for widget in (toolbar, popup):
            widget.move(-32000, -32000)
            widget.show()
            widget.raise_()
            app.processEvents()
            style = get_style(int(widget.winId()), -20)
            assert style & 0x08000000, "WS_EX_NOACTIVATE missing"
            assert style & 0x00000008, "WS_EX_TOPMOST missing"
            image = widget.grab().toImage()
            pixel = image.pixelColor(widget.width() // 2, 3)
            assert pixel.alpha() == 255 and pixel.red() < 30 and pixel.blue() > pixel.red(), "Opaque ocean card background missing"
        assert WindowService.get_foreground_window() == foreground, "Showing Quick UI stole focus"

        label = popup._headline
        local = QPoint(20, 10)
        origin = label.mapToGlobal(local)
        old_position = popup.pos()
        for kind, global_pos, button, buttons in (
            (QEvent.MouseButtonPress, origin, Qt.LeftButton, Qt.LeftButton),
            (QEvent.MouseMove, origin + QPoint(40, 30), Qt.NoButton, Qt.LeftButton),
            (QEvent.MouseButtonRelease, origin + QPoint(40, 30), Qt.LeftButton, Qt.NoButton),
        ):
            QApplication.sendEvent(label, QMouseEvent(kind, QPointF(local), QPointF(global_pos),
                                                      button, buttons, Qt.NoModifier))
        assert popup.pos() == old_position + QPoint(40, 30), "Native header drag failed"
        popup.resize(590, 430)
        popup._pending_job = "native-smoke"
        geometry = popup.geometry()
        popup.finish("native-smoke", "Synthetic translation", False)
        app.processEvents()
        assert popup.geometry() == geometry, "Final result reset user geometry"
        assert WindowService.get_foreground_window() == foreground, "Interacting with Quick UI stole focus"
        print("PASS: native Windows opaque background, topmost, no-activate, drag and retained geometry")
    finally:
        toolbar.close()
        popup.close()
        app.processEvents()


if __name__ == "__main__":
    main()
