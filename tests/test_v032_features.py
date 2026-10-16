from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class V032FeatureSourceTests(unittest.TestCase):
    def test_main_window_has_prompt_editor_for_speed_and_style(self) -> None:
        source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn('self._nav.addItem("Prompt Editor")', source)
        self.assertIn('("ultra_fast", "fast", "quality")', source)
        self.assertIn('("engineering", "chat", "email")', source)
        self.assertIn("reset_all_prompts_requested", source)
        self.assertIn("Lưu tùy chỉnh", source)

    def test_provider_page_has_test_import_export(self) -> None:
        source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("Test provider / model hiện tại", source)
        self.assertIn("Import providers.json", source)
        self.assertIn("Export providers.json", source)

    def test_single_instance_guard_notifies_first_instance(self) -> None:
        source = (ROOT / "app" / "services" / "single_instance.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("QLocalServer", source)
        self.assertIn("QLocalSocket", source)
        self.assertIn('acquire_or_notify("SHOW")', main)
        self.assertIn("controller.show_main_window", main)

    def test_translation_worker_fingerprints_effective_prompt(self) -> None:
        source = (ROOT / "app" / "workers" / "translation_worker.py").read_text(encoding="utf-8")
        self.assertIn("hashlib.sha256(instructions.encode", source)
        self.assertIn("prompt_overrides=self._prompt_overrides", source)


if __name__ == "__main__":
    unittest.main()
