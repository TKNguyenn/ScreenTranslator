from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.runtime_settings import RuntimeSettingsStore


class RuntimeSettingsStoreTests(unittest.TestCase):
    def test_round_trip_and_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime_settings.json"
            store = RuntimeSettingsStore(path)
            self.assertEqual(store.load(), {})

            store.update(target_language="vi")
            store.update(provider_profile="mock")

            self.assertEqual(
                store.load(),
                {"target_language": "vi", "provider_profile": "mock"},
            )


if __name__ == "__main__":
    unittest.main()
