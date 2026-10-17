"""Local daily estimate; never an authoritative balance or usage limit."""
import hashlib
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.runtime_settings import RuntimeSettingsStore
from app.trial import TRIAL_DAILY_BUDGET_VND, TRIAL_ESTIMATED_COST_VND


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()


def _timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


class TrialUsageStore:
    # Translation and provider-test workers can use separate instances of this file.
    _lock = threading.Lock()

    def __init__(self, path: Path) -> None:
        self._store = RuntimeSettingsStore(path)
        with self._lock:
            self._touch_current_day()

    @staticmethod
    def _key_id(api_key: str) -> str:
        return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def _checks(state: dict) -> list[dict[str, str]]:
        raw = state.get("checks")
        checks = raw if isinstance(raw, list) else []
        valid = [
            {"date": str(item["date"]), "time": str(item.get("time", ""))}
            for item in checks
            if isinstance(item, dict) and isinstance(item.get("date"), str)
            and item["date"]
        ]
        # Migrate the previous single-date format into the two-check history.
        if not valid and isinstance(state.get("date"), str) and state["date"]:
            valid = [{"date": state["date"], "time": ""}]
        return valid[-2:]

    def _state(self, *, append_check: bool = False) -> tuple[str, dict[str, int]]:
        today = _today()
        state = self._store.load()
        checks = self._checks(state)
        last_date = checks[-1]["date"] if checks else ""
        day_changed = last_date != today
        spent = state.get("spent", {}) if not day_changed else {}
        if not isinstance(spent, dict):
            spent = {}
        spent = {k: v for k, v in spent.items() if isinstance(k, str) and type(v) is int and v >= 0}
        if day_changed or append_check:
            checks.append({"date": today, "time": _timestamp()})
            self._store.update(date=today, spent=spent, checks=checks[-2:])
        return today, spent

    def _touch_current_day(self) -> None:
        self._state(append_check=True)

    def remaining(self, api_key: str) -> int:
        if not api_key.strip():
            return TRIAL_DAILY_BUDGET_VND
        with self._lock:
            _, spent = self._state()
            return max(0, TRIAL_DAILY_BUDGET_VND - spent.get(self._key_id(api_key), 0))

    def record(self, api_key: str, model: str) -> None:
        if not api_key.strip():
            return
        cost = TRIAL_ESTIMATED_COST_VND[model]
        with self._lock:
            today, spent = self._state()
            key = self._key_id(api_key)
            spent[key] = min(TRIAL_DAILY_BUDGET_VND, spent.get(key, 0) + cost)
            state = self._store.load()
            self._store.update(date=today, spent=spent, checks=self._checks(state))
