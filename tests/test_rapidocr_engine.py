from __future__ import annotations

import unittest

from app.ocr.rapidocr_engine import RapidOcrEngine


class _FakeRapidOcr:
    def __call__(self, image_bytes: bytes):
        self.last_image = image_bytes
        return (
            [
                [[[10, 30], [80, 30], [80, 42], [10, 42]], "第二行", 0.96],
                [[[10, 10], [80, 10], [80, 22], [10, 22]], "第一行", 0.98],
                [[[10, 50], [80, 50], [80, 62], [10, 62]], "low", 0.20],
            ],
            0.012,
        )


class RapidOcrEngineTests(unittest.TestCase):
    def test_normalizes_order_and_filters_confidence(self) -> None:
        engine = RapidOcrEngine(min_confidence=0.45)
        fake = _FakeRapidOcr()
        engine._engine = fake  # inject backend so this test needs no optional package

        text, blocks = engine.recognize(b"png")

        self.assertEqual(text, "第一行\n第二行")
        self.assertEqual([block.text for block in blocks], ["第一行", "第二行"])
        self.assertEqual(fake.last_image, b"png")

    def test_empty_image_is_rejected(self) -> None:
        engine = RapidOcrEngine()
        with self.assertRaises(ValueError):
            engine.recognize(b"")


if __name__ == "__main__":
    unittest.main()
