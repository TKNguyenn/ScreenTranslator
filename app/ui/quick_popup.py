from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer, QPoint, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QGuiApplication, QImage, QPainter, QPalette, QPen, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSizeGrip, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.config import QuickUxSection
from app.models import RequestMode
from app.prompts import EXPLAIN_PROMPT_VERSION
from app.ui.quick_toolbar import clamp_floating_position
from app.ui.floating_surface import FloatingSurface
from app.ui.theme import asset_icon


TARGET_LABELS = {"vi": "Tiếng Việt", "en": "English", "zh-Hant": "繁體中文"}


class _OutputDocument(QTextDocument):
    def loadResource(self, resource_type, name):
        # A non-null placeholder prevents Qt's image handler falling back to disk.
        if resource_type == QTextDocument.ImageResource:
            image = QImage(1, 1, QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            return image
        return None


class WaveTranslationOutput(QTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setDocument(_OutputDocument(self))
        self._loading = False
        self._wave_clock = QElapsedTimer()
        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(33)
        self._wave_timer.timeout.connect(self.viewport().update)

    def start_loading(self, text: str = "Đang dịch...") -> None:
        # Keep real text available to accessibility while painting the animated glyphs.
        self.setPlainText(text)
        self._loading = True
        self._wave_clock.start()
        if self.isVisible():
            self._wave_timer.start()
        self.viewport().update()

    def setPlainText(self, text: str) -> None:
        self._loading = False
        self._wave_timer.stop()
        super().setPlainText(text)

    def setMarkdown(self, text: str) -> None:
        self._loading = False
        self._wave_timer.stop()
        self.document().setMarkdown(text, QTextDocument.MarkdownNoHTML)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._loading:
            self._wave_timer.start()

    def hideEvent(self, event) -> None:
        self._wave_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        if not self._loading:
            super().paintEvent(event)
            return
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), self.palette().brush(QPalette.Base))
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setFont(self.document().defaultFont())
        metrics = QFontMetricsF(painter.font())
        origin = self.cursorRect(QTextCursor(self.document())).topLeft()
        text = self.toPlainText()
        elapsed = self._wave_clock.elapsed()
        for index, letter in enumerate(text):
            phase = ((elapsed - index * 85) % 1650) / 1650
            lift = (1 - math.cos(2 * math.pi * phase / .6)) / 2 if phase < .6 else 0
            painter.setPen(QColor(round(238 - 139 * lift), round(245 - 6 * lift), 255))
            x = origin.x() + metrics.horizontalAdvance(text[:index])
            painter.drawText(QPointF(x, origin.y() + metrics.ascent() - 5 * lift), letter)


class PopupSizeGrip(QSizeGrip):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#849bbd"), 1.5))
        for offset in (3, 7, 11):
            painter.drawLine(self.width() - offset, self.height() - 3,
                             self.width() - 3, self.height() - offset)


