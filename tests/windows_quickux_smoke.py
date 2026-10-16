"""Run explicitly on Windows: python tests/windows_quickux_smoke.py.

Creates an offscreen native RichEdit with synthetic selected text. Does not touch
the user's focus, selection, clipboard, providers or running translator.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.quickux.uia_reader import read_selected_text


def main():
    if os.name != "nt":
        raise SystemExit("Windows required")
    user32 = ctypes.windll.user32
    create = user32.CreateWindowExW
    create.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                      wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                      ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE,
                      wintypes.LPVOID]
    create.restype = wintypes.HWND
    send = user32.SendMessageW
    send.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    send.restype = ctypes.c_ssize_t
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    root = create(0x08000000, "STATIC", "Quick UX synthetic smoke", 0x80000000,
                  -32000, -32000, 300, 100, None, None, None, None)
    if not root:
        raise ctypes.WinError()
    try:
        ctypes.windll.kernel32.LoadLibraryW("Msftedit.dll")
        editor = create(0, "RICHEDIT50W", "Synthetic selected text", 0x50000004,
                        0, 0, 300, 100, root, None, None, None)
        if not editor:
            raise ctypes.WinError()
        user32.ShowWindow(root, 4)  # SW_SHOWNOACTIVATE, offscreen
        send(editor, 0x00B1, 0, 9)  # EM_SETSEL: "Synthetic"
        outcome = []

        def probe():
            try:
                import uiautomation as uia
                with uia.UIAutomationInitializerInThread():
                    control = uia.ControlFromHandle(editor)
                    backend = SimpleNamespace(
                        PatternId=uia.PatternId,
                        GetFocusedControl=lambda: control,
                        ControlFromHandle=uia.ControlFromHandle,
                    )
                    statuses = []
                    with patch("app.quickux.uia_reader.WindowService.get_foreground_window",
                               return_value=root):
                        snapshot = read_selected_text(backend, root, 100,
                                                      on_status=statuses.append)
                    if snapshot is None or snapshot.text != "Synthetic":
                        raise AssertionError(f"Native selection not detected: {statuses}")
                    outcome.append("PASS: native Win32 RichEdit selection read through UIA")
            except Exception as exc:
                outcome.append(exc)

        worker = threading.Thread(target=probe, daemon=True)
        worker.start()
        message = wintypes.MSG()
        deadline = time.monotonic() + 20
        while worker.is_alive() and time.monotonic() < deadline:
            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
            time.sleep(0.01)
        if not outcome:
            raise TimeoutError("Native UIA smoke test timed out")
        if isinstance(outcome[0], Exception):
            raise outcome[0]
        print(outcome[0])
    finally:
        user32.DestroyWindow(root)


if __name__ == "__main__":
    main()
