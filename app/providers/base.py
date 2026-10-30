from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from app.models import TranslationRequest


class TranslationProvider(ABC):
    supports_explain = False

    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def translate(self, request: TranslationRequest, instructions: str) -> str:
        raise NotImplementedError

    def translate_stream(
        self,
        request: TranslationRequest,
        instructions: str,
        on_delta: Callable[[str], None],
    ) -> str:
        """
        Optional streaming interface.

        Providers without native streaming support remain compatible: they run a
        normal translation and emit the completed text as one delta.
        """
        text = self.translate(request, instructions)
        if text:
            on_delta(text)
        return text

    def streaming_override_for(self, performance_mode: str) -> bool | None:
        """Return a per-profile streaming override, or None to use global config."""
        del performance_mode
        return None
