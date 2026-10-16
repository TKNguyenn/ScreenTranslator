from __future__ import annotations

import logging
import os
from collections import deque
from collections.abc import Callable
from typing import Any

from app.quickux.selection import SelectionSnapshot
from app.services.window_service import WindowService

logger = logging.getLogger(__name__)


def _get(obj: object, name: str, fallback: Any = "") -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return fallback


def _secure_control(control: object) -> bool:
    """Never read a UIA element explicitly reported as a password control."""
    if bool(_get(control, "IsPassword", False)):
        return True
    # Some custom accessibility implementations forget IsPassword.
    marker = " ".join(str(_get(control, key)).lower() for key in ("AutomationId", "ClassName"))
    return "password" in marker or "passwd" in marker


def _identity(control: object) -> tuple[str, ...]:
    """Best-effort identity; combined with HWND and exact selected text on verify."""
    fields = ["ProcessId", "ControlTypeName", "AutomationId", "ClassName", "NativeWindowHandle"]
    values = [str(_get(control, key)) for key in fields]
    rect = _get(control, "BoundingRectangle", None)
    if rect is not None:
        for key in ("left", "top", "right", "bottom"):
            values.append(str(int(_get(rect, key, 0))))
    return tuple(values)


def _pattern(control: Any, uia: Any, name: str) -> Any:
    # Custom/Pane controls can expose TextPattern without GetTextPattern().
    getter = getattr(control, "GetPattern", None)
    pattern_id = getattr(getattr(uia, "PatternId", None), name, None)
    if getter is not None and pattern_id is not None:
        return getter(pattern_id)
    getter = getattr(control, "Get" + name, None)
    return getter() if getter is not None else None


def read_selected_text(
    uia: Any, hwnd: int, max_characters: int, *, pointer: tuple[int, int] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> SelectionSnapshot | None:
    """Try UIA TextPattern selection only, never fall back to grabbing a document.

    A provider may not expose selected text; returning None is intentional.
    Ctrl+C probing is *not* allowed during passive toolbar detection.
    """
    def status(message: str) -> None:
        if on_status is not None:
            on_status(message)

    if not hwnd or WindowService.get_foreground_window() != hwnd:
        status("UIA: source window is no longer foreground")
        return None
    target_pid = WindowService.get_window_process_id(hwnd)
    visited: dict[int, Any] = {}
    pattern_count = 0
    errors: set[str] = set()
    rejected = False

    def eligible(control: Any) -> bool:
        pid = _get(control, "ProcessId", None)
        return target_pid is None or pid == target_pid

    def extract(control: Any) -> SelectionSnapshot | None:
        nonlocal pattern_count, rejected
        if not eligible(control) or _secure_control(control):
            return None
        try:
            identity = _identity(control)
            if id(control) in visited:
                return None
            visited[id(control)] = control
            text_pattern = _pattern(control, uia, "TextPattern")
            if text_pattern is None:
                return None
            pattern_count += 1
            selected_parts = []
            total = 0
            for selection_range in (text_pattern.GetSelection() or ()):
                part = selection_range.GetText(max_characters + 1 - total)
                if part:
                    total += len(str(part)) + (1 if selected_parts else 0)
                    selected_parts.append(str(part))
                    if total > max_characters:
                        break
            selected = "\n".join(selected_parts).strip()
            if not selected:
                return None
            if total > max_characters:
                rejected = True
                status("UIA: selected text exceeds configured character limit")
                return None
            if WindowService.get_foreground_window() != hwnd:
                rejected = True
                status("UIA: source window changed during probe")
                return None
            value_pattern = None
            try:
                value_pattern = _pattern(control, uia, "ValuePattern")
            except Exception:
                pass
            writable = (value_pattern is not None and
                        not bool(_get(value_pattern, "IsReadOnly", True)))
            status(f"UIA: selection read ({len(selected)} characters)")
            return SelectionSnapshot(selected, hwnd, identity, writable)
        except Exception as exc:
            # Exception messages from providers may contain document content.
            errors.add(type(exc).__name__)
            logger.info("Quick UX UIA pattern read failed: control=%s exception=%s hresult=%s",
                        _get(control, "ControlTypeName", "unknown"), type(exc).__name__,
                        getattr(exc, "hresult", "n/a"))
            return None

    candidates: list[Any] = []
    try:
        focused = uia.GetFocusedControl()
        if focused:
            if _secure_control(focused):
                status("UIA: password control excluded")
                return None
            candidates.append(focused)
    except Exception as exc:
        errors.add(type(exc).__name__)
    if pointer is not None:
        try:
            under_mouse = uia.ControlFromPoint(*pointer)
            if under_mouse:
                if _secure_control(under_mouse):
                    status("UIA: password control excluded")
                    return None
                candidates.append(under_mouse)
        except Exception as exc:
            errors.add(type(exc).__name__)

    for child in candidates:
        control = child
        for _ in range(12):
            if control is None:
                break
            if _secure_control(control):
                # Never walk upward from a secure field into its document.
                break
            if not eligible(control):
                break
            snapshot = extract(control)
            if rejected:
                return None
            if snapshot is not None:
                return snapshot
            try:
                control = control.GetParentControl()
            except Exception:
                break
    # Browser/Electron focus may be on a container, with the selected document
    # in a descendant rather than an ancestor. Search only this source window,
    # with a strict node/depth budget, skipping entire password subtrees.
    try:
        root = uia.ControlFromHandle(hwnd)
        pending = deque([(root, 0)]) if root is not None else deque()
        examined = 0
        while pending and examined < 64:
            control, depth = pending.popleft()
            examined += 1
            if control is None or not eligible(control) or _secure_control(control):
                continue
            snapshot = extract(control)
            if rejected:
                return None
            if snapshot is not None:
                return snapshot
            if depth < 6:
                child = control.GetFirstChildControl()
                while child is not None and len(pending) + examined < 64:
                    pending.append((child, depth + 1))
                    child = child.GetNextSiblingControl()
    except Exception as exc:
        if not isinstance(exc, AttributeError):
            errors.add(type(exc).__name__)
    details = ", ".join(sorted(errors)) or "none"
    status(f"UIA: no selection; controls={len(visited)}, TextPatterns={pattern_count}, errors={details}")
    return None


class WindowsUiaSelectionReader:
    """Called only on the worker's COM-initialized thread."""

    def __init__(self, max_characters: int = 6000) -> None:
        self.max_characters = max_characters
        self.last_status = "UIA: not probed yet"

    def probe(self, hwnd: int, pointer: tuple[int, int] | None = None) -> SelectionSnapshot | None:
        if os.name != "nt":
            return None
        import uiautomation as uia

        return read_selected_text(uia, hwnd, self.max_characters, pointer=pointer,
                                  on_status=lambda value: setattr(self, "last_status", value))

    def verify(self, snapshot: SelectionSnapshot) -> bool:
        # This is a strict check to prevent pasting into a changed selection.
        current = self.probe(snapshot.hwnd)
        return bool(
            current
            and current.hwnd == snapshot.hwnd
            and current.identity == snapshot.identity
            and current.text == snapshot.text
            and current.replace_allowed
        )
