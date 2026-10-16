"""Aurora Bento identity shared by every desktop surface."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parents[1] / "assets"
OCEAN = "#080E1A"
CYAN = "#38BDF8"
EMERALD = "#10B981"


def asset_icon(name: str = "app_icon.ico") -> QIcon:
    return QIcon(str(ASSETS / name))


def apply_theme(app: QApplication) -> None:
    # Fusion avoids Windows light-mode controls leaking into dark forms/menus.
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in (
        (QPalette.Window, OCEAN), (QPalette.WindowText, "#EAF4FA"),
        (QPalette.Base, "#0A1524"), (QPalette.AlternateBase, "#14263A"),
        (QPalette.Text, "#EAF4FA"), (QPalette.Button, "#152C40"),
        (QPalette.ButtonText, "#EAF4FA"), (QPalette.Highlight, "#11617C"),
        (QPalette.HighlightedText, "#FFFFFF"), (QPalette.ToolTipBase, "#13293A"),
        (QPalette.ToolTipText, "#EAF4FA"), (QPalette.PlaceholderText, "#7E9BB0"),
        (QPalette.Link, CYAN),
    ):
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#6D879B"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#6D879B"))
    app.setPalette(palette)
    sheet = (ASSETS / "ocean_theme.qss").read_text(encoding="utf-8")
    sheet = sheet.replace("@ASSETS@", ASSETS.as_posix())
    app.setStyleSheet(sheet)
    app.setWindowIcon(asset_icon())


def dark_titlebar(widget) -> None:
    """Use a dark native frame; painted glass keeps the content predictable."""
    if os.name != "nt":
        return
    try:
        setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
        setter.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        setter.restype = ctypes.c_long
        value = ctypes.c_int(1)
        setter(int(widget.winId()), 20, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError):
        pass
