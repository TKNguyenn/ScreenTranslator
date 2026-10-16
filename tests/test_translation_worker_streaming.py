from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import TranslationSection
from app.models import RequestMode, TranslationRequest
from app.providers.base import TranslationProvider
from app.services.cache import TranslationCache
from app.workers.translation_worker import TranslationWorker


class FakeProvider(TranslationProvider):
    def __init__(self, overrides=None) -> None:
        self.normal_calls = 0
        self.stream_calls = 0
        self.overrides = dict(overrides or {})

    @property
    def provider_id(self) -> str:
        return "fake"

    @property
    def model_id(self) -> str:
        return "fake-model"

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        self.normal_calls += 1
        return "xin chao"

    def translate_stream(self, request, instructions, on_delta):
        self.stream_calls += 1
        on_delta("xin ")
        on_delta("chao")
        return "xin chao"

    def streaming_override_for(self, performance_mode: str):
        return self.overrides.get(performance_mode)


def make_request(performance_mode: str) -> TranslationRequest:
    return TranslationRequest(
        job_id=f"job-{performance_mode}",
        source_text="hello",
        source_language="en",
        target_language="vi",
        context_preset="engineering",
        performance_mode=performance_mode,
        mode=RequestMode.POPUP,
        foreground_hwnd=None,
    )


class TranslationWorkerStreamingTests(unittest.TestCase):
    def test_only_enabled_mode_uses_streaming(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider()
            results = []
            progress = []
            config = TranslationSection(
                cache_enabled=False,
                streaming={
                    "ultra_fast": True,
                    "fast": False,
                    "quality": False,
                },
            )
            worker = TranslationWorker(
                provider=provider,
                cache=TranslationCache(Path(tmp) / "cache.sqlite3", enabled=False),
                config=config,
                on_result=results.append,
                on_progress=progress.append,
            )

            worker._translate(make_request("ultra_fast"))
            worker._translate(make_request("fast"))
            worker._translate(make_request("quality"))

            self.assertEqual(provider.stream_calls, 1)
            self.assertEqual(provider.normal_calls, 2)
            self.assertEqual([item.delta_text for item in progress], ["xin ", "chao"])
            self.assertEqual(len(results), 3)

    def test_streaming_can_be_enabled_for_all_three_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider()
            config = TranslationSection(
                cache_enabled=False,
                streaming={
                    "ultra_fast": True,
                    "fast": True,
                    "quality": True,
                },
            )
            worker = TranslationWorker(
                provider=provider,
                cache=TranslationCache(Path(tmp) / "cache.sqlite3", enabled=False),
                config=config,
                on_result=lambda result: None,
                on_progress=lambda progress: None,
            )

            for mode in ("ultra_fast", "fast", "quality"):
                worker._translate(make_request(mode))

            self.assertEqual(provider.stream_calls, 3)
            self.assertEqual(provider.normal_calls, 0)

    def test_profile_override_wins_over_global_streaming(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider(overrides={"ultra_fast": False, "fast": True})
            config = TranslationSection(
                cache_enabled=False,
                streaming={
                    "ultra_fast": True,
                    "fast": False,
                    "quality": False,
                },
            )
            worker = TranslationWorker(
                provider=provider,
                cache=TranslationCache(Path(tmp) / "cache.sqlite3", enabled=False),
                config=config,
                on_result=lambda result: None,
                on_progress=lambda progress: None,
            )
            worker._translate(make_request("ultra_fast"))
            worker._translate(make_request("fast"))
            worker._translate(make_request("quality"))
            self.assertEqual(provider.stream_calls, 1)
            self.assertEqual(provider.normal_calls, 2)

    def test_runtime_reload_replaces_translation_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider()
            worker = TranslationWorker(
                provider=provider,
                cache=TranslationCache(Path(tmp) / "cache.sqlite3", enabled=False),
                config=TranslationSection(
                    cache_enabled=False,
                    streaming={"ultra_fast": False, "fast": False, "quality": False},
                ),
                on_result=lambda result: None,
                on_progress=lambda progress: None,
            )
            replacement = FakeProvider()
            worker._reload_runtime(
                replacement,
                TranslationSection(
                    cache_enabled=False,
                    streaming={"ultra_fast": True, "fast": False, "quality": False},
                ),
            )
            worker._translate(make_request("ultra_fast"))
            self.assertEqual(replacement.stream_calls, 1)
            self.assertEqual(provider.stream_calls, 0)


if __name__ == "__main__":
    unittest.main()
