from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.config_store import ConfigFileStore


class ConfigFileStoreTests(unittest.TestCase):
    def test_update_cache_enabled_preserves_other_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "translation": {"cache_enabled": True, "performance_mode": "fast"},
                        "providers": {"active_profile": "mock"},
                    }
                ),
                encoding="utf-8",
            )

            store = ConfigFileStore(path)
            store.update_nested(("translation", "cache_enabled"), False)

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(data["translation"]["cache_enabled"])
            self.assertEqual(data["translation"]["performance_mode"], "fast")
            self.assertEqual(data["providers"]["active_profile"], "mock")
