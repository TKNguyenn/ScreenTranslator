import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.config import ProviderProfile
from microsoft_translator import UsageEvent
from microsoft_translator_usage import LocalUsageLedger


class MicrosoftOnlyTests(unittest.TestCase):
    def test_profile_has_only_translation_connection_fields(self):
        fields = ProviderProfile.__dataclass_fields__
        self.assertIn('region', fields)
        self.assertNotIn('azure_resource_id', fields)
        self.assertNotIn('azure_tenant_id', fields)

    def test_local_usage_ignores_old_remote_snapshot_without_deleting_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'usage.sqlite3'
            ledger = LocalUsageLedger(path)
            ledger.record(UsageEvent('one', 'en', ('vi',), 5, 'header'))
            ledger.record(UsageEvent('two', 'en', ('vi',), 3, 'estimate'))
            month = ledger.month_usage().month
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute('CREATE TABLE IF NOT EXISTS microsoft_azure_usage_snapshot ('
                             'resource_label TEXT, month TEXT, azure_resource_id TEXT, '
                             'used_characters INTEGER, cutoff_utc TEXT, fetched_at_utc TEXT, '
                             'PRIMARY KEY(resource_label, month, azure_resource_id))')
                conn.execute('INSERT INTO microsoft_azure_usage_snapshot VALUES (?, ?, ?, ?, ?, ?)',
                             ('default', month, 'legacy-resource', 900, '9999', '9999'))
            restored = LocalUsageLedger(path).month_usage()
            self.assertEqual((restored.calls, restored.local_total), (2, 8))
            self.assertEqual(restored.estimated_local_remaining, 1_999_992)
            self.assertFalse(hasattr(ledger, 'sync_azure_usage'))
            with closing(sqlite3.connect(path)) as conn:
                self.assertEqual(conn.execute('SELECT used_characters FROM microsoft_azure_usage_snapshot').fetchone()[0], 900)

    def test_new_ledger_creates_only_local_usage_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = LocalUsageLedger(Path(tmp) / 'usage.sqlite3')
            with closing(sqlite3.connect(ledger.path)) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {'microsoft_translation_usage'})


if __name__ == '__main__':
    unittest.main()
