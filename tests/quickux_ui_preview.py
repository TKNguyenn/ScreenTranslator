"""Render the real widgets with synthetic text; no API or clipboard access."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PySide6.QtWidgets import QApplication

from app.config import QuickUxSection
from app.ui.quick_popup import QuickTranslationPopup
from app.ui.quick_toolbar import QuickToolbar


def main():
    app = QApplication([])
    # The Windows offscreen plugin has no system font database by default.
    if os.name == "nt":
        font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for filename in ("segoeui.ttf", "seguisb.ttf", "msjh.ttc"):
            QFontDatabase.addApplicationFont(str(font_dir / filename))
        app.setFont(QFont("Segoe UI", 9))
    toolbar = QuickToolbar(QuickUxSection())
    toolbar.show()
    popup = QuickTranslationPopup(QuickUxSection())
    popup.start("preview", "設備を起動する前に、安全インターロックを確認してください。",
                "vi", "Engineer", "Fast", "OpenAI-compatible", "configured-model",
                QPoint(20, 20), True)
    popup.finish("preview", "Trước khi khởi động thiết bị, hãy kiểm tra liên động an toàn.\n\n"
                 "Chỉ tiếp tục vận hành khi các điều kiện bảo vệ đã được đáp ứng.", False)
    expanded = QuickTranslationPopup(QuickUxSection())
    expanded.start("wide", "設備を起動する前に、安全インターロックを確認してください。",
                   "vi", "Engineer", "Fast", "OpenAI-compatible", "configured-model",
                   QPoint(20, 20), True)
    expanded.resize(620, 465)
    expanded.finish("wide", popup._translation, False)
    expanded._show_original.click()
    expanded._pin.click()
    app.processEvents()

    canvas = QImage(1200, 720, QImage.Format_ARGB32)
    canvas.fill(QColor("#e9eef5"))
    painter = QPainter(canvas)
    painter.setPen(QColor("#24354e"))
    painter.setFont(QFont("Segoe UI", 22, QFont.Bold))
    painter.drawText(QPoint(32, 48), "Quick Translate")
    painter.setFont(QFont("Segoe UI", 12))
    painter.drawText(QPoint(32, 80), "Toolbar rõ nền · Popup kéo thả và thay đổi kích thước")
    painter.drawPixmap(32, 108, toolbar.grab())
    painter.drawPixmap(32, 210, popup.grab())
    painter.drawPixmap(528, 210, expanded.grab())
    painter.setPen(QColor("#52647e"))
    painter.drawText(QRect(32, 175, 460, 25), Qt.AlignLeft, "Kích thước mặc định")
    painter.drawText(QRect(528, 175, 620, 25), Qt.AlignLeft, "Mở rộng · Xem gốc · Ghim")
    painter.end()
    output = Path(__file__).resolve().parents[1] / "artifacts" / "quickux-v0413-preview.png"
    output.parent.mkdir(exist_ok=True)
    if not canvas.save(str(output)):
        raise RuntimeError("Could not save UI preview")
    print(output)
    for widget in (toolbar, popup, expanded):
        widget.close()


if __name__ == "__main__":
    main()
