from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from app import config


class PackagedConfigTests(unittest.TestCase):
    def test_frozen_root_is_beside_executable_and_source_root_is_project(self):
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "executable", "D:/My Apps/Translator/ScreenTranslator.exe"), \
             patch.dict(os.environ, {"LOCALAPPDATA": "C:/Users/Test/AppData/Local"}):
            self.assertEqual(config.application_root(), Path(sys.executable).resolve().parent)
        with patch.object(sys, "frozen", False, create=True):
            self.assertEqual(config.application_root(), Path(config.__file__).resolve().parent.parent)

    def test_packaged_first_run_is_keyless_and_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sys, "frozen", True, create=True), \
             patch.object(config, "PROJECT_ROOT", Path(tmp)), \
             patch.dict(os.environ, {"APP_CONFIG_PATH": "", "PROVIDER_CATALOG_PATH": "", "PROMPT_CATALOG_PATH": ""}):
            loaded = config.AppConfig.load()
            self.assertEqual(loaded.providers.active_profile, "Google Translate Free")
            self.assertEqual(loaded.providers.active()[1].api_key, "")
            self.assertEqual(loaded.data_dir, Path(tmp) / "data")
            for name in ("config.json", "providers.json", "prompts.json"):
                self.assertTrue((Path(tmp) / name).is_file())
            path = Path(tmp) / "config.json"
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["translation"]["target_language"] = "en"
            path.write_text(json.dumps(raw), encoding="utf-8")
            self.assertEqual(config.AppConfig.load().translation.target_language, "en")

    def test_frozen_explicit_config_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sys, "frozen", True, create=True):
            path = Path(tmp) / "custom.json"
            path.write_text('{"translation": {"target_language": "en"}}', encoding="utf-8")
            with patch.dict(os.environ, {"APP_CONFIG_PATH": str(path)}):
                self.assertEqual(config.AppConfig.load().translation.target_language, "en")
            self.assertFalse((Path(tmp) / "providers.json").exists())

    def test_reinstall_seeds_config_without_overwriting_retained_catalogs(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sys, "frozen", True, create=True), \
             patch.object(config, "PROJECT_ROOT", Path(tmp)), \
             patch.dict(os.environ, {"APP_CONFIG_PATH": "", "PROVIDER_CATALOG_PATH": "", "PROMPT_CATALOG_PATH": ""}):
            saved = {}
            for name in ("providers.json", "prompts.json"):
                saved[name] = (Path(config.__file__).parent / "defaults" / name).read_bytes() + b"\n "
                (Path(tmp) / name).write_bytes(saved[name])
            config.AppConfig.load()
            self.assertTrue((Path(tmp) / "config.json").is_file())
            for name, content in saved.items():
                self.assertEqual((Path(tmp) / name).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
