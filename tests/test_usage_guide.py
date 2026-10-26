from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtGui import QContextMenuEvent, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QPushButton
from app.config import AppConfig, HotkeySection
from app.controller import AppController
from app.services.runtime_settings import RuntimeSettingsStore
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from app.ui.tray import TrayIcon


class UsageGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        if os.name == 'nt' and cls.app.platformName() == 'offscreen':
            for name in ('segoeui.ttf', 'seguisb.ttf'):
                QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR']) / 'Fonts' / name))
        apply_theme(cls.app)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.window = MainWindow(self.app, AppConfig())
        self.addCleanup(self.cleanup_windows)
        self.store = RuntimeSettingsStore(Path(self.tmp.name) / 'runtime_settings.json')
        self.controller = SimpleNamespace(
            _config=AppConfig(), _main_window=self.window, _runtime_settings=self.store,
            _usage_guide=None,
        )
        self.controller._show_usage_guide = lambda: AppController._show_usage_guide(self.controller)

    def cleanup_windows(self):
        for dialog in self.window.findChildren(QDialog):
            dialog.close()
        self.window.allow_close()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_help_button_emits_request(self):
        button = self.window.findChild(QPushButton, 'usageGuideButton')
        self.assertIsNotNone(button)
        requests = []
        self.window.usage_guide_requested.connect(lambda: requests.append(True))
        button.click()
        self.assertEqual(requests, [True])

    def test_first_start_shows_once_and_preserves_runtime_choices(self):
        self.store.update(provider_profile='fixture', target_language='en')
        AppController._show_usage_guide_on_startup(self.controller)
        guide = self.controller._usage_guide
        self.assertTrue(guide.isVisible())
        guide.reject()
        # A fresh controller/store models the next process launch.
        self.controller._usage_guide = None
        self.controller._runtime_settings = RuntimeSettingsStore(self.store._path)
        AppController._show_usage_guide_on_startup(self.controller)
        self.assertIsNone(self.controller._usage_guide)
        self.assertEqual(self.store.load(), {
            'provider_profile': 'fixture', 'target_language': 'en', 'onboarding_seen': True,
        })

    def test_tray_help_opens_real_guide(self):
        def noop(*args):
            pass

        tray = TrayIcon(
            app=self.app, provider_profiles={}, active_provider='', active_target_language='vi',
            active_performance_mode='fast', active_context_preset='engineering', cache_enabled=True,
            on_open_main_window=noop, on_translate=noop, on_translate_replace=noop,
            on_region_translate=noop, region_translate_enabled=True, quick_auto_enabled=True,
            on_quick_auto_toggle=noop, on_open_quick_settings=noop, on_target_language=noop,
            on_provider=noop, on_performance_mode=noop, on_context_preset=noop,
            on_cache_enabled=noop, on_show_diagnostics=noop, on_reload_config=noop, on_quit=noop,
            on_open_usage_guide=self.controller._show_usage_guide,
        )
        self.addCleanup(tray._tray.deleteLater)
        tray._guide_action.trigger()
        self.assertTrue(self.controller._usage_guide.isVisible())

    def test_help_reopens_at_start_and_uses_updated_shortcuts(self):
        self.controller._show_usage_guide()
        guide = self.controller._usage_guide
        guide._next.click()
        self.controller._show_usage_guide()
        self.assertIs(self.controller._usage_guide, guide)
        self.assertEqual(guide._pages.currentIndex(), 1)
        guide.reject()
        self.controller._config = replace(AppConfig(), hotkeys=replace(HotkeySection(),
            translate_selection='ctrl+alt+t', region_translate='ctrl+alt+s'))
        self.controller._show_usage_guide()
        reopened = self.controller._usage_guide
        self.assertEqual(reopened._pages.currentIndex(), 0)
        self.assertIn('Ctrl+Alt+T', reopened._note.text())
        reopened._next.click()
        self.assertIn('Ctrl+Alt+S', reopened._description.text())
        self.assertFalse(guide.isVisible())

    def test_marker_write_failure_does_not_block_guide(self):
        with patch.object(self.store, 'update', side_effect=OSError('read only')), \
                self.assertLogs('app.controller', level='WARNING'):
            self.controller._show_usage_guide()
        self.assertTrue(self.controller._usage_guide.isVisible())

    def test_failed_open_is_not_marked_as_seen(self):
        with patch('app.controller.UsageGuideDialog', side_effect=RuntimeError('fixture')), \
                self.assertLogs('app.controller', level='ERROR'):
            self.controller._show_usage_guide()
        self.assertNotIn('onboarding_seen', self.store.load())

    def test_failed_reopen_can_be_retried(self):
        self.controller._show_usage_guide()
        self.controller._usage_guide.reject()
        with patch('app.controller.UsageGuideDialog', side_effect=RuntimeError('fixture')), \
                self.assertLogs('app.controller', level='ERROR'):
            self.controller._show_usage_guide()
        self.app.processEvents()
        self.controller._show_usage_guide()
        self.assertTrue(self.controller._usage_guide.isVisible())

    def test_navigation_demos_finish_and_escape(self):
        self.controller._show_usage_guide()
        guide = self.controller._usage_guide
        self.assertFalse(guide._previous.isEnabled())
        guide.findChild(QPushButton, 'guideLanguageZh').click()
        self.assertIn('請', guide.findChild(QLabel, 'guideTranslation').text())
        guide._next.click()
        guide.findChild(QPushButton, 'guideOcrDemo').click()
        self.assertTrue(guide.findChild(QLabel, 'guideOcrResult').isVisible())
        guide._next.click()
        guide.findChild(QPushButton, 'guideReplaceDemo').click()
        self.assertIn('Please check', guide.findChild(QLabel, 'guideDraft').text())
        self.assertIn('Chưa gửi', guide.findChild(QLabel, 'guideDraftStatus').text())
        guide._next.click()
        pin = guide.findChild(QPushButton, 'guidePinDemo')
        pin.click()
        self.assertTrue(pin.isChecked())
        guide.findChild(QPushButton, 'guideCopyDemo').click()
        self.assertIn('Vui lòng', self.app.clipboard().text())
        guide._next.click()
        self.assertEqual(guide._next.text(), 'Bắt đầu sử dụng')
        guide._next.click()
        self.assertFalse(guide.isVisible())
        self.controller._show_usage_guide()
        guide = self.controller._usage_guide
        QTest.keyClick(guide, Qt.Key_Right)
        self.assertEqual(guide._pages.currentIndex(), 1)
        QTest.keyClick(guide, Qt.Key_Escape)
        self.assertFalse(guide.isVisible())

    def test_skip_closes_and_small_screen_content_is_scrollable(self):
        self.controller._show_usage_guide()
        guide = self.controller._usage_guide
        guide.resize(600, 500)
        self.app.processEvents()
        self.assertLessEqual(guide.width(), 600)
        self.assertGreater(guide._scroll.verticalScrollBar().maximum(), 0)
        skip = guide.findChild(QPushButton, 'guideSkip')
        self.assertTrue(skip.isVisible())
        skip.click()
        self.assertFalse(guide.isVisible())

    def test_tray_icon_context_menu_and_keyboard_toggle_demo(self):
        self.controller._show_usage_guide()
        guide = self.controller._usage_guide
        guide._go(4)
        icon = guide.findChild(QPushButton, 'guideTrayIconDemo')
        self.assertIsNotNone(icon)
        menu = guide.findChild(QFrame, 'guideTrayMenuDemo')
        self.assertTrue(menu.isVisible())
        self.assertIn('Nhấp chuột phải', guide._description.text())
        self.assertIn('dấu ^', guide._note.text())
        point = icon.rect().center()
        self.app.sendEvent(icon, QContextMenuEvent(QContextMenuEvent.Mouse, point,
                                                  icon.mapToGlobal(point)))
        self.assertFalse(menu.isVisible())
        icon.setFocus()
        QTest.keyClick(icon, Qt.Key_Space)
        self.assertTrue(menu.isVisible())
        self.assertEqual(guide._pages.count(), 5)

    def test_tray_menu_samples_preserve_runtime_and_do_not_quit(self):
        self.controller._show_usage_guide()
        guide = self.controller._usage_guide
        guide._go(4)
        settings = self.store.load()
        language = guide.findChild(QPushButton, 'guideTrayLanguageDemo')
        self.assertIsNotNone(language)
        actions = language.menu().actions()
        actions[1].trigger()
        status = guide.findChild(QLabel, 'guideTrayStatusDemo')
        self.assertIn('English', status.text())
        self.assertEqual([action.isChecked() for action in actions], [False, True, False])
        actions[2].trigger()
        self.assertEqual([action.isChecked() for action in actions], [False, False, True])
        guide.findChild(QPushButton, 'guideTrayQuitDemo').click()
        self.assertIn('menu thật', status.text())
        self.assertTrue(guide.isVisible())
        self.assertEqual(self.store.load(), settings)


if __name__ == '__main__':
    unittest.main()
