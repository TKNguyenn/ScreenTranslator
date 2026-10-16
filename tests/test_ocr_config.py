from __future__ import annotations

import unittest

from app.config import AppConfig, OcrSection, _build_ocr_section


class OcrConfigTests(unittest.TestCase):
    def test_defaults_enable_region_with_rapidocr(self) -> None:
        config = AppConfig()
        self.assertTrue(config.features.region_translate_enabled)
        self.assertEqual(config.ocr.engine, "rapidocr")
        self.assertAlmostEqual(config.ocr.min_confidence, 0.45)

    def test_ocr_section_accepts_mock_for_tests(self) -> None:
        section = _build_ocr_section({"engine": "mock", "min_confidence": 0.2})
        self.assertEqual(section, OcrSection(engine="mock", min_confidence=0.2))

    def test_invalid_confidence_fails_fast(self) -> None:
        with self.assertRaises(ValueError):
            _build_ocr_section({"engine": "rapidocr", "min_confidence": 1.5})

    def test_unknown_engine_fails_fast(self) -> None:
        with self.assertRaises(ValueError):
            _build_ocr_section({"engine": "cloud-ocr"})


if __name__ == "__main__":
    unittest.main()
