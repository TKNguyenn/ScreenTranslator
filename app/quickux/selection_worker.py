from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass

from app.quickux.selection import QuickSelectionProbe, QuickSelectionCheck, SelectionSnapshot
from app.quickux.uia_reader import WindowsUiaSelectionReader

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbeTask:
    serial: int
    hwnd: int
    x: int
    y: int


@dataclass(frozen=True)
class VerifyTask:
    job_id: str
    snapshot: SelectionSnapshot


class QuickSelectionWorker:
    def __init__(
        self,
        on_probe: Callable[[QuickSelectionProbe], None],
        on_check: Callable[[QuickSelectionCheck], None],
        reader: WindowsUiaSelectionReader | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._on_probe = on_probe
        self._on_check = on_check
        self._on_error = on_error
        self._reader = reader or WindowsUiaSelectionReader()
        self._queue: queue.Queue[ProbeTask | VerifyTask | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="UIASelectionWorker", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def probe(self, serial: int, hwnd: int, x: int, y: int) -> None:
        # Serial is checked again in GUI; stale UIA results never show the bar.
        self._queue.put(ProbeTask(serial, hwnd, x, y))

    def verify(self, job_id: str, snapshot: SelectionSnapshot) -> None:
        self._queue.put(VerifyTask(job_id, snapshot))

    def update_max_characters(self, max_characters: int) -> None:
        # Safe for the next read (Python atomic integer assignment).
        self._reader.max_characters = max_characters

    def _run(self) -> None:
        try:
            import os
            if os.name == "nt":
                import uiautomation as auto
                with auto.UIAutomationInitializerInThread():
                    self._work_loop()
            else:
                self._work_loop()
        except Exception as exc:
            logger.exception("UI Automation worker unavailable")
            if self._on_error is not None:
                self._on_error(f"Windows UI Automation không hoạt động: {exc}")
            # No automatic clipboard fallback: passive probing must be safe.

    def _work_loop(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                return
            if isinstance(task, ProbeTask):
                try:
                    snapshot = self._reader.probe(task.hwnd, (task.x, task.y))
                except Exception as exc:
                    logger.warning("UIA selection probe failed: %s", type(exc).__name__)
                    snapshot = None
                    self._reader.last_status = f"UIA: probe failed ({type(exc).__name__})"
                self._on_probe(QuickSelectionProbe(task.serial, snapshot,
                                                 getattr(self._reader, "last_status", "")))
            elif isinstance(task, VerifyTask):
                try:
                    valid = self._reader.verify(task.snapshot)
                except Exception:
                    logger.debug("UIA replacement verification failed", exc_info=True)
                    valid = False
                self._on_check(QuickSelectionCheck(
                    task.job_id, valid,
                    "Vùng bôi đen đã thay đổi hoặc app nguồn không hỗ trợ xác minh qua UI Automation. "
                    "Hãy chọn lại chữ rồi thử lại; không dán để tránh thay nhầm nội dung." if not valid else "",
                ))
