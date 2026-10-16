from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton

from app.config import QuickUxSection
from app.ui.floating_surface import FloatingSurface
from app.ui.theme import asset_icon


LANGUAGE_BUTTONS = (("vi", "VI"), ("en", "EN"), ("zh-Hant", "繁"))


def clamp_floating_position(
    anchor: QPoint, width: int, height: int, available, *, offset: int = 12
) -> QPoint:
    """Clamp a floating window within one monitor's work area (negative origins OK)."""
    x = anchor.x() + offset
    y = anchor.y() + offset
    if x + width > available.right() + 1:
        x = anchor.x() - width - offset
    if y + height > available.bottom() + 1:
        y = anchor.y() - height - offset
    x = min(max(available.left(), x), max(available.left(), available.right() + 1 - width))
    y = min(max(available.top(), y), max(available.top(), available.bottom() + 1 - height))
    return QPoint(x, y)


class QuickToolbar(FloatingSurface):
    language_requested = Signal(str)
    translate_replace_requested = Signal()
    settings_requested = Signal()
    close_requested = Signal()

    def __init__(self, config: QuickUxSection) -> None:
        super().__init__()
        self._config = config
        self._anchor = QPoint(0, 0)
        self.setObjectName("quickToolbar")
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(4)
        badge = QLabel("Dịch")
        logo = QLabel()
        logo.setPixmap(asset_icon().pixmap(22, 22))
        layout.addWidget(logo)
        badge.setObjectName("toolbarBadge")
        layout.addWidget(badge)
        divider = QFrame()
        divider.setObjectName("toolbarDivider")
        divider.setFixedSize(1, 22)
        layout.addWidget(divider)
        self._buttons: dict[str, QPushButton] = {}
        for code, label in LANGUAGE_BUTTONS:
            button = QPushButton(label, self)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(f"Dịch sang {code} với model/style/speed hiện tại")
            button.clicked.connect(lambda checked=False, lang=code: self.language_requested.emit(lang))
            layout.addWidget(button)
            self._buttons[code] = button
        self._more = QPushButton("…", self)
        self._more.setToolTip("Thao tác khác")
        self._more.setFocusPolicy(Qt.NoFocus)
        self._more.setCursor(Qt.PointingHandCursor)
        menu = QMenu(self._more)
        menu.addAction("Dịch và thay thế (ngôn ngữ đang chọn)", lambda: self.translate_replace_requested.emit())
        menu.addSeparator()
        menu.addAction("Cài đặt Quick UX", lambda: self.settings_requested.emit())
        menu.addAction("Ẩn toolbar", lambda: self.close_requested.emit())
        self._more.setMenu(menu)
        self._menu = menu
        menu.aboutToShow.connect(lambda: self._dismiss_timer.stop())
        menu.aboutToHide.connect(lambda: self._dismiss_timer.start(1400))
        layout.addWidget(self._more)
        self.setStyleSheet("""
            QLabel#toolbarBadge { color: #72e1d5; font-size: 12px; font-weight: 700; padding: 0 6px; }
            QFrame#toolbarDivider { background: #28718a; border: none; }
            QWidget#quickToolbar QPushButton { color: #f4f7ff; border: 1px solid transparent;
                border-radius: 7px; background: #14344a; padding: 6px 9px;
                font-size: 13px; font-weight: 600; min-width: 24px; }
            QWidget#quickToolbar QPushButton:hover { background: #185268; border-color: #38BDF8; }
            QWidget#quickToolbar QPushButton:pressed { background: #426886; }
            QMenu { background: #0D2031; color: #f4f7ff; border: 1px solid #38BDF8; padding: 5px; }
            QMenu::item { padding: 8px 14px; border-radius: 4px; }
            QMenu::item:selected { background: #335271; }
            QMenu::separator { background: #40516c; height: 1px; margin: 4px 8px; }
        """)
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide)
        self.set_config(config)

    def set_config(self, config: QuickUxSection) -> None:
        self._config = config
        for code, button in self._buttons.items():
            button.setVisible(code in config.languages)
        self.adjustSize()

    def show_at(self, cursor_anchor: QPoint) -> None:
        self._anchor = QPoint(cursor_anchor)
        self.adjustSize()
        screen = QGuiApplication.screenAt(cursor_anchor) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        self.move(clamp_floating_position(cursor_anchor, self.width(), self.height(), screen.availableGeometry()))
        self.show()
        self.raise_()  # does not activate because of WindowDoesNotAcceptFocus
        self._dismiss_timer.start(self._config.toolbar_timeout_ms)

    def enterEvent(self, event) -> None:
        self._dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._menu.isVisible():
            self._dismiss_timer.start(1400)
        super().leaveEvent(event)

    def hideEvent(self, event) -> None:
        self._dismiss_timer.stop()
        super().hideEvent(event)
