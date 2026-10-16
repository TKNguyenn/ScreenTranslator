from __future__ import annotations

import os
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtGui import QFontDatabase
from app.config import AppConfig, ProviderProfile, ProviderSection
from app.controller import AppController
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from app.services.provider_catalog import ProviderCatalogStore
from app.config import portable_provider_entry, provider_profile_from_dict
from pathlib import Path
import tempfile


class GoogleUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Windows offscreen Qt has no system font database; use the real UI font.
        if os.name == "nt" and cls.app.platformName() == "offscreen":
            for filename in ("segoeui.ttf", "seguisb.ttf"):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename))
        apply_theme(cls.app)

    def setUp(self):
        self.config = AppConfig(providers=ProviderSection(active_profile="AI", profiles={
            "AI": ProviderProfile(model="test-model", api_key="test-key",
                                  streaming_override={"quality": True}),
        }))
        self.window = MainWindow(self.app, self.config)
        self.addCleanup(self.close)

    def close(self):
        self.window.allow_close()
        self.window.close()

    def test_presets_added_through_buttons_without_overwriting_or_switching_active(self):
        original = deepcopy(self.window._working_profiles["AI"])
        buttons = {b.text(): b for b in self.window.findChildren(QPushButton)}
        self.assertIn("+ Google Free", buttons)
        self.assertIn("+ Google Cloud", buttons)
        buttons["+ Google Free"].click()
        buttons["+ Google Cloud"].click()
        self.assertEqual(self.window._active_profile_combo.currentText(), "AI")
        self.assertEqual(self.window._working_profiles["AI"], original)
        self.assertEqual(self.window._working_profiles["Google Translate Free"]["type"], "google_translate_web")
        self.window._api_key_edit.setText("user-cloud-key")
        buttons["+ Google Cloud"].click()
        self.assertEqual(self.window._api_key_edit.text(), "user-cloud-key")
        self.assertEqual(len(self.window._working_profiles), 3)
        saves = []
        self.window.save_providers_requested.connect(lambda p, a: saves.append((p, a)))
        self.window._save_and_apply()
        self.assertEqual(saves[0][1], "AI")
        self.assertEqual(saves[0][0]["Google Cloud Translate"]["api_key"], "user-cloud-key")

    def test_google_controls_and_prompt_disabled_then_restored_for_ai(self):
        self.window._add_google_provider("Google Translate Free")
        self.assertFalse(self.window._api_key_edit.isEnabled())
        self.assertFalse(self.window._endpoint_combo.isEnabled())
        self.assertFalse(self.window._stream_quality.isEnabled())
        self.assertFalse(self.window._active_model_combo.isEnabled())
        self.assertTrue(self.window._models_list.parentWidget().isHidden())
        self.assertTrue(self.window._stream_quality.parentWidget().isHidden())
        self.window._add_google_provider("Google Cloud Translate")
        self.assertTrue(self.window._models_list.parentWidget().isHidden())
        self.assertTrue(self.window._stream_quality.parentWidget().isHidden())
        self.window.update_runtime_state("Google Translate Free",
            {"Google Translate Free": ProviderProfile(type="google_translate_web", model="google-translate")},
            "vi", "email", "quality", True)
        self.assertFalse(self.window._prompt_editor.isEnabled())
        self.assertTrue(self.window._google_prompt_note.isVisibleTo(self.window._google_prompt_note.parentWidget()))
        self.window._provider_list.setCurrentRow(0)
        self.window.update_runtime_state("AI", self.config.providers.profiles, "vi", "email", "quality", True)
        self.assertTrue(self.window._stream_quality.isEnabled())
        self.assertTrue(self.window._prompt_editor.isEnabled())
        self.assertEqual(self.window._stream_quality.currentData(), True)
        self.assertFalse(self.window._models_list.parentWidget().isHidden())
        self.assertFalse(self.window._stream_quality.parentWidget().isHidden())

    def test_type_selection_configures_google_defaults_and_compact_layout_fits(self):
        self.window._type_combo.setCurrentText("google_cloud_translate")
        self.assertEqual(self.window._base_url_edit.text(), "https://translation.googleapis.com")
        self.assertEqual(self.window._active_model_combo.currentText(), "nmt")
        self.assertTrue(self.window._api_key_edit.isEnabled())
        self.window.resize(900, 620)
        self.window._nav.setCurrentRow(1)
        self.window.show()
        self.app.processEvents()
        page = self.window._pages.widget(1)
        self.assertLessEqual(page.widget().minimumSizeHint().width(), page.viewport().width())
        buttons = {b.text(): b for b in self.window.findChildren(QPushButton)}
        self.assertEqual(buttons["+ Google Free"].y(), buttons["Import providers.json"].y())
        self.assertEqual(buttons["+ Google Cloud"].y(), buttons["Export providers.json"].y())

    def test_google_can_be_renamed_removed_and_saved_portably(self):
        self.window._add_google_provider("Google Translate Free")
        with patch("app.ui.main_window.QInputDialog.getText", return_value=("My Free", True)):
            self.window._rename_provider()
        saves = []
        self.window.save_providers_requested.connect(lambda p, a: saves.append((p, a)))
        self.window._save_and_apply()
        with tempfile.TemporaryDirectory() as tmp:
            store = ProviderCatalogStore(Path(tmp) / "providers.json")
            store.replace_all({name: portable_provider_entry(profile) for name, profile in saves[0][0].items()})
            saved = store.read()
            self.assertEqual(set(saved["My Free"]), {"base_url", "api_key", "models"})
            self.assertEqual(provider_profile_from_dict(saved["My Free"]).type, "google_translate_web")
        from PySide6.QtWidgets import QMessageBox
        with patch("app.ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
            self.window._delete_provider()
        self.assertEqual(set(self.window._working_profiles), {"AI"})


class GoogleControllerTests(unittest.TestCase):
    def test_effective_streaming_for_google_always_off(self):
        controller = SimpleNamespace(_config=AppConfig(), _performance_mode="ultra_fast",
            _profile=ProviderProfile(type="google_translate_web", streaming_override={"ultra_fast": True}))
        self.assertEqual(AppController._effective_streaming(controller), (False, "provider"))

    def test_provider_test_sends_real_translation_and_closes_client(self):
        class Provider:
            closed = False
            def translate(self, req, instructions):
                self.req, self.instructions = req, instructions
                return "Xin chào"
            def close(self):
                self.closed = True
        provider = Provider()
        results = []
        controller = SimpleNamespace(_config=AppConfig(), _bridge=SimpleNamespace(
            provider_test_result=SimpleNamespace(emit=results.append)))
        with patch("app.controller.create_translation_provider", return_value=provider):
            AppController._run_provider_test(controller, "Free", {"type": "google_translate_web",
                "base_url": "https://translate.googleapis.com", "model": "google-translate"})
        self.assertEqual(provider.req.source_text, "Hello")
        self.assertEqual(provider.req.target_language, "vi")
        self.assertNotIn("Reply exactly: OK", provider.instructions)
        self.assertTrue(provider.closed)
        self.assertTrue(results[0]["success"])


if __name__ == "__main__":
    unittest.main()
