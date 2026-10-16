from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.config import portable_provider_entry


class ProviderCatalogStore:
    """Atomic store for the portable provider catalog.

    File schema is intentionally minimal and portable across app versions:

    {
      "Provider name": {
        "base_url": "https://.../v1",
        "api_key": "...",
        "models": ["model-a", "model-b"]
      }
    }
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return self._read_unlocked()

    def replace_all(self, providers: dict[str, Any]) -> None:
        if not providers:
            raise ValueError("Provider catalog must contain at least one provider.")
        normalized: dict[str, dict[str, Any]] = {}
        for raw_name, raw_profile in providers.items():
            name = str(raw_name).strip()
            if not name:
                raise ValueError("Provider name cannot be empty.")
            if not isinstance(raw_profile, dict):
                raise ValueError(f"Provider '{name}' must be an object.")
            entry = portable_provider_entry(raw_profile)
            if not entry["models"]:
                raise ValueError(f"Provider '{name}' must have at least one model.")
            if not entry["base_url"] and name.lower() != "mock":
                raise ValueError(f"Provider '{name}' is missing base_url.")
            normalized[name] = entry

        with self._lock:
            self._write_unlocked(normalized)

    def _read_unlocked(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("providers.json root must be a JSON object.")
        result: dict[str, dict[str, Any]] = {}
        for raw_name, raw_profile in loaded.items():
            if not isinstance(raw_profile, dict):
                continue
            result[str(raw_name)] = portable_provider_entry(raw_profile)
        return result

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(self._path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        temp.replace(self._path)
