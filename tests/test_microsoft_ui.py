import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_google_ui
from app.config import provider_profile_from_dict, portable_provider_entry
from app.services.provider_catalog import ProviderCatalogStore
from microsoft_translator import UsageEvent
from microsoft_translator_usage import LocalUsageLedger


class MicrosoftUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_google_ui.GoogleUiTests.setUpClass.__func__(cls)

    def setUp(self):
        test_google_ui.GoogleUiTests.setUp(self)
        from dataclasses import replace
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.window._config = replace(self.config, app=replace(self.config.app, data_dir=self.tmp.name))

    def close(self):
        test_google_ui.GoogleUiTests.close(self)

    def test_microsoft_editor_saves_and_switches_back_to_ai(self):
        from PySide6.QtWidgets import QPushButton
        buttons = {b.text(): b for b in self.window.findChildren(QPushButton)}
        buttons['+ Microsoft'].click()
        self.assertEqual(self.window._active_profile_combo.currentText(), 'AI')
        self.assertTrue(self.window._models_group.isHidden())
        self.assertTrue(self.window._stream_group.isHidden())
        self.assertFalse(self.window._microsoft_usage_group.isHidden())
        self.assertEqual(self.window._region_edit.text(), 'southeastasia')
        self.assertTrue(self.window._api_key_edit.isEnabled())
        self.window._region_edit.setText('eastasia')
        self.window._api_key_edit.setText('synthetic-key')
        self.window._commit_current_form()
        saved = self.window._working_profiles['Microsoft Translator']
        with tempfile.TemporaryDirectory() as tmp:
            store = ProviderCatalogStore(Path(tmp) / 'providers.json')
            store.replace_all({'Renamed MS': saved})
            restored = provider_profile_from_dict(store.read()['Renamed MS'])
        self.assertEqual(restored.region, 'eastasia')
        self.assertEqual(restored.type, 'microsoft_translator')
        self.assertFalse(hasattr(self.window, '_azure_usage_group'))
        self.assertFalse(hasattr(self.window, '_azure_resource_edit'))
        self.assertNotIn('Connect Microsoft', buttons)
        self.window._load_provider_form('AI')
        self.assertFalse(self.window._models_group.isHidden())
        self.assertFalse(self.window._stream_group.isHidden())
        self.assertTrue(self.window._region_edit.isHidden())
        self.assertTrue(self.window._microsoft_usage_group.isHidden())

    def test_monthly_usage_refresh_and_direct_runtime_ui(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as tmp:
            self.window._config = replace(self.config, app=replace(self.config.app, data_dir=tmp))
            self.window._add_microsoft_provider()
            ledger = LocalUsageLedger(Path(tmp) / 'microsoft_usage.sqlite3')
            ledger.record(UsageEvent('one', 'en', ('vi',), 125, 'header'))
            self.window.refresh_microsoft_usage()
            self.assertIn('125', self.window._microsoft_usage_status.text())
            profile = provider_profile_from_dict(self.window._working_profiles['Microsoft Translator'])
            self.window.update_runtime_state('MS', {'MS': profile}, 'vi', 'email', 'quality', True)
            self.assertFalse(self.window._prompt_editor.isEnabled())
            self.assertIn('Microsoft', self.window._google_prompt_note.text())
            self.assertEqual(self.window._overview_performance.text(), 'Dịch trực tiếp')

    def test_compact_microsoft_layout_renders(self):
        self.window._add_microsoft_provider()
        self.window.resize(900, 620)
        self.window._nav.setCurrentRow(1)
        self.window.show()
        self.app.processEvents()
        page = self.window._pages.widget(1)
        self.assertLessEqual(page.widget().minimumSizeHint().width(), page.viewport().width())