class QuickTranslationPopup(FloatingSurface):
    replace_requested = Signal(str)
    closed = Signal()

    def __init__(self, config: QuickUxSection) -> None:
        super().__init__(resizable=True)
        self._config = config
        self._translation = ""
        self._original = ""
        self._stream_buffer = ""
        self._pending_job: str | None = None
        self._anchor = QPoint(0, 0)
        self._replace_allowed = False
        self._mode = RequestMode.POPUP
        self._pinned = False
        self.setObjectName("quickTranslationPopup")
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle("Bản dịch — AI Screen Translator")
        self.setMinimumSize(360, 280)
        self.resize(460, 360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(15, 13, 15, 10)
        outer.setSpacing(10)
        self._header = QWidget(self)
        head = QHBoxLayout(self._header)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(asset_icon().pixmap(30, 30))
        head.addWidget(logo)
        self.make_drag_handle(logo)
        title = QVBoxLayout()
        title.setSpacing(3)
        self._headline = QLabel("Bản dịch")
        self._headline.setObjectName("popupHeadline")
        self._headline.setTextFormat(Qt.PlainText)
        self._drag_hint = QLabel("Kéo để di chuyển")
        self._drag_hint.setObjectName("popupDragHint")
        title.addWidget(self._headline)
        title.addWidget(self._drag_hint)
        head.addLayout(title, 1)
        self.make_drag_handle(self._header)
        self.make_drag_handle(self._headline)
        self.make_drag_handle(self._drag_hint)
        self._pin = QPushButton("📌")
        self._pin.setObjectName("popupPin")
        self._pin.setFixedSize(34, 34)
        self._pin.setToolTip("Ghim popup")
        self._pin.setAccessibleName("Ghim popup")
        self._pin_opacity = QGraphicsOpacityEffect(self._pin)
        self._pin_opacity.setOpacity(0.5)
        self._pin.setGraphicsEffect(self._pin_opacity)
        self._pin.setCheckable(True)
        self._pin.toggled.connect(self._toggle_pin)
        head.addWidget(self._pin)
        self._close = QPushButton("×")
        self._close.setObjectName("popupClose")
        self._close.setFixedSize(30, 30)
        self._close.setToolTip("Đóng popup (Esc)")
        self._close.clicked.connect(self.force_close)
        head.addWidget(self._close)
        outer.addWidget(self._header)
        self._meta = QLabel("")
        self._meta.setTextFormat(Qt.PlainText)
        self._meta.setWordWrap(True)
        self._meta.setObjectName("popupMeta")
        self.make_drag_handle(self._meta)
        outer.addWidget(self._meta)
        self._splitter = QSplitter(Qt.Vertical, self)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(6)
        self._output = WaveTranslationOutput()
        self._output.setObjectName("translationOutput")
        self._output.setReadOnly(True)
        self._output.setFocusPolicy(Qt.NoFocus)
        self._output.setMinimumHeight(80)
        self._splitter.addWidget(self._output)
        self._original_view = QPlainTextEdit()
        self._original_view.setObjectName("originalOutput")
        self._original_view.setReadOnly(True)
        self._original_view.setFocusPolicy(Qt.NoFocus)
        self._original_view.setMinimumHeight(65)
        self._original_view.setToolTip("Văn bản gốc — kéo thanh phân cách để đổi chiều cao")
        self._splitter.addWidget(self._original_view)
        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 1)
        self._original_view.setVisible(False)
        outer.addWidget(self._splitter, 1)
        foot = QHBoxLayout()
        self._copy = QPushButton("Sao chép")
        self._copy.setObjectName("popupCopy")
        self._copy.clicked.connect(self.copy_translation)
        self._replace = QPushButton("Thay thế")
        self._replace.clicked.connect(self._request_replace)
        self._show_original = QPushButton("Xem gốc")
        self._show_original.setToolTip("Hiện / ẩn văn bản gốc")
        self._show_original.setCheckable(True)
        self._show_original.toggled.connect(self._toggle_original)
        foot.addWidget(self._copy)
        foot.addWidget(self._replace)
        foot.addWidget(self._show_original)
        outer.addLayout(foot)
        status = QHBoxLayout()
        self._feedback = QLabel("")
        self._feedback.setTextFormat(Qt.PlainText)
        self._feedback.setWordWrap(True)
        self._feedback.setObjectName("popupFeedback")
        status.addWidget(self._feedback, 1)
        self._size_grip = PopupSizeGrip(self)
        self._size_grip.setFixedSize(18, 18)
        self._size_grip.setToolTip("Kéo góc hoặc cạnh để đổi kích thước")
        self._size_grip.setFocusPolicy(Qt.NoFocus)
        status.addWidget(self._size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        outer.addLayout(status)
        for button in (self._pin, self._close, self._copy, self._replace, self._show_original):
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
          QLabel { color: #eef4ff; background: transparent; }
          QLabel#popupHeadline { font-size: 15px; font-weight: 700; }
          QLabel#popupDragHint { color: #91a6c5; font-size: 11px; }
          QLabel#popupMeta { color: #a7bbd6; font-size: 11px; }
          QLabel#popupFeedback { color: #80dfd1; font-size: 11px; }
          QWidget#quickTranslationPopup QPushButton { background: #153449;
            color: #f1f5ff; border: 1px solid #2C667B; border-radius: 7px;
            padding: 7px 10px; font-size: 12px; font-weight: 600; }
          QWidget#quickTranslationPopup QPushButton:hover { background: #1B5064; border-color: #38BDF8; }
          QWidget#quickTranslationPopup QPushButton:pressed { background: #426186; }
          QWidget#quickTranslationPopup QPushButton:checked { background: #214d55; border-color: #72dcd0; }
          QWidget#quickTranslationPopup QPushButton:disabled { color: #8b9db9; background: #1d2b40; border-color: #30425c; }
          QWidget#quickTranslationPopup QPushButton#popupPin { padding: 0;
            font-family: "Segoe UI Emoji"; font-size: 20px; font-weight: 400;
            background: transparent; border: none; }
          QWidget#quickTranslationPopup QPushButton#popupCopy { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #38BDF8,stop:1 #10B981); color: #032535; border-color: #67E8CF; }
          QWidget#quickTranslationPopup QPushButton#popupCopy:hover { background: #67E8CF; }
          QWidget#quickTranslationPopup QPushButton#popupCopy:disabled { background: #1d2b40; color: #8b9db9; border-color: #30425c; }
          QWidget#quickTranslationPopup QPushButton#popupClose { padding: 0; font-size: 22px; background: transparent; border: none; }
          QWidget#quickTranslationPopup QPushButton#popupClose:hover { background: #593342; color: #ffbdc9; }
          QWidget#quickTranslationPopup QPlainTextEdit, QWidget#quickTranslationPopup QTextEdit { background: #0B1A2C;
            color: #f3f6ff; border: 1px solid #285368; border-radius: 8px;
            padding: 10px; font-size: 14px; selection-background-color: #386381;
            selection-color: #ffffff; }
          QSplitter::handle { background: #080E1A; }
          QSplitter::handle:hover { background: #405a78; }
          QScrollBar:vertical { background: #1a2941; width: 8px; margin: 3px; }
          QScrollBar::handle:vertical { background: #6882a2; min-height: 24px; border-radius: 2px; }
          QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
          QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_stream)
        self._copy.setEnabled(False)
        self._replace.setEnabled(False)

    @property
    def pinned(self) -> bool:
        return self._pinned

    def set_config(self, config: QuickUxSection) -> None:
        self._config = config

    def _toggle_pin(self, enabled: bool) -> None:
        self._pinned = enabled
        self._pin_opacity.setOpacity(1.0 if enabled else 0.5)
        self._pin.setToolTip("Bỏ ghim" if enabled else "Ghim popup")
        self._pin.setAccessibleName(self._pin.toolTip())

    def _toggle_original(self, enabled: bool) -> None:
        self._original_view.setVisible(enabled)
        self._show_original.setText("Ẩn gốc" if enabled else "Xem gốc")
        if enabled:
            self._splitter.setSizes([max(80, self._splitter.height() * 2 // 3),
                                     max(65, self._splitter.height() // 3)])

    def force_close(self) -> None:
        self._pending_job = None
        self._flush_timer.stop()
        self._stream_buffer = ""
        self.hide()
        self.closed.emit()

    def dismiss_if_unpinned(self) -> None:
        if not self._pinned:
            self.force_close()

    def start(self, job_id: str, original: str, target: str, style: str,
              speed: str, provider_name: str, model: str, anchor: QPoint,
              replace_allowed: bool, *, mode: RequestMode = RequestMode.POPUP) -> None:
        self._pending_job = job_id
        self._translation = ""
        self._stream_buffer = ""
        self._flush_timer.stop()
        self._original = original
        self._mode = mode
        explain = mode == RequestMode.EXPLAIN
        self._replace_allowed = replace_allowed and not explain
        self._replace.setVisible(not explain)
        self._show_original.setVisible(not explain)
        self._anchor = QPoint(anchor)
        title = "Giải thích" if explain else "Bản dịch"
        self.setWindowTitle(f"{title} — AI Screen Translator")
        self._headline.setText(f"{title} · {TARGET_LABELS.get(target, target)}")
        self._meta.setText(f"{provider_name} / {model}\n{EXPLAIN_PROMPT_VERSION if explain else style} · {speed}")
        self._output.start_loading("Đang giải thích..." if explain else "Đang dịch...")
        self._original_view.setPlainText(original)
        self._original_view.setVisible(not explain and self._show_original.isChecked())
        self._feedback.setText("Đang giải thích…" if explain else "Đang dịch…")
        self._copy.setEnabled(False)
        self._replace.setEnabled(False)
        self._show_near(anchor)

    def append_delta(self, job_id: str, delta: str) -> None:
        if self._pending_job != job_id or not delta:
            return
        self._stream_buffer += delta
        if not self._flush_timer.isActive():
            self._flush_timer.start(55)

    def _flush_stream(self) -> None:
        if not self._stream_buffer or self._pending_job is None:
            return
        if not self._translation:
            self._output.setPlainText("")
        scrollbar = self._output.verticalScrollBar()
        follow = scrollbar.value() >= scrollbar.maximum() - 4
        scroll_position = scrollbar.value()
        self._translation += self._stream_buffer
        if self._mode == RequestMode.EXPLAIN:
            self._output.setMarkdown(self._translation)
        else:
            cursor = QTextCursor(self._output.document())
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(self._stream_buffer)
        if follow:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(scroll_position)
        self._feedback.setText("Đang nhận giải thích…" if self._mode == RequestMode.EXPLAIN else "Đang nhận bản dịch…")
        self._stream_buffer = ""

    def finish(self, job_id: str, translated: str, cached: bool) -> None:
        if self._pending_job != job_id:
            return
        self._flush_timer.stop()
        self._stream_buffer = ""
        self._translation = translated
        if self._mode == RequestMode.EXPLAIN:
            self._output.setMarkdown(translated)
        else:
            self._output.setPlainText(translated)
        self._feedback.setText("Giải thích hoàn tất" if self._mode == RequestMode.EXPLAIN else
                               "Từ cache" if cached else "Dịch hoàn tất")
        self._copy.setEnabled(bool(translated))
        self._replace.setEnabled(bool(translated) and self._replace_allowed)

    def fail(self, job_id: str, message: str) -> None:
        if self._pending_job != job_id:
            return
        self._flush_timer.stop()
        self._stream_buffer = ""
        self._translation = ""
        explain = self._mode == RequestMode.EXPLAIN
        self._output.setPlainText(("Không thể giải thích. " if explain else "Không thể dịch. ") + message)
        self._feedback.setText("Chọn lại nội dung và bấm Explain để thử lại." if explain else
                               "Có thể dùng Alt+T để thử lại.")
        self._copy.setEnabled(False)
        self._replace.setEnabled(False)

    def show_replace_feedback(self, text: str, success: bool) -> None:
        self._feedback.setText(text)
        self._replace.setEnabled(not success and bool(self._translation) and self._replace_allowed)

    def copy_translation(self) -> None:
        if not self._translation:
            return
        text = self._output.toPlainText() if self._mode == RequestMode.EXPLAIN else self._translation
        QGuiApplication.clipboard().setText(text)
        self._feedback.setText("Đã sao chép giải thích" if self._mode == RequestMode.EXPLAIN else "Đã sao chép bản dịch")

    def _request_replace(self) -> None:
        if self._translation and self._replace_allowed:
            self._replace.setEnabled(False)
            self._feedback.setText("Đang kiểm tra vùng chọn trước khi thay thế...")
            self.replace_requested.emit(self._translation)

    def _show_near(self, anchor: QPoint) -> None:
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(min(self.width(), available.width()), min(self.height(), available.height()))
        # Prefer below/right of selection, fall back above/left at edges.
        self.move(clamp_floating_position(anchor, self.width(), self.height(), available, offset=18))
        self.show()
        self.raise_()
