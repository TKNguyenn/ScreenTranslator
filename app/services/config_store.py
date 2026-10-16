from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class ConfigFileStore:
    """Atomic JSON config updates used by tray controls and the desktop manager."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def update_nested(self, keys: tuple[str, ...], value: Any) -> None:
        if not keys:
            raise ValueError("At least one config key is required.")

        with self._lock:
            data = self._read_unlocked()
            cursor: dict[str, Any] = data
            for key in keys[:-1]:
                child = cursor.get(key)
                if not isinstance(child, dict):
                    child = {}
                    cursor[key] = child
                cursor = child
            cursor[keys[-1]] = value
            self._write_unlocked(data)

    def replace_section(self, section_name: str, value: Any) -> None:
        if not section_name:
            raise ValueError("section_name cannot be empty")
        with self._lock:
            data = self._read_unlocked()
            data[section_name] = value
            self._write_unlocked(data)

    def read(self) -> dict[str, Any]:
        with self._lock:
            return self._read_unlocked()

    def _read_unlocked(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("config.json root must be a JSON object.")
        return loaded

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(self._path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        temp.replace(self._path)
