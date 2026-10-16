from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import TranslationSection
from app.models import RequestMode, TranslationRequest
from app.providers.base import TranslationProvider
from app.services.cache import TranslationCache
from app.workers.translation_worker import TranslationWorker


class PromptEchoProvider(TranslationProvider):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return "prompt-echo"

    @property
    def model_id(self) -> str:
        return "echo-v1"

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        self.calls += 1
        return instructions


def make_request() -> TranslationRequest:
    return TranslationRequest(
        job_id="job",
        source_text="hello",
        source_language="en",
        target_language="vi",
        context_preset="engineering",
        performance_mode="fast",
        mode=RequestMode.POPUP,
        foreground_hwnd=None,
    )


class TranslationWorkerCustomPromptTests(unittest.TestCase):
    def test_prompt_change_invalidates_translation_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = PromptEchoProvider()
            results = []
            worker = TranslationWorker(
                provider=provider,
                cache=TranslationCache(Path(tmp) / "cache.sqlite3", enabled=True),
                config=TranslationSection(prompt_version="v5", cache_enabled=True),
                on_result=results.append,
                prompt_overrides={},
            )
            worker._translate(make_request())
            worker._translate(make_request())
            self.assertEqual(provider.calls, 1)
            self.assertTrue(results[-1].cached)

            worker._prompt_overrides = {
                "fast": {"engineering": "CUSTOM -> {target_language}"}
            }
            worker._translate(make_request())
            self.assertEqual(provider.calls, 2)
            self.assertIn("CUSTOM", results[-1].translated_text)
            self.assertFalse(results[-1].cached)


if __name__ == "__main__":
    unittest.main()
