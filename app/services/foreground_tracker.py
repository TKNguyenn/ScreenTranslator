from __future__ import annotations

import logging
import threading
from typing import Optional

from app.services.window_service import WindowService


logger = logging.getLogger(__name__)


class ForegroundWindowTracker:
    """Tracks the most recent non-translator, non-taskbar foreground window."""

    def __init__(self, poll_interval_s: float = 0.10) -> None:
        self._poll_interval_s = poll_interval_s
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="ForegroundTracker",
            daemon=True,
        )
        self._lock = threading.Lock()
        self._last_external_hwnd: Optional[int] = None

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def last_external_window(self) -> Optional[int]:
        with self._lock:
            return self._last_external_hwnd

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval_s):
            hwnd = WindowService.get_foreground_window()
            if not hwnd:
                continue
            if WindowService.is_own_process_window(hwnd):
                continue
            if WindowService.is_shell_surface(hwnd):
                continue
            with self._lock:
                self._last_external_hwnd = hwnd
