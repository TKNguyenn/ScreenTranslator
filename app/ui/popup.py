from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import UiSection
from app.ui.theme import asset_icon, dark_titlebar


class TranslationPopup(QWidget):
    replace_requested = Signal(str, object)

    def __init__(self, config: UiSection) -> None:
        super().__init__()
        self._config = config
        self._foreground_hwnd: Optional[int] = None
        self._translated_text = ""
        self._streaming_started = False
        self._allow_replace = True

        self.setWindowTitle("AI Screen Translator")
        self.setWindowIcon(asset_icon())
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.resize(config.popup_width, config.popup_height)
        self.setMinimumSize(400, 360)
        dark_titlebar(self)

        self._status = QLabel("")
        self._status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._status.setWordWrap(True)

        self._original = QPlainTextEdit()
        self._original.setReadOnly(True)
        self._translation = QPlainTextEdit()
        self._translation.setReadOnly(True)

        self._copy_button = QPushButton("Sao chép")
        self._copy_button.setProperty("primaryCta", True)
        self._replace_button = QPushButton("Thay thế vào app nguồn")
        self._close_button = QPushButton("Đóng")

        self._copy_button.clicked.connect(self._copy_translation)
        self._replace_button.clicked.connect(self._request_replace)
        self._close_button.clicked.connect(self.hide)

        buttons = QHBoxLayout()
        buttons.addWidget(self._copy_button)
        buttons.addWidget(self._replace_button)
        buttons.addStretch(1)
        buttons.addWidget(self._close_button)

        layout = QVBoxLayout(self)
        heading = QLabel("Bản dịch")
        heading.setProperty("pageTitle", True)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addWidget(QLabel("Văn bản gốc"))
        layout.addWidget(self._original)
        layout.addWidget(QLabel("Bản dịch / Trạng thái"))
        layout.addWidget(self._translation)
        layout.addWidget(self._status)
        layout.addLayout(buttons)

    def show_ocr_processing(
        self,
        provider_name: str,
        model: str,
        ocr_engine: str,
        image_size: tuple[int, int],
    ) -> None:
        self._foreground_hwnd = None
        self._translated_text = ""
        self._streaming_started = False
        self._allow_replace = False
        self._original.setPlainText("Đang nhận dạng chữ trong vùng đã chọn...")
        self._translation.setPlainText("OCR local đang xử lý. Lần chạy đầu có thể lâu hơn do khởi tạo model.")
        self._status.setText(
            f"OCR: {ocr_engine} | Capture: {image_size[0]}x{image_size[1]} | "
            f"Provider: {provider_name} | Model: {model}"
        )
        self._copy_button.setEnabled(False)
        self._replace_button.setEnabled(False)
        self._show_near_cursor()

    def show_processing(
        self,
        original: str,
        target_language: str,
        provider_name: str,
        model: str,
        foreground_hwnd: Optional[int],
        *,
        allow_replace: bool = True,
    ) -> None:
        self._foreground_hwnd = foreground_hwnd
        self._translated_text = ""
        self._streaming_started = False
        self._allow_replace = bool(allow_replace)
        self._original.setPlainText(original)
        self._translation.setPlainText("Đang dịch... vui lòng chờ.")
        self._status.setText(
            f"Target: {target_language} | Provider: {provider_name} | Model: {model}"
        )
        self._copy_button.setEnabled(False)
        self._replace_button.setEnabled(False)
        self._show_near_cursor()


    def append_stream_delta(self, delta: str) -> None:
        if not delta:
            return
        if not self._streaming_started:
            self._translation.clear()
            self._streaming_started = True
            self._status.setText(self._status.text() + " | Streaming")

        self._translated_text += delta
        cursor = self._translation.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(delta)
        self._translation.setTextCursor(cursor)
        self._translation.ensureCursorVisible()

    def show_translation(
        self,
        original: str,
        translated: str,
        target_language: str,
        cached: bool,
        foreground_hwnd: Optional[int],
        *,
        allow_replace: bool = True,
    ) -> None:
        self._foreground_hwnd = foreground_hwnd
        self._translated_text = translated
        self._streaming_started = False
        self._allow_replace = bool(allow_replace)
        self._original.setPlainText(original)
        self._translation.setPlainText(translated)
        source = "cache" if cached else "AI"
        self._status.setText(f"Target: {target_language} | Source: {source}")
        self._copy_button.setEnabled(True)
        self._replace_button.setEnabled(self._allow_replace)
        self._show_near_cursor()

    def show_error(
        self,
        original: str,
        error_message: str,
        log_path: str,
        foreground_hwnd: Optional[int] = None,
    ) -> None:
        self._foreground_hwnd = foreground_hwnd
        self._translated_text = ""
        self._streaming_started = False
        self._allow_replace = foreground_hwnd is not None
        self._original.setPlainText(original)
        self._translation.setPlainText(f"LỖI:\n{error_message}")
        self._status.setText(f"Chi tiết cũng được ghi tại: {log_path}")
        self._copy_button.setEnabled(False)
        self._replace_button.setEnabled(False)
        self._show_near_cursor()

    def _copy_translation(self) -> None:
        QGuiApplication.clipboard().setText(self._translated_text)
        self._status.setText(self._status.text() + " | Copied")

    def _request_replace(self) -> None:
        if self._translated_text and self._allow_replace:
            self.replace_requested.emit(self._translated_text, self._foreground_hwnd)

    def _show_near_cursor(self) -> None:
        self._move_near_cursor()
        self.show()
        self.raise_()
        self.activateWindow()

    def _move_near_cursor(self) -> None:
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        x = cursor_pos.x() + self._config.popup_offset_x
        y = cursor_pos.y() + self._config.popup_offset_y

        x = min(max(x, geometry.left()), geometry.right() - self.width())
        y = min(max(y, geometry.top()), geometry.bottom() - self.height())
        self.move(x, y)
