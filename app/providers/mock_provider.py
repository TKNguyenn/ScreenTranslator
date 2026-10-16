from __future__ import annotations

from app.models import TranslationRequest
from app.providers.base import TranslationProvider


class MockTranslationProvider(TranslationProvider):
    """Offline provider used for UI/architecture smoke tests."""

    def __init__(self, model: str = "mock-v2", streaming_override: dict[str, bool] | None = None) -> None:
        self._model = model
        self._streaming_override = dict(streaming_override or {})

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return self._model

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        del instructions
        return f"[MOCK {request.target_language}] {request.source_text}"

    def streaming_override_for(self, performance_mode: str) -> bool | None:
        mode = str(performance_mode).strip().lower()
        if mode not in self._streaming_override:
            return None
        return bool(self._streaming_override[mode])
