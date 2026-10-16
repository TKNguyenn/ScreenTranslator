from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

import keyboard
import pyperclip

from app.config import ClipboardSection, HotkeySection
from app.services.window_service import WindowService


@dataclass(frozen=True)
class CapturedSelection:
    text: str
    foreground_hwnd: Optional[int]


class ClipboardSelectionService:
    """
    Windows-first selection capture using Ctrl+C and a clipboard sentinel.

    V0.2.1 still restores Unicode text only. UI Automation remains the preferred
    future path, with this kept as the compatibility fallback.
    """

    def __init__(self, clipboard_config: ClipboardSection, hotkey_config: HotkeySection) -> None:
        self._clipboard_config = clipboard_config
        self._hotkey_config = hotkey_config

    def capture_selection(self, preferred_hwnd: Optional[int] = None) -> CapturedSelection:
        if preferred_hwnd:
            WindowService.activate_window(preferred_hwnd, settle_s=0.08)

        hwnd = WindowService.get_foreground_window()
        previous = self._safe_paste()
        sentinel = f"__SCREEN_TRANSLATOR_SENTINEL_{uuid4().hex}__"

        time.sleep(self._hotkey_config.release_delay_ms / 1000.0)
        pyperclip.copy(sentinel)
        keyboard.send("ctrl+c")

        deadline = time.monotonic() + self._clipboard_config.copy_timeout_ms / 1000.0
        selected = sentinel
        while time.monotonic() < deadline:
            time.sleep(self._clipboard_config.copy_poll_ms / 1000.0)
            selected = self._safe_paste()
            if selected != sentinel:
                break

        self._restore_text(previous)

        if selected == sentinel or not selected.strip():
            raise RuntimeError(
                "Không lấy được text đang bôi đen. Hãy bôi đen text rồi dùng hotkey. "
                "Nếu app nguồn đang chạy Run as administrator thì Screen Translator cũng phải chạy cùng quyền."
            )

        return CapturedSelection(text=selected.strip(), foreground_hwnd=hwnd)

    def paste_text(self, text: str, target_hwnd: Optional[int], *,
                   cancel_event: threading.Event | None = None) -> None:
        if not text:
            raise ValueError("Cannot paste empty text.")

        previous = self._safe_paste()
        if target_hwnd:
            WindowService.activate_window(target_hwnd)

        pyperclip.copy(text)
        try:
            # Called by Quick UX for an explicit Replace; cancellation can
            # arrive while queued or while clipboard text is being staged.
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Quick UX Replace đã bị hủy trước khi dán.")
            keyboard.send("ctrl+v")
            time.sleep(self._clipboard_config.paste_restore_delay_ms / 1000.0)
        finally:
            self._restore_text(previous)

    @staticmethod
    def _safe_paste() -> str:
        try:
            value = pyperclip.paste()
            return value if isinstance(value, str) else ""
        except pyperclip.PyperclipException:
            return ""

    @staticmethod
    def _restore_text(previous: str) -> None:
        try:
            pyperclip.copy(previous)
        except pyperclip.PyperclipException:
            pass
