from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class RuntimeSettingsStore:
    """Small local store for tray choices that should survive an app restart."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self._path.exists():
                return {}
            try:
                with self._path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return data if isinstance(data, dict) else {}
            except Exception:
                logger.exception("Failed to load runtime settings from %s", self._path)
                return {}

    def update(self, **values: Any) -> None:
        with self._lock:
            data: dict[str, Any] = {}
            if self._path.exists():
                try:
                    with self._path.open("r", encoding="utf-8") as handle:
                        existing = json.load(handle)
                    if isinstance(existing, dict):
                        data.update(existing)
                except Exception:
                    logger.exception("Failed to read runtime settings before update")

            data.update(values)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temp = self._path.with_suffix(self._path.suffix + ".tmp")
            with temp.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
            temp.replace(self._path)
