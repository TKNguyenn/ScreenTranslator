from __future__ import annotations

import os
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtGui import QFontDatabase
from app.config import AppConfig
from app.controller import AppController
from app.services.updates import Release
from app.services.trial_usage import TrialUsageStore
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        if os.name == "nt" and cls.app.platformName() == "offscreen":
            for name in ("segoeui.ttf", "seguisb.ttf"):
                QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))
        apply_theme(cls.app)

    def setUp(self):
        self.window = MainWindow(self.app, AppConfig())
        self.addCleanup(self.window.allow_close)
        self.addCleanup(self.window.deleteLater)

    def test_footer_replaces_old_text_and_emits_update_action(self):
        button = self.window.findChild(QPushButton, "checkUpdatesButton")
        self.assertIsNotNone(button)
        self.assertEqual(button.text(), "Check for updates")
        self.assertFalse(any("AURORA BENTO" in label.text() for label in self.window.findChildren(QLabel)))
        actions = []
        self.window.check_updates_requested.connect(lambda: actions.append(True))
        button.click()
        self.assertEqual(actions, [True])
        self.window.set_update_state("Downloading 42%", "Đang tải…", busy=True, progress=42)
        self.assertFalse(button.isEnabled())
        self.assertEqual(self.window._update_progress.value(), 42)
        self.window.set_update_state("Latest version: v0.4.1.9")
        self.assertTrue(button.isEnabled())
        self.assertTrue(self.window._update_progress.isHidden())

    def test_checked_current_older_and_newer_releases_never_offer_downgrade(self):
        controller = SimpleNamespace(_main_window=self.window, _available_update=None)
        with patch("app.controller.APP_VERSION", "0.4.1.9"):
            for version, available in (("0.4.1.8", False), ("0.4.1.9", False), ("0.4.1.10", True)):
                with self.subTest(version=version):
                    release = Release(version, "", 10, "0" * 64)
                    AppController._on_update_checked(controller, release)
                    self.assertEqual(controller._available_update is not None, available)
                    self.assertIn(version, self.window._update_status.text())
                    self.assertEqual(self.window._check_updates_button.text().startswith("Update to"), available)

    def test_startup_checks_once_per_day_using_trial_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trial_usage.json"
            controller = SimpleNamespace(
                _config=SimpleNamespace(data_dir=Path(tmp)), _check_for_updates=Mock())
            with patch("app.services.trial_usage._today", return_value="2026-10-17"):
                usage = TrialUsageStore(path)
                usage.record("synthetic-key", "gpt-6-sol")
                AppController._check_updates_on_startup(controller)
                controller._check_for_updates.assert_called_once()
                for _ in range(3):
                    TrialUsageStore(path)
                    AppController._check_updates_on_startup(controller)
                self.assertEqual(controller._check_for_updates.call_count, 1)
                self.assertEqual(usage.remaining("synthetic-key"), 96)
            for day in ("2026-10-18", "2026-10-23"):
                with patch("app.services.trial_usage._today", return_value=day):
                    AppController._check_updates_on_startup(controller)
                    self.assertEqual(TrialUsageStore(path).remaining("synthetic-key"), 100)
                    state = json.loads(path.read_text())
                    self.assertEqual(state["last_update_check_date"], day)
                    self.assertLessEqual(len(state["checks"]), 2)
            self.assertEqual(controller._check_for_updates.call_count, 3)

    def test_manual_check_bypasses_daily_gate_and_startup_never_downloads(self):
        controller = SimpleNamespace(
            _main_window=self.window, _updates=Mock(), _available_update=None)
        controller._check_for_updates = lambda: AppController._check_for_updates(controller)
        AppController._on_update_clicked(controller)
        AppController._on_update_clicked(controller)
        self.assertEqual(controller._updates.check.call_count, 2)
        with tempfile.TemporaryDirectory() as tmp:
            controller._config = SimpleNamespace(data_dir=Path(tmp))
            controller._available_update = Release("99.0.0", "", 10, "0" * 64)
            AppController._check_updates_on_startup(controller)
            self.assertEqual(controller._updates.check.call_count, 3)
            controller._updates.download.assert_not_called()

    def test_daily_marker_disk_failure_does_not_prevent_startup(self):
        controller = SimpleNamespace(
            _config=SimpleNamespace(data_dir=Path("fixture")), _check_for_updates=Mock())
        with patch("app.controller.TrialUsageStore", side_effect=OSError("disk unavailable")), \
                self.assertLogs("app.controller", level="WARNING"):
            AppController._check_updates_on_startup(controller)
        controller._check_for_updates.assert_not_called()

    def test_start_schedules_daily_check_after_showing_window(self):
        controller = SimpleNamespace(
            _config=AppConfig(), _main_window=self.window, _profile=SimpleNamespace(model="test"),
            _profile_name="Custom", _target_language="vi", _startup_provider_error=None,
            _check_updates_on_startup=Mock(), _tray=Mock(), _refresh_tray_state=Mock(),
            **{name: Mock() for name in ("_foreground_tracker", "_quick_selection_worker",
               "_mouse_selection_monitor", "_input_worker", "_ocr_worker", "_translation_worker", "_hotkeys")})
        AppController.start(controller)
        self.addCleanup(self.window.hide)
        self.assertTrue(self.window.isVisible())
        controller._check_updates_on_startup.assert_not_called()
        self.app.processEvents()
        controller._check_updates_on_startup.assert_called_once()

    def test_update_marker_and_trial_workers_share_atomic_writes(self):
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trial_usage.json"
            def run(_):
                store = TrialUsageStore(path)
                due = store.claim_update_check()
                store.record("synthetic-key", "gpt-6-luna")
                return due
            with ThreadPoolExecutor(max_workers=4) as pool:
                due = list(pool.map(run, range(20)))
            self.assertEqual(sum(due), 1)
            self.assertEqual(TrialUsageStore(path).remaining("synthetic-key"), 80)

    def test_update_controls_fit_compact_sidebar(self):
        self.window.resize(900, 620)
        self.window.set_update_state("Latest version: v0.4.1.10", "Update to v0.4.1.10")
        self.window.show()
        self.app.processEvents()
        button = self.window._check_updates_button
        self.assertGreaterEqual(button.contentsRect().width(), button.fontMetrics().horizontalAdvance(button.text()))
        self.assertLessEqual(self.window._update_status.geometry().bottom(), button.parentWidget().height())
        self.window.hide()

    def test_install_failure_keeps_app_running_and_success_hands_off_before_quit(self):
        controller = SimpleNamespace(_main_window=self.window, _available_update=Release("0.4.1.10", "", 10, "0" * 64),
                                     _updates=Mock(), _app=Mock(), _on_update_failed=Mock())
        with patch("app.controller.launch_installer", side_effect=OSError("fixture failure")):
            AppController._on_update_downloaded(controller, "fixture.exe")
        controller._app.quit.assert_not_called()
        controller._updates.keep_download_for_installer.assert_not_called()
        controller._on_update_failed.assert_called_once()
        with patch("app.controller.launch_installer"):
            AppController._on_update_downloaded(controller, "fixture.exe")
        controller._updates.keep_download_for_installer.assert_called_once()
        controller._app.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
