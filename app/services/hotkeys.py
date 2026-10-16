from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import keyboard

from app.config import HotkeySection
from app.models import HotkeyAction


logger = logging.getLogger(__name__)


class HotkeyService:
    def __init__(
        self,
        config: HotkeySection,
        on_action: Callable[[HotkeyAction], None],
        on_ready: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_escape: Callable[[], None] | None = None,
    ) -> None:
        self._config = config
        self._on_action = on_action
        self._on_ready = on_ready
        self._on_error = on_error
        self._on_escape = on_escape
        self._escape_handle = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._handles: list[object] = []

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="HotkeyThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for handle in self._handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                logger.exception("Failed to remove hotkey handle")
        self._handles.clear()
        if self._escape_handle is not None:
            try:
                keyboard.unhook(self._escape_handle)
            except Exception:
                logger.exception("Failed to unregister Quick UX Escape hook")
            self._escape_handle = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _run(self) -> None:
        bindings = {
            self._config.translate_selection: HotkeyAction.TRANSLATE_SELECTION,
            self._config.translate_and_replace: HotkeyAction.TRANSLATE_AND_REPLACE,
            self._config.live_toggle: HotkeyAction.LIVE_TOGGLE,
            self._config.region_translate: HotkeyAction.REGION_TRANSLATE,
            self._config.target_vi: HotkeyAction.TARGET_VI,
            self._config.target_en: HotkeyAction.TARGET_EN,
            self._config.target_zh_hant: HotkeyAction.TARGET_ZH_HANT,
        }

        try:
            for hotkey, action in bindings.items():
                handle = keyboard.add_hotkey(
                    hotkey,
                    lambda selected_action=action: self._on_action(selected_action),
                    # Important on Windows: if Alt+T is allowed to reach the source
                    # application it can open a menu and destroy the current selection.
                    suppress=self._config.suppress_hotkeys,
                    trigger_on_release=True,
                )
                self._handles.append(handle)
                logger.info(
                    "Registered hotkey %s -> %s (suppress=%s)",
                    hotkey,
                    action.value,
                    self._config.suppress_hotkeys,
                )
        except Exception as exc:
            message = f"Global hotkey registration failed: {exc}"
            logger.exception(message)
            if self._on_error:
                self._on_error(message)
            return

        if self._on_escape is not None:
            try:
                # Observe Escape, never suppress it in the source app.
                self._escape_handle = keyboard.on_press_key(
                    "esc", lambda event: self._on_escape(), suppress=False
                )
            except Exception:
                logger.warning("Quick UX Escape hook unavailable", exc_info=True)

        if self._on_ready:
            self._on_ready()

        while not self._stop_event.wait(0.25):
            pass
