from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontDatabase, QKeySequence
    from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QScrollArea
    from app.config import AppConfig, FeatureSection, ProviderProfile, ProviderSection, parse_hotkey_section
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_theme, asset_icon
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "PySide6 required")
class OceanUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        if os.name == "nt" and cls.app.platformName() == "offscreen":
            for filename in ("segoeui.ttf", "seguisb.ttf"):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename))
        apply_theme(cls.app)

    def setUp(self):
        self.config = AppConfig(providers=ProviderSection(active_profile="Test Provider", profiles={
            "Test Provider": ProviderProfile(model="test-model", api_key="synthetic-key"),
        }))
        self.window = MainWindow(self.app, self.config)
        self.window.show()
        self.app.processEvents()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.window.allow_close()
        self.window.close()

    def test_all_navigation_pages_preserved_and_icons_loaded(self):
        self.assertFalse(asset_icon().isNull())
        self.assertEqual(self.window._nav.count(), 7)
        for index in range(7):
            self.assertFalse(self.window._nav.item(index).icon().isNull())
            self.window._nav.setCurrentRow(index)
            self.assertEqual(self.window._pages.currentIndex(), index)

    def test_overview_shows_runtime_state_and_capture_emits_action(self):
        self.window.update_runtime_state("Test Provider", self.config.providers.profiles,
                                          "en", "chat", "quality", False)
        self.assertEqual(self.window._overview_model.text(), "test-model")
        self.assertEqual(self.window._overview_provider.text(), "Test Provider")
        self.assertEqual(self.window._overview_target.text(), "English")
        self.assertIn("Chat", self.window._overview_style.text())
        requests = []
        self.window.region_translate_requested.connect(lambda: requests.append(True))
        self.window._overview_region_button.click()
        self.assertEqual(requests, [True])

    def test_disabled_region_applies_to_overview_cta_too(self):
        from dataclasses import replace
        disabled = replace(self.config, features=FeatureSection(region_translate_enabled=False))
        self.window.load_config(disabled, active_profile="Test Provider")
        self.assertFalse(self.window._overview_region_button.isEnabled())
        self.assertFalse(self.window._region_translate_button.isEnabled())

    def test_provider_key_remains_masked_and_save_signal_preserved(self):
        self.assertEqual(self.window._api_key_edit.echoMode(), QLineEdit.Password)
        saves = []
        self.window.save_providers_requested.connect(lambda profiles, active: saves.append((profiles, active)))
        self.window._save_and_apply()
        self.assertEqual(len(saves), 1)
        self.assertEqual(saves[0][1], "Test Provider")

    def test_quick_settings_emit_without_writing_config(self):
        saved = []
        self.window.quick_ux_settings_requested.connect(saved.append)
        self.window._quick_delay.setValue(350)
        self.window._save_quick_ux()
        self.assertEqual(saved[0]["selection_delay_ms"], 350)

    def test_hotkey_settings_emit_and_validate(self):
        saved = []
        self.window.hotkeys_settings_requested.connect(saved.append)
        self.window._nav.setCurrentRow(6)
        self.window._hotkey_edits["translate_selection"].setKeySequence(QKeySequence("Ctrl+T"))
        self.window._save_hotkeys()
        self.assertEqual(saved[0]["translate_selection"], "ctrl+t")
        with self.assertRaises(ValueError):
            parse_hotkey_section({"translate_selection": "alt+t", "target_vi": "alt+t"})

    def test_compact_form_pages_scroll_and_no_horizontal_overflow(self):
        self.window.resize(900, 620)
        for index in (0, 2, 3, 4, 5, 6):
            self.window._nav.setCurrentRow(index)
            self.app.processEvents()
            page = self.window._pages.widget(index)
            self.assertIsInstance(page, QScrollArea)
            self.assertEqual(page.horizontalScrollBar().maximum(), 0, f"page {index} overflows")
            self.assertLessEqual(page.widget().minimumSizeHint().width(), page.viewport().width(),
                                 f"page {index} minimum width exceeds viewport")

    def test_provider_page_minimum_width_fits_compact_content_area(self):
        self.window.resize(900, 620)
        self.window._nav.setCurrentRow(1)
        self.app.processEvents()
        page = self.window._pages.widget(1)
        self.assertLessEqual(page.widget().minimumSizeHint().width(), page.viewport().width())


if __name__ == "__main__":
    unittest.main()
