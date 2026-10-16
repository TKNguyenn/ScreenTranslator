"""Regression for pynput 1.8+ mouse callback and silent listener thread death."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.quickux.mouse_monitor import MouseSelectionMonitor
from app.services.window_service import WindowService


class MouseCallbackCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.candidates = []
        self.external_clicks = []
        self.errors = []
        self.monitor = MouseSelectionMonitor(
            on_selection_candidate=self.candidates.append,
            on_external_press=lambda: self.external_clicks.append(1),
            on_error=self.errors.append,
        )
        self.button = SimpleNamespace(name="left")
        self.foreground = patch.object(WindowService, "get_foreground_window", return_value=42)
        self.hit = patch.object(WindowService, "get_window_from_point", return_value=42)
        self.own = patch.object(WindowService, "is_own_process_window", return_value=False)
        self.shell = patch.object(WindowService, "is_shell_surface", return_value=False)
        for each in [self.foreground, self.hit, self.own, self.shell]:
            each.start()
            self.addCleanup(each.stop)

    def test_old_four_argument_callback_still_works(self):
        self.monitor._on_click(12, 20, self.button, True)
        self.monitor._on_click(46, 20, self.button, False)
        self.assertEqual(len(self.candidates), 1)
        self.assertEqual(self.candidates[0].hwnd, 42)
        self.assertEqual(len(self.external_clicks), 1)
        self.assertEqual(self.errors, [])

    def test_new_five_argument_callback_works(self):
        self.monitor._on_click(12, 20, self.button, True, False)
        self.monitor._on_click(46, 20, self.button, False, False)
        self.assertEqual(len(self.candidates), 1)
        self.assertEqual((self.candidates[0].x, self.candidates[0].y), (46, 20))
        self.assertEqual(self.errors, [])

    def test_injected_clicks_do_not_trigger(self):
        self.monitor._on_click(12, 20, self.button, True, True)
        self.monitor._on_click(46, 20, self.button, False, True)
        self.assertEqual(self.candidates, [])
        self.assertEqual(self.external_clicks, [])

    def test_callback_errors_are_caught_to_keep_listener_alive(self):
        with patch.object(self.monitor, "_process_click", side_effect=RuntimeError("synthetic-failure")):
            self.monitor._on_click(5, 5, self.button, True, False)
        self.assertEqual(len(self.errors), 1)
        self.assertIn("synthetic-failure", self.errors[0])

    def test_hook_health_detection(self):
        self.assertFalse(self.monitor.is_running())
        self.monitor._listener = SimpleNamespace(is_alive=lambda: True)
        self.assertTrue(self.monitor.is_running())
        self.monitor._listener = SimpleNamespace(is_alive=lambda: False)
        self.assertFalse(self.monitor.is_running())

    def test_controller_diagnostics_distinguish_hook_and_uia(self):
        source = (Path(__file__).resolve().parents[1] / "app/controller.py").read_text(encoding="utf-8")
        self.assertIn("Quick UX mouse hook running:", source)
        self.assertIn("Quick UX last probe:", source)
        self.assertIn("Quick UX UI Automation did not expose selected text", source)


if __name__ == "__main__":
    unittest.main()
