from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from app.models import PasteResult, SelectionResult
from app.services.clipboard import ClipboardSelectionService
from app.services.window_service import WindowService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaptureSelectionTask:
    job_id: str
    preferred_hwnd: Optional[int] = None


@dataclass(frozen=True)
class PasteTextTask:
    job_id: str
    text: str
    foreground_hwnd: Optional[int]
    expected_selected_text: Optional[str] = None
    cancel_event: Optional[threading.Event] = None


@dataclass(frozen=True)
class InputServiceSwitchTask:
    service: ClipboardSelectionService


class InputWorker:
    def __init__(
        self,
        service: ClipboardSelectionService,
        on_selection: Callable[[SelectionResult], None],
        on_paste: Callable[[PasteResult], None],
    ) -> None:
        self._service = service
        self._on_selection = on_selection
        self._on_paste = on_paste
        self._queue: queue.Queue[CaptureSelectionTask | PasteTextTask | InputServiceSwitchTask | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="InputWorker", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def capture_selection(self, job_id: str, preferred_hwnd: Optional[int] = None) -> None:
        self._queue.put(CaptureSelectionTask(job_id=job_id, preferred_hwnd=preferred_hwnd))

    def paste_text(
        self, job_id: str, text: str, foreground_hwnd: Optional[int],
        *, expected_selected_text: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        self._queue.put(
            PasteTextTask(job_id=job_id, text=text, foreground_hwnd=foreground_hwnd,
                          expected_selected_text=expected_selected_text,
                          cancel_event=cancel_event)
        )

    def replace_service(self, service: ClipboardSelectionService) -> None:
        """Apply new clipboard/hotkey timing config after earlier queued input work."""
        self._queue.put(InputServiceSwitchTask(service=service))

    def _run(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                return

            if isinstance(task, CaptureSelectionTask):
                self._capture(task)
            elif isinstance(task, PasteTextTask):
                self._paste(task)
            elif isinstance(task, InputServiceSwitchTask):
                self._service = task.service
                logger.info("Input clipboard service reloaded")

    def _capture(self, task: CaptureSelectionTask) -> None:
        try:
            captured = self._service.capture_selection(task.preferred_hwnd)
            self._on_selection(
                SelectionResult(
                    job_id=task.job_id,
                    text=captured.text,
                    foreground_hwnd=captured.foreground_hwnd,
                )
            )
        except Exception as exc:
            logger.exception("Selection capture failed")
            self._on_selection(
                SelectionResult(job_id=task.job_id, text="", foreground_hwnd=None, error=str(exc))
            )

    def _paste(self, task: PasteTextTask) -> None:
        try:
            if task.cancel_event is not None and task.cancel_event.is_set():
                raise RuntimeError("Đã hủy thao tác Replace trước khi dán.")
            # For Quick UX, verify the *actual* clipboard-copyable selection as
            # close to paste time as possible. This is an explicit Replace action,
            # not passive auto-selection detection. Legacy paste is unchanged.
            if task.expected_selected_text is not None:
                # Passive Quick UX must never forcibly focus an old window.
                # If the user switched focus during a queued request, reject.
                if WindowService.get_foreground_window() != task.foreground_hwnd:
                    raise RuntimeError("Đã đổi cửa sổ trước khi thay thế; hủy Replace.")
                current = self._service.capture_selection(None)
                if current.foreground_hwnd != task.foreground_hwnd or current.text != task.expected_selected_text:
                    raise RuntimeError(
                        "Vùng chọn đã thay đổi trước khi dán; đã hủy Replace để tránh thay nhầm."
                    )
                if WindowService.get_foreground_window() != task.foreground_hwnd:
                    raise RuntimeError("Cửa sổ nguồn không còn active; hủy Replace.")
            if task.cancel_event is not None and task.cancel_event.is_set():
                raise RuntimeError("Người dùng đã hủy Replace hoặc click ra ngoài.")
            # Never SetForegroundWindow() for the safety-checked Quick UX path.
            # Legacy hotkey replacement retains previous behavior.
            destination = None if task.expected_selected_text is not None else task.foreground_hwnd
            self._service.paste_text(task.text, destination, cancel_event=task.cancel_event)
            self._on_paste(PasteResult(job_id=task.job_id, success=True))
        except Exception as exc:
            logger.exception("Paste failed")
            self._on_paste(PasteResult(job_id=task.job_id, success=False, error=str(exc)))
