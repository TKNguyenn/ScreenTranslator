from __future__ import annotations

from app.models import TranslationRequest
from app.providers.base import TranslationProvider


class UnavailableTranslationProvider(TranslationProvider):
    """Keeps the app alive when provider configuration is invalid."""

    def __init__(self, error_message: str, model: str = "unavailable") -> None:
        self._error_message = error_message
        self._model = model or "unavailable"

    @property
    def provider_id(self) -> str:
        return "unavailable"

    @property
    def model_id(self) -> str:
        return self._model

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        del request, instructions
        raise RuntimeError(self._error_message)
