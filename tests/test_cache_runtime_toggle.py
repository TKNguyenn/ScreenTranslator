from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.cache import TranslationCache


class CacheRuntimeToggleTests(unittest.TestCase):
    def test_disable_bypasses_existing_cache_and_reenable_restores_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = TranslationCache(Path(tmp) / "cache.sqlite3", enabled=True)
            key = cache.make_key("hello", "en", "vi", "chat", "mock", "m1", "v4:fast")
            cache.put(key, "hello", "xin chao", "en", "vi", "chat", "mock", "m1", "v4:fast")
            self.assertEqual(cache.get(key), "xin chao")

            cache.set_enabled(False)
            self.assertFalse(cache.enabled)
            self.assertIsNone(cache.get(key))

            cache.set_enabled(True)
            self.assertTrue(cache.enabled)
            self.assertEqual(cache.get(key), "xin chao")

    def test_enable_after_starting_disabled_initializes_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.sqlite3"
            cache = TranslationCache(path, enabled=False)
            self.assertFalse(path.exists())
            cache.set_enabled(True)
            self.assertTrue(path.exists())
