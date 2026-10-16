from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from app.config import TranslationSection
from app.models import RequestMode, TranslationRequest
from app.providers.base import TranslationProvider
from app.services.cache import TranslationCache
from app.workers.translation_worker import TranslationWorker


class NamedProvider(TranslationProvider):
    def __init__(self, name: str) -> None:
        self._name = name
        self.closed = False

    @property
    def provider_id(self) -> str:
        return f"test:{self._name}"

    @property
    def model_id(self) -> str:
        return self._name

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        del instructions
        return f"{self._name}:{request.source_text}"

    def close(self) -> None:
        self.closed = True


class ProviderSwitchTests(unittest.TestCase):
    def test_provider_switch_is_ordered_before_later_translation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = NamedProvider("old")
            new = NamedProvider("new")
            results = []
            event = threading.Event()

            def on_result(result):
                results.append(result)
                event.set()

            worker = TranslationWorker(
                provider=old,
                cache=TranslationCache(Path(tmp) / "cache.sqlite3", enabled=True),
                config=TranslationSection(),
                on_result=on_result,
            )
            worker.start()
            worker.replace_provider(new)
            worker.submit(
                TranslationRequest(
                    job_id="1",
                    source_text="hello",
                    source_language="auto",
                    target_language="vi",
                    context_preset="engineering",
                    performance_mode="fast",
                    mode=RequestMode.POPUP,
                    foreground_hwnd=None,
                )
            )

            self.assertTrue(event.wait(2.0))
            worker.stop()

            self.assertEqual(results[0].translated_text, "new:hello")
            self.assertTrue(old.closed)
            self.assertTrue(new.closed)


if __name__ == "__main__":
    unittest.main()
