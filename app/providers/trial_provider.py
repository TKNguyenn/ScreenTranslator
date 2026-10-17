import logging
from collections.abc import Callable

from app.models import TranslationRequest
from app.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.services.trial_usage import TrialUsageStore

logger = logging.getLogger(__name__)


class TrialProvider(OpenAICompatibleProvider):
    def __init__(self, profile_name, profile, usage: TrialUsageStore, **kwargs):
        super().__init__(profile_name, profile, **kwargs)
        self._trial_usage = usage

    def _record_usage(self) -> None:
        try:
            self._trial_usage.record(self._api_key, self.model_id)
        except (OSError, ValueError):
            # A local estimate write failure must not discard a successful translation.
            logger.warning("Unable to save Trial usage estimate", exc_info=True)

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        text = super().translate(request, instructions)
        self._record_usage()
        return text

    def translate_stream(self, request: TranslationRequest, instructions: str, on_delta: Callable[[str], None]) -> str:
        text = super().translate_stream(request, instructions, on_delta)
        self._record_usage()
        return text
