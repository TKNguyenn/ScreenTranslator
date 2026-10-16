from __future__ import annotations

from app.models import OcrBlock
from app.ocr.base import OcrEngine


class MockOcrEngine(OcrEngine):
    """Deterministic backend for tests/development without an OCR runtime."""

    def __init__(self, text: str = "Mock OCR text") -> None:
        self._text = text

    @property
    def engine_id(self) -> str:
        return "mock"

    def recognize(self, image_png: bytes) -> tuple[str, tuple[OcrBlock, ...]]:
        del image_png
        text = self._text.strip()
        blocks = (OcrBlock(text=text, confidence=1.0),) if text else ()
        return text, blocks
