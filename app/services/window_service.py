from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import time
from typing import Optional


class WindowService:
    @staticmethod
    def get_window_from_point(x: int, y: int) -> Optional[int]:
        """Win32 hit testing. POINT packed as two signed 32-bit coordinates."""
        if os.name != "nt":
            return None
        point = ((int(y) & 0xFFFFFFFF) << 32) | (int(x) & 0xFFFFFFFF)
        user32 = ctypes.windll.user32
        user32.WindowFromPoint.argtypes = [ctypes.c_longlong]
        user32.WindowFromPoint.restype = ctypes.c_void_p
        hwnd = user32.WindowFromPoint(point)
        return int(hwnd) if hwnd else None

    @staticmethod
    def get_foreground_window() -> Optional[int]:
        if os.name != "nt":
            return None
        getter = ctypes.windll.user32.GetForegroundWindow
        getter.argtypes = []
        getter.restype = wintypes.HWND
        hwnd = getter()
        return int(hwnd) if hwnd else None

    @staticmethod
    def activate_window(hwnd: Optional[int], settle_s: float = 0.12) -> bool:
        if os.name != "nt" or not hwnd:
            return False
        user32 = ctypes.windll.user32
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        if not user32.IsWindow(hwnd):
            return False
        user32.ShowWindow(hwnd, 5)
        ok = bool(user32.SetForegroundWindow(hwnd))
        if ok and settle_s > 0:
            time.sleep(settle_s)
        return ok

    @staticmethod
    def get_window_process_id(hwnd: Optional[int]) -> Optional[int]:
        if os.name != "nt" or not hwnd:
            return None
        pid = ctypes.c_ulong(0)
        getter = ctypes.windll.user32.GetWindowThreadProcessId
        getter.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        getter.restype = wintypes.DWORD
        getter(hwnd, ctypes.byref(pid))
        return int(pid.value) if pid.value else None

    @staticmethod
    def get_window_class_name(hwnd: Optional[int]) -> str:
        if os.name != "nt" or not hwnd:
            return ""
        buffer = ctypes.create_unicode_buffer(256)
        getter = ctypes.windll.user32.GetClassNameW
        getter.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        getter.restype = ctypes.c_int
        length = getter(hwnd, buffer, len(buffer))
        return buffer.value if length else ""

    @classmethod
    def is_own_process_window(cls, hwnd: Optional[int]) -> bool:
        pid = cls.get_window_process_id(hwnd)
        return pid == os.getpid() if pid is not None else False

    @classmethod
    def is_shell_surface(cls, hwnd: Optional[int]) -> bool:
        class_name = cls.get_window_class_name(hwnd)
        return class_name in {
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
            "NotifyIconOverflowWindow",
            "Progman",
            "WorkerW",
        }
