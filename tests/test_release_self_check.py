from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ReleaseSelfCheckTests(unittest.TestCase):
    def test_failed_check_writes_report_and_returns_failure(self):
        from app.self_check import run_self_check
        import json
        with tempfile.TemporaryDirectory() as tmp, patch("app.self_check.AppConfig.load", side_effect=RuntimeError("test failure")):
            report = Path(tmp) / "self-check.json"
            self.assertEqual(run_self_check(report), 1)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertFalse(result["ok"])
            self.assertIn("test failure", result["error"])


if __name__ == "__main__":
    unittest.main()
