from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import OcrBlock


class OcrEngine(ABC):
    @property
    @abstractmethod
    def engine_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def recognize(self, image_png: bytes) -> tuple[str, tuple[OcrBlock, ...]]:
        """Return normalized OCR text plus recognized blocks."""
        raise NotImplementedError

    def close(self) -> None:
        """Release engine resources if the backend owns any."""
