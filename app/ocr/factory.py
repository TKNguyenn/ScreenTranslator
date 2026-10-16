from __future__ import annotations

from app.config import OcrSection
from app.ocr.base import OcrEngine
from app.ocr.mock_engine import MockOcrEngine
from app.ocr.rapidocr_engine import RapidOcrEngine


def create_ocr_engine(config: OcrSection) -> OcrEngine:
    engine = config.engine.strip().lower()
    if engine == "rapidocr":
        return RapidOcrEngine(min_confidence=config.min_confidence)
    if engine == "mock":
        return MockOcrEngine()
    raise ValueError(f"Unsupported OCR engine: {engine}")
