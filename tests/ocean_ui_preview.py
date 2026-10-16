"""Render every real UI page using synthetic config and no app workers."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PySide6.QtWidgets import QApplication

from app.config import AppConfig, ProviderProfile, ProviderSection
from app.ui.main_window import MainWindow
from app.ui.popup import TranslationPopup
from app.ui.quick_popup import QuickTranslationPopup
from app.ui.quick_toolbar import QuickToolbar
from app.ui.theme import apply_theme


def synthetic_config():
    return AppConfig(providers=ProviderSection(active_profile="Demo Provider", profiles={
        "Demo Provider": ProviderProfile(model="translation-model", models=("translation-model",),
                                         base_url="https://example.test/v1", api_key=""),
    }))


def main():
    app = QApplication([])
    if os.name == "nt" and app.platformName() == "offscreen":
        directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "seguisb.ttf", "msjh.ttc"):
            QFontDatabase.addApplicationFont(str(directory / name))
        app.setFont(QFont("Segoe UI", 9))
    apply_theme(app)
    output = Path(__file__).resolve().parents[1] / "artifacts" / "ocean-v0414"
    output.mkdir(parents=True, exist_ok=True)
    config = synthetic_config()
    window = MainWindow(app, config)
    window.resize(1180, 800)
    window.show()
    for index, name in enumerate(("overview", "providers", "prompts", "region", "quick-ux", "pdf")):
        window._nav.setCurrentRow(index)
        app.processEvents()
        window.grab().save(str(output / (name + ".png")))
    window.resize(900, 620)
    for index in range(6):
        window._nav.setCurrentRow(index)
        app.processEvents()
        window.grab().save(str(output / f"compact-{index}.png"))
    toolbar = QuickToolbar(config.quick_ux)
    toolbar.show()
    popup = QuickTranslationPopup(config.quick_ux)
    popup.start("preview", "Check the safety interlock before starting the machine.",
                "vi", "Engineer", "Fast", "Demo Provider", "translation-model", QPoint(20,20), True)
    popup.resize(500, 400)
    popup.finish("preview", "Kiểm tra liên động an toàn trước khi khởi động máy.\n\n"
                 "Chỉ tiếp tục vận hành khi các điều kiện bảo vệ đã được đáp ứng.", False)
    popup._show_original.click()
    popup._pin.click()
    app.processEvents()
    image = QImage(640, 600, QImage.Format_ARGB32)
    image.fill(QColor("#080E1A"))
    painter = QPainter(image)
    painter.drawPixmap(32, 30, toolbar.grab())
    painter.drawPixmap(32, 120, popup.grab())
    painter.end()
    image.save(str(output / "quick-surfaces.png"))
    legacy = TranslationPopup(config.ui)
    legacy.show_processing("Synthetic selection", "vi", "Demo Provider", "translation-model", None)
    app.processEvents()
    legacy.grab().save(str(output / "legacy-popup.png"))
    for widget in (window, toolbar, popup, legacy):
        if isinstance(widget, MainWindow):
            widget.allow_close()
        widget.close()
    print(output)


if __name__ == "__main__":
    main()
