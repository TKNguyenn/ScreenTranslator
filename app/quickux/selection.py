from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MouseSelectionCandidate:
    hwnd: int
    x: int
    y: int


@dataclass(frozen=True)
class SelectionSnapshot:
    """Selected text read passively from UIA; no clipboard changes occur."""

    text: str
    hwnd: int
    identity: tuple[str, ...]
    replace_allowed: bool = True


@dataclass(frozen=True)
class QuickSelectionProbe:
    serial: int
    snapshot: SelectionSnapshot | None
    status: str = ""


@dataclass(frozen=True)
class QuickSelectionCheck:
    job_id: str
    valid: bool
    reason: str = ""


class MouseGestureRecognizer:
    """Recognizes text-selection drags and double-clicks, not ordinary single clicks."""

    def __init__(self, min_drag_px: int = 8, double_click_s: float = 0.45) -> None:
        self.min_drag_px = min_drag_px
        self.double_click_s = double_click_s
        self._down: tuple[int, int, float, int] | None = None
        self._last_release: tuple[int, int, float, int] | None = None

    def press(self, x: int, y: int, at_s: float, hwnd: int) -> None:
        self._down = (x, y, at_s, hwnd)

    def release(self, x: int, y: int, at_s: float, hwnd: int) -> bool:
        down = self._down
        self._down = None
        prev = self._last_release
        self._last_release = (x, y, at_s, hwnd)
        if not hwnd or down is None or hwnd != down[3]:
            return False
        drag = math.hypot(x - down[0], y - down[1]) >= self.min_drag_px
        double_click = bool(
            prev
            and hwnd == prev[3]
            and 0 < at_s - prev[2] <= self.double_click_s
            and math.hypot(x - prev[0], y - prev[1]) < self.min_drag_px
            and math.hypot(x - down[0], y - down[1]) < self.min_drag_px
        )
        return drag or double_click
