from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import AppConfig


class ConfigStreamingOverrideTests(unittest.TestCase):
    def test_loads_profile_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "translation": {
                    "streaming": {"ultra_fast": True, "fast": False, "quality": False}
                },
                "providers": {
                    "active_profile": "p",
                    "profiles": {
                        "p": {
                            "type": "mock",
                            "model": "m",
                            "streaming_override": {
                                "ultra_fast": False,
                                "fast": True
                            }
                        }
                    }
                }
            }), encoding="utf-8")
            with patch.dict(os.environ, {"APP_CONFIG_PATH": str(path)}):
                config = AppConfig.load()
            profile = config.providers.profiles["p"]
            self.assertFalse(profile.streaming_override_for("ultra_fast"))
            self.assertTrue(profile.streaming_override_for("fast"))
            self.assertIsNone(profile.streaming_override_for("quality"))

    def test_invalid_override_value_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "providers": {
                    "active_profile": "p",
                    "profiles": {
                        "p": {
                            "type": "mock",
                            "model": "m",
                            "streaming_override": {"fast": 123}
                        }
                    }
                }
            }), encoding="utf-8")
            with patch.dict(os.environ, {"APP_CONFIG_PATH": str(path)}):
                with self.assertRaises(ValueError):
                    AppConfig.load()


if __name__ == "__main__":
    unittest.main()
