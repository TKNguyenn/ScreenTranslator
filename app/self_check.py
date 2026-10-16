"""Offline checks for a packaged Windows release; no input hooks or API calls."""
from __future__ import annotations

import json
from pathlib import Path

from app.config import AppConfig
from app.version import APP_VERSION


def run_self_check(report_path: Path) -> int:
    report = {"version": APP_VERSION, "ok": False, "checks": []}
    try:
        config = AppConfig.load()
        from PySide6.QtCore import QBuffer, QIODevice, QPoint
        from PySide6.QtGui import QFont, QImage, QPainter
        from PySide6.QtWidgets import QApplication
        from app.ui.main_window import MainWindow
        from app.ui.quick_popup import QuickTranslationPopup
        from app.ui.quick_toolbar import QuickToolbar
        from app.ui.theme import apply_theme, asset_icon
        app = QApplication.instance() or QApplication([])
        apply_theme(app)
        assert not asset_icon().isNull(), "App icon is missing"
        window = MainWindow(app, config)
        window.resize(1000, 720)
        window._add_google_provider("Google Translate Free")
        assert window._models_group.isHidden() and window._stream_group.isHidden()
        window._add_google_provider("Google Cloud Translate")
        assert window._api_key_edit.isEnabled()
        report["checks"].append("Qt theme, icons, manager and Google forms")
        toolbar = QuickToolbar(config.quick_ux)
        popup = QuickTranslationPopup(config.quick_ux)
        popup.resize(550, 420)
        image = toolbar.grab().toImage()
        assert image.pixelColor(toolbar.width() // 2, 3).alpha() == 255
        popup._pending_job = "self-check"
        geometry = popup.geometry()
        popup.finish("self-check", "Synthetic translation", False)
        assert popup.geometry() == geometry
        report["checks"].append("Quick UI opaque background and retained popup size")
        from app.providers.factory import create_translation_provider
        provider = create_translation_provider(config)
        provider.close()
        report["checks"].append("Configured provider construction (no network)")
        import pynput.mouse._win32
        import keyboard._winkeyboard
        import uiautomation as uia
        assert uia.GetRootControl().NativeWindowHandle
        report["checks"].append("Windows UI Automation COM and input backends (no hooks)")
        canvas = QImage(800, 130, QImage.Format_RGB32)
        canvas.fill(0xFFFFFF)
        painter = QPainter(canvas)
        painter.setPen(0x000000)
        painter.setFont(QFont("Arial", 40))
        painter.drawText(QPoint(20, 85), "HELLO WORLD 123")
        painter.end()
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        canvas.save(buffer, "PNG")
        from app.ocr.rapidocr_engine import RapidOcrEngine
        text, blocks = RapidOcrEngine().recognize(bytes(buffer.data()))
        assert "HELLO" in text.upper() and blocks, f"OCR failed synthetic text: {text!r}"
        report["checks"].append("RapidOCR inference using bundled models: HELLO WORLD 123")
        window.allow_close()
        for widget in (window, toolbar, popup):
            widget.close()
        report["ok"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
