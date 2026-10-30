from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HotkeyAction(str, Enum):
    TRANSLATE_SELECTION = "translate_selection"
    TRANSLATE_AND_REPLACE = "translate_and_replace"
    LIVE_TOGGLE = "live_toggle"
    REGION_TRANSLATE = "region_translate"
    TARGET_VI = "target_vi"
    TARGET_EN = "target_en"
    TARGET_ZH_HANT = "target_zh_hant"


class RequestMode(str, Enum):
    POPUP = "popup"
    REPLACE = "replace"
    REGION = "region"
    EXPLAIN = "explain"


@dataclass(frozen=True)
class SelectionResult:
    job_id: str
    text: str
    foreground_hwnd: Optional[int]
    error: Optional[str] = None


@dataclass(frozen=True)
class PasteResult:
    job_id: str
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class RegionCaptureResult:
    """PNG bytes captured from one screen region.

    V0.4.0 intentionally captures one monitor at a time. ``width_px`` and
    ``height_px`` describe the actual PNG pixel dimensions after Qt/DPI mapping.
    """

    job_id: str
    image_png: bytes
    screen_name: str
    width_px: int
    height_px: int
    error: Optional[str] = None


@dataclass(frozen=True)
class OcrBlock:
    text: str
    confidence: float


@dataclass(frozen=True)
class OcrResult:
    job_id: str
    text: str
    blocks: tuple[OcrBlock, ...] = ()
    error: Optional[str] = None


@dataclass(frozen=True)
class TranslationRequest:
    job_id: str
    source_text: str
    source_language: str
    target_language: str
    context_preset: str
    performance_mode: str
    mode: RequestMode
    foreground_hwnd: Optional[int]


@dataclass(frozen=True)
class TranslationProgress:
    """One streaming text delta for an in-flight translation request."""

    request: TranslationRequest
    delta_text: str


@dataclass(frozen=True)
class TranslationResult:
    request: TranslationRequest
    translated_text: str
    cached: bool
    error: Optional[str] = None
