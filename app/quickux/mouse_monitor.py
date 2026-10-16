from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable

from app.quickux.selection import MouseGestureRecognizer, MouseSelectionCandidate
from app.services.window_service import WindowService

logger = logging.getLogger(__name__)


class MouseSelectionMonitor:
    """Detect mouse-selection gestures without reading the clipboard.

    pynput <=1.7 calls on_click(x, y, button, pressed). Newer versions call
    on_click(x, y, button, pressed, injected). Accept BOTH. Uncaught exceptions
    in a pynput listener callback stop the hook thread, so callback failures
    must be handled here and never leak into the input-hook thread.
    """

    def __init__(
        self,
        on_selection_candidate: Callable[[MouseSelectionCandidate], None],
        on_external_press: Callable[[], None],
        on_error: Callable[[str], None],
        enabled: bool = True,
    ) -> None:
        self._on_candidate = on_selection_candidate
        self._on_external_press = on_external_press
        self._on_error = on_error
        self._enabled = enabled
        self._lock = threading.Lock()
        self._listener = None
        self._gesture = MouseGestureRecognizer()
        self._last_error_at = 0.0

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = bool(enabled)

    def is_running(self) -> bool:
        listener = self._listener
        return bool(listener is not None and listener.is_alive())

    def start(self) -> None:
        if os.name != "nt":
            return
        if self.is_running():
            return
        self._listener = None
        try:
            from pynput import mouse

            listener = mouse.Listener(on_click=self._on_click)
            listener.start()
            self._listener = listener
            logger.info("Quick UX global mouse hook started (pynput 4/5-argument compatible)")
        except Exception as exc:
            logger.exception("Quick UX mouse hook unavailable")
            self._on_error(f"Quick Toolbar khong the theo doi chuot: {exc}")

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.stop()
                listener.join(timeout=1.0)
            except Exception:
                logger.exception("Quick UX mouse hook shutdown failed")

    def _on_click(
        self,
        x: float,
        y: float,
        button: object,
        pressed: bool,
        injected: bool = False,
    ) -> None:
        """Both pynput callback signatures are supported; ignore synthetic input."""
        try:
            if injected:
                return
            self._process_click(x, y, button, pressed)
        except Exception as exc:
            # A raised exception kills pynput.Listener, sometimes silently.
            # Throttle user notifications to avoid a mouse hook notification loop.
            logger.exception("Quick UX mouse callback failed")
            now = time.monotonic()
            if now - self._last_error_at > 10.0:
                self._last_error_at = now
                try:
                    self._on_error(f"Quick Toolbar mouse callback failed: {exc}")
                except Exception:
                    logger.exception("Quick UX error callback failed")

    def _process_click(self, x: float, y: float, button: object, pressed: bool) -> None:
        if getattr(button, "name", "") != "left" and str(button) != "Button.left":
            return
        with self._lock:
            if not self._enabled:
                return
        x, y = int(x), int(y)
        hit_hwnd = WindowService.get_window_from_point(x, y)
        if WindowService.is_own_process_window(hit_hwnd):
            return
        hwnd = WindowService.get_foreground_window()
        if not hwnd or WindowService.is_own_process_window(hwnd) or WindowService.is_shell_surface(hwnd):
            return
        now = time.monotonic()
        if pressed:
            self._gesture.press(x, y, now, hwnd)
            self._on_external_press()
            return
        if not self._gesture.release(x, y, now, hwnd):
            return
        logger.info("Quick UX mouse selection gesture recognized; probing UIA selection")
        self._on_candidate(MouseSelectionCandidate(hwnd, x, y))
