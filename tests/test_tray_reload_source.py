from __future__ import annotations

import unittest
from pathlib import Path


class TrayReloadSourceTests(unittest.TestCase):
    def test_reload_action_is_persistent_and_visible_near_top(self) -> None:
        tray_path = Path(__file__).resolve().parents[1] / "app" / "ui" / "tray.py"
        source = tray_path.read_text(encoding="utf-8")
        self.assertIn("self._reload_action = QAction", source)
        self.assertIn('"Reload config.json"', source)
        self.assertIn("self._menu.addAction(self._reload_action)", source)
        self.assertIn("APP_VERSION", source)


if __name__ == "__main__":
    unittest.main()
