from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.services.provider_catalog import ProviderCatalogStore


class PortableProviderCatalogTests(unittest.TestCase):
    def test_catalog_store_writes_exact_three_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            store = ProviderCatalogStore(path)
            store.replace_all(
                {
                    "VietAPI": {
                        "base_url": "https://api.example.test/v1",
                        "api_key": "secret",
                        "models": ["m1", "m2"],
                        "endpoint_mode": "responses",  # must not leak to portable file
                        "streaming_override": {"fast": True},
                    }
                }
            )
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(raw["VietAPI"]), {"base_url", "api_key", "models"})
            self.assertEqual(raw["VietAPI"]["models"], ["m1", "m2"])

    def test_app_config_merges_catalog_with_app_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers.json").write_text(
                json.dumps(
                    {
                        "VietAPI": {
                            "base_url": "https://api.example.test/v1",
                            "api_key": "secret",
                            "models": ["m1", "m2"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "providers": {
                            "catalog_path": "providers.json",
                            "active_profile": "VietAPI",
                            "profile_overrides": {
                                "VietAPI": {
                                    "model": "m2",
                                    "endpoint_mode": "chat_completions",
                                    "streaming_override": {"ultra_fast": False},
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            previous = os.environ.get("APP_CONFIG_PATH")
            os.environ["APP_CONFIG_PATH"] = str(root / "config.json")
            try:
                config = AppConfig.load()
            finally:
                if previous is None:
                    os.environ.pop("APP_CONFIG_PATH", None)
                else:
                    os.environ["APP_CONFIG_PATH"] = previous

            profile = config.providers.profiles["VietAPI"]
            self.assertEqual(profile.base_url, "https://api.example.test/v1")
            self.assertEqual(profile.api_key, "secret")
            self.assertEqual(profile.available_models(), ("m1", "m2"))
            self.assertEqual(profile.model, "m2")
            self.assertEqual(profile.endpoint_mode, "chat_completions")
            self.assertFalse(profile.streaming_override_for("ultra_fast"))

    def test_missing_active_profile_falls_back_to_first_catalog_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers.json").write_text(
                json.dumps(
                    {
                        "A": {"base_url": "https://a.test/v1", "api_key": "x", "models": ["m"]},
                        "B": {"base_url": "https://b.test/v1", "api_key": "y", "models": ["n"]},
                    }
                ),
                encoding="utf-8",
            )
            (root / "config.json").write_text(
                json.dumps({"providers": {"catalog_path": "providers.json", "active_profile": "missing"}}),
                encoding="utf-8",
            )
            previous = os.environ.get("APP_CONFIG_PATH")
            os.environ["APP_CONFIG_PATH"] = str(root / "config.json")
            try:
                config = AppConfig.load()
            finally:
                if previous is None:
                    os.environ.pop("APP_CONFIG_PATH", None)
                else:
                    os.environ["APP_CONFIG_PATH"] = previous
            self.assertEqual(config.providers.active_profile, "A")


class PortableCatalogIntegrationSourceTests(unittest.TestCase):
    def test_controller_saves_portable_catalog_and_app_overrides_separately(self) -> None:
        root = Path(__file__).parents[1]
        source = (root / "app" / "controller.py").read_text(encoding="utf-8")
        self.assertIn("self._provider_catalog_store.replace_all(portable_catalog)", source)
        self.assertIn('"profile_overrides"', source)
        self.assertIn("portable_provider_entry", source)


if __name__ == "__main__":
    unittest.main()
