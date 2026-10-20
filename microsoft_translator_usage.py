"""Local monthly usage ledger for Microsoft Translator in ScreenTranslator.

Tracks returned X-Metered-Usage (or flagged estimates) from THIS app only.
NOT the official Azure resource balance: other machines/keys/apps aren't seen.
Does not store translated text or API keys. Standard library only.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from microsoft_translator import UsageEvent

# Vietnam has no daylight saving time. UI month accounting uses UTC+7.
_VIETNAM = timezone(timedelta(hours=7))


def default_database_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "ScreenTranslator" / "microsoft_usage.sqlite3"
    return Path.home() / ".screentranslator" / "microsoft_usage.sqlite3"


@dataclass(frozen=True)
class MonthUsage:
    month: str
    calls: int
    verified_characters: int
    estimated_characters: int
    free_tier_reference: int = 2_000_000

    @property
    def local_total(self) -> int:
        return self.verified_characters + self.estimated_characters

    @property
    def estimated_local_remaining(self) -> int:
        # This is NOT the real remaining free tier quota at Azure.
        return max(self.free_tier_reference - self.local_total, 0)


class LocalUsageLedger:
    """SQLite ledger, uniquely keyed by request id to avoid double recording."""

    def __init__(self, path: Optional[os.PathLike] = None,
                 *, resource_label: str = "default") -> None:
        self.path = Path(path) if path is not None else default_database_path()
        if not resource_label.strip():
            raise ValueError("resource_label không được rỗng.")
        self.resource_label = resource_label
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS microsoft_translation_usage (
                    request_id TEXT PRIMARY KEY,
                    resource_label TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    metered_characters INTEGER NOT NULL CHECK(metered_characters >= 0),
                    usage_source TEXT NOT NULL CHECK(usage_source IN ('header','estimate')),
                    source_language TEXT NOT NULL,
                    target_languages TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_microsoft_translation_time
                ON microsoft_translation_usage (resource_label, timestamp_utc)
            """)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        try:
            with connection:
                connection.execute("PRAGMA busy_timeout = 10000")
                yield connection
        finally:
            connection.close()

    def record(self, event: UsageEvent) -> None:
        """Safe to pass as MicrosoftTranslator(on_usage=ledger.record)."""
        if not isinstance(event.metered_characters, int) or event.metered_characters < 0:
            raise ValueError("Số ký tự không hợp lệ.")
        if event.usage_source not in ("header", "estimate"):
            raise ValueError("Nguồn thống kê không hợp lệ.")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO microsoft_translation_usage (
                    request_id, resource_label, timestamp_utc, metered_characters,
                    usage_source, source_language, target_languages
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.request_id, self.resource_label, timestamp,
                event.metered_characters, event.usage_source,
                event.source_language, ",".join(event.target_languages),
            ))


    def month_usage(self, month: Optional[str] = None) -> MonthUsage:
        """Return this computer's recorded usage for the Vietnam-local month."""
        if month is None:
            month = datetime.now(_VIETNAM).strftime("%Y-%m")
        try:
            start = datetime.strptime(month, "%Y-%m").replace(tzinfo=_VIETNAM)
        except ValueError as exc:
            raise ValueError("month phải có dạng YYYY-MM.") from exc
        if start.strftime("%Y-%m") != month:
            raise ValueError("month phải có dạng YYYY-MM.")
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        start_iso = start.astimezone(timezone.utc).isoformat(timespec="microseconds")
        end_iso = next_month.astimezone(timezone.utc).isoformat(timespec="microseconds")
        with self._connect() as conn:
            row = conn.execute("""
                SELECT COUNT(*),
                       COALESCE(SUM(CASE WHEN usage_source='header' THEN metered_characters ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN usage_source='estimate' THEN metered_characters ELSE 0 END), 0)
                FROM microsoft_translation_usage
                WHERE resource_label=? AND timestamp_utc>=? AND timestamp_utc<?
            """, (self.resource_label, start_iso, end_iso)).fetchone()
        return MonthUsage(month, int(row[0]), int(row[1]), int(row[2]))
