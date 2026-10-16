from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.cache import TranslationCache


class TranslationCacheTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = TranslationCache(Path(tmp) / "cache.sqlite3", enabled=True)
            key = cache.make_key("hello", "en", "vi", "engineering", "mock", "m1", "v2")
            self.assertIsNone(cache.get(key))
            cache.put(key, "hello", "xin chao", "en", "vi", "engineering", "mock", "m1", "v2")
            self.assertEqual(cache.get(key), "xin chao")
            self.assertEqual(cache.count(), 1)

    def test_metadata_changes_cache_key(self) -> None:
        key_vi = TranslationCache.make_key("hello", "en", "vi", "general", "p", "m1", "v2")
        key_zh = TranslationCache.make_key("hello", "en", "zh-Hant", "general", "p", "m1", "v2")
        self.assertNotEqual(key_vi, key_zh)
