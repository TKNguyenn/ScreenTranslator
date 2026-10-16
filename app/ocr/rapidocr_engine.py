from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from app.models import OcrBlock
from app.ocr.base import OcrEngine


logger = logging.getLogger(__name__)


class RapidOcrEngine(OcrEngine):
    """Local OCR using ``rapidocr_onnxruntime``.

    The dependency is imported and the model is initialized lazily on the first
    Region Translate request. That keeps normal text-translation startup light
    and makes missing OCR dependencies fail with a focused runtime message.
    """

    def __init__(self, min_confidence: float = 0.45) -> None:
        self._min_confidence = float(min_confidence)
        self._engine: Any | None = None

    @property
    def engine_id(self) -> str:
        return "rapidocr"

    def _ensure_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        try:
            from rapidocr_onnxruntime import RapidOCR
        except Exception as exc:  # pragma: no cover - depends on optional runtime
            raise RuntimeError(
                "RapidOCR chưa sẵn sàng. Hãy chạy lại run.bat để cài "
                "rapidocr_onnxruntime, hoặc cài thủ công bằng: "
                "pip install rapidocr_onnxruntime"
            ) from exc
        try:
            self._engine = RapidOCR()
        except Exception as exc:  # pragma: no cover - backend/runtime specific
            raise RuntimeError(f"Không thể khởi tạo RapidOCR: {exc}") from exc
        logger.info("RapidOCR initialized")
        return self._engine

    def recognize(self, image_png: bytes) -> tuple[str, tuple[OcrBlock, ...]]:
        if not image_png:
            raise ValueError("OCR image is empty")

        engine = self._ensure_engine()
        try:
            raw = engine(image_png)
        except Exception as exc:
            raise RuntimeError(f"RapidOCR nhận dạng thất bại: {exc}") from exc

        records = self._extract_records(raw)
        normalized: list[tuple[float, float, str, float]] = []
        for item in records:
            parsed = self._parse_record(item)
            if parsed is None:
                continue
            top, left, text, score = parsed
            if score < self._min_confidence or not text.strip():
                continue
            normalized.append((top, left, text.strip(), score))

        # Most RapidOCR builds already return reading order. Sorting by top/left
        # makes output deterministic for gateways/backends that do not.
        normalized.sort(key=lambda row: (round(row[0] / 12.0), row[1], row[0]))
        blocks = tuple(OcrBlock(text=text, confidence=score) for _, _, text, score in normalized)
        text = "\n".join(block.text for block in blocks).strip()
        return text, blocks

    @staticmethod
    def _extract_records(raw: Any) -> Iterable[Any]:
        if raw is None:
            return ()

        # rapidocr_onnxruntime 1.x commonly returns: (result, elapsed)
        if isinstance(raw, tuple) and raw:
            first = raw[0]
            if first is None:
                return ()
            if isinstance(first, (list, tuple)):
                return first

        if isinstance(raw, list):
            return raw

        # Defensive support for object-style wrappers used by newer forks.
        for attr in ("result", "results", "boxes"):
            value = getattr(raw, attr, None)
            if isinstance(value, (list, tuple)):
                return value
        return ()

    @staticmethod
    def _parse_record(item: Any) -> tuple[float, float, str, float] | None:
        # Canonical item: [box, text, score]
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            box, text, score = item[0], item[1], item[2]
            try:
                confidence = float(score)
            except (TypeError, ValueError):
                confidence = 0.0
            top, left = RapidOcrEngine._box_origin(box)
            return top, left, str(text), confidence

        # Object/dict fallbacks are intentionally small and non-magical.
        if isinstance(item, dict):
            text = item.get("text") or item.get("txt") or ""
            score = item.get("score", item.get("confidence", 0.0))
            box = item.get("box") or item.get("points") or ()
            try:
                confidence = float(score)
            except (TypeError, ValueError):
                confidence = 0.0
            top, left = RapidOcrEngine._box_origin(box)
            return top, left, str(text), confidence
        return None

    @staticmethod
    def _box_origin(box: Any) -> tuple[float, float]:
        xs: list[float] = []
        ys: list[float] = []
        if isinstance(box, (list, tuple)):
            for point in box:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    try:
                        xs.append(float(point[0]))
                        ys.append(float(point[1]))
                    except (TypeError, ValueError):
                        continue
        return (min(ys) if ys else 0.0, min(xs) if xs else 0.0)

    def close(self) -> None:
        self._engine = None
