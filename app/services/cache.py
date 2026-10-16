from __future__ import annotations

import hashlib
import sqlite3
import threading
from collections import OrderedDict
from contextlib import closing
from pathlib import Path
from typing import Optional


class TranslationCache:
    def __init__(self, db_path: Path, enabled: bool = True, memory_capacity: int = 256) -> None:
        self._db_path = db_path
        self._enabled = bool(enabled)
        self._lock = threading.Lock()
        self._memory_capacity = max(0, int(memory_capacity))
        self._memory: OrderedDict[str, str] = OrderedDict()
        if self._enabled:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable both cache reads and writes at runtime.

        Disabling does not delete the existing SQLite database. This is useful
        for benchmarks: every request reaches the provider while cache is off.
        Re-enabling makes old persisted entries available again.
        """
        enabled = bool(enabled)
        with self._lock:
            if self._enabled == enabled:
                return
            self._enabled = enabled
            self._memory.clear()
            if enabled:
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
                self._initialize_unlocked()

    @staticmethod
    def make_key(
        source_text: str,
        source_language: str,
        target_language: str,
        context_preset: str,
        provider_id: str,
        model_id: str,
        prompt_version: str,
    ) -> str:
        normalized = source_text.replace("\r\n", "\n").strip()
        material = "\x1f".join(
            [
                normalized,
                source_language,
                target_language,
                context_preset,
                provider_id,
                model_id,
                prompt_version,
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if not self._enabled:
                return None
            if key in self._memory:
                value = self._memory.pop(key)
                self._memory[key] = value
                return value

            with closing(sqlite3.connect(self._db_path)) as conn:
                row = conn.execute(
                    "SELECT translated_text FROM translations WHERE cache_key = ?",
                    (key,),
                ).fetchone()

            if not row:
                return None

            value = row[0]
            self._remember(key, value)
            return value

    def put(
        self,
        key: str,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        context_preset: str,
        provider_id: str,
        model_id: str,
        prompt_version: str,
    ) -> None:
        with self._lock:
            if not self._enabled:
                return
            self._remember(key, translated_text)
            with closing(sqlite3.connect(self._db_path)) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO translations (
                        cache_key, source_text, translated_text, source_language,
                        target_language, context_preset, provider_id, model_id,
                        prompt_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        key,
                        source_text,
                        translated_text,
                        source_language,
                        target_language,
                        context_preset,
                        provider_id,
                        model_id,
                        prompt_version,
                    ),
                )
                conn.commit()

    def count(self) -> int:
        with self._lock:
            if not self._enabled:
                return 0
            with closing(sqlite3.connect(self._db_path)) as conn:
                return int(conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0])

    def _remember(self, key: str, value: str) -> None:
        if self._memory_capacity <= 0:
            return
        self._memory.pop(key, None)
        self._memory[key] = value
        while len(self._memory) > self._memory_capacity:
            self._memory.popitem(last=False)

    def _initialize(self) -> None:
        with self._lock:
            self._initialize_unlocked()

    def _initialize_unlocked(self) -> None:
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    cache_key TEXT PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    context_preset TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
