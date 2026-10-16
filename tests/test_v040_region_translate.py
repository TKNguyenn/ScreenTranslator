from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class V040RegionTranslateSourceTests(unittest.TestCase):
    def test_region_selector_targets_monitor_under_cursor_and_handles_dpi_mapping(self) -> None:
        source = (ROOT / "app" / "ui" / "region_selector.py").read_text(encoding="utf-8")
        self.assertIn("QGuiApplication.screenAt(QCursor.pos())", source)
        self.assertIn("scale_x = self._screenshot.width() / logical_width", source)
        self.assertIn("Esc / chuột phải để hủy", source)

    def test_controller_pipelines_capture_to_ocr_to_translation(self) -> None:
        source = (ROOT / "app" / "controller.py").read_text(encoding="utf-8")
        self.assertIn("self._ocr_worker.submit(result.job_id, result.image_png)", source)
        self.assertIn("mode=RequestMode.REGION", source)
        self.assertIn("allow_replace=False", source)
        self.assertIn("self._translation_worker.submit(request)", source)

    def test_tray_and_main_window_expose_region_translate(self) -> None:
        tray = (ROOT / "app" / "ui" / "tray.py").read_text(encoding="utf-8")
        main = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn('QAction("Dịch vùng màn hình"', tray)
        self.assertIn('self._nav.addItem("Dịch vùng màn hình")', main)
        self.assertIn("region_translate_requested", main)

    def test_rapidocr_dependency_is_declared(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("rapidocr_onnxruntime", requirements)


if __name__ == "__main__":
    unittest.main()
