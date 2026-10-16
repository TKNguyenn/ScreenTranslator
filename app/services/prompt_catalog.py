from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.prompts import (
    CONTEXT_PRESETS,
    PERFORMANCE_MODES,
    normalize_prompt_overrides,
    validate_prompt_template,
)


class PromptCatalogStore:
    """Atomic portable storage for user prompt overrides.

    The file stores only user customizations. Defaults remain in source code, so a
    reset simply removes an override and automatically tracks improved defaults in
    future app versions.
    """

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def read_overrides(self) -> dict[str, dict[str, str]]:
        with self._lock:
            return self._read_unlocked()

    def replace_all(self, overrides: dict[str, Any]) -> None:
        normalized = normalize_prompt_overrides(overrides)
        with self._lock:
            self._write_unlocked(normalized)

    def set_override(self, performance_mode: str, context_preset: str, template: str) -> None:
        mode = self._validate_mode(performance_mode)
        style = self._validate_style(context_preset)
        validate_prompt_template(template)
        template = template.strip()
        with self._lock:
            overrides = self._read_unlocked()
            overrides.setdefault(mode, {})[style] = template
            self._write_unlocked(overrides)

    def reset_override(self, performance_mode: str, context_preset: str) -> None:
        mode = self._validate_mode(performance_mode)
        style = self._validate_style(context_preset)
        with self._lock:
            overrides = self._read_unlocked()
            styles = overrides.get(mode)
            if isinstance(styles, dict):
                styles.pop(style, None)
                if not styles:
                    overrides.pop(mode, None)
            self._write_unlocked(overrides)

    def reset_all(self) -> None:
        with self._lock:
            self._write_unlocked({})

    def _read_unlocked(self) -> dict[str, dict[str, str]]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("prompts.json root must be a JSON object.")

        # V0.3.2 canonical format is {schema_version, overrides}. Accept a plain
        # overrides object as a forgiving import format.
        raw_overrides = loaded.get("overrides", loaded)
        if not isinstance(raw_overrides, dict):
            raise ValueError("prompts.json 'overrides' must be a JSON object.")
        return normalize_prompt_overrides(raw_overrides)

    def _write_unlocked(self, overrides: dict[str, dict[str, str]]) -> None:
        normalized = normalize_prompt_overrides(overrides)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "overrides": normalized,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(self._path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        temp.replace(self._path)

    @staticmethod
    def _validate_mode(value: str) -> str:
        mode = str(value).strip().lower()
        if mode not in PERFORMANCE_MODES:
            raise ValueError(f"Unsupported performance mode: {value}")
        return mode

    @staticmethod
    def _validate_style(value: str) -> str:
        style = str(value).strip().lower()
        if style not in CONTEXT_PRESETS:
            raise ValueError(f"Unsupported translation style: {value}")
        return style
