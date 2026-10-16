from __future__ import annotations

import math

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget

from app.config import UiSection
from app.models import RegionCaptureResult


class RegionSelectorOverlay(QWidget):
    """One-monitor drag selector used by Region Translate.

    Multi-monitor setups are supported by opening the selector on the monitor
    that contains the cursor when Region Translate starts. V0.4.0 intentionally
    does not allow one selection rectangle to span multiple monitors; this avoids
    ambiguous per-monitor DPI conversion while still supporting any attached
    screen.
    """

    captured = Signal(object)
    cancelled = Signal(str)
    failed = Signal(str, str)

    def __init__(self, config: UiSection) -> None:
        super().__init__()
        self._config = config
        self._job_id = ""
        self._screen = None
        self._screen_geometry = QRect()
        self._screenshot = None
        self._drag_start: QPoint | None = None
        self._drag_end: QPoint | None = None
        self._dragging = False

        self.setWindowTitle("AI Screen Translator - Chọn vùng")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

        self._hint = QLabel(self)
        self._hint.setText(
            "Kéo chuột để chọn vùng cần dịch  |  Esc / chuột phải để hủy"
        )
        self._hint.setStyleSheet(
            "QLabel { background: rgba(8,14,26,240); color: #DDF6FF; "
            "border: 1px solid #38BDF8; padding: 10px 16px; border-radius: 9px; font-size: 13px; }"
        )
        self._hint.adjustSize()

    def update_config(self, config: UiSection) -> None:
        self._config = config

    def is_selecting(self) -> bool:
        return bool(self._job_id) and self.isVisible()

    def begin(self, job_id: str) -> None:
        if self.is_selecting():
            self.cancel_current()

        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            self.failed.emit(job_id, "Không tìm thấy màn hình để chụp.")
            return

        try:
            screenshot = screen.grabWindow(0)
        except Exception as exc:
            self.failed.emit(job_id, f"Không thể chụp màn hình: {exc}")
            return
        if screenshot.isNull():
            self.failed.emit(job_id, "Ảnh chụp màn hình rỗng.")
            return

        self._job_id = job_id
        self._screen = screen
        self._screen_geometry = screen.geometry()
        self._screenshot = screenshot
        self._drag_start = None
        self._drag_end = None
        self._dragging = False

        self.setGeometry(self._screen_geometry)
        self._hint.move(20, 20)
        self._hint.raise_()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self.update()

    def cancel_current(self) -> None:
        if not self._job_id:
            self.hide()
            return
        job_id = self._job_id
        self._reset_state()
        self.cancelled.emit(job_id)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.cancel_current()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self.cancel_current()
            event.accept()
            return
        if event.button() != Qt.LeftButton:
            return
        point = self._clamp_point(event.position().toPoint())
        self._drag_start = point
        self._drag_end = point
        self._dragging = True
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._dragging or self._drag_start is None:
            return
        self._drag_end = self._clamp_point(event.position().toPoint())
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton or not self._dragging:
            return
        self._drag_end = self._clamp_point(event.position().toPoint())
        self._dragging = False
        selection = self._selection_rect()
        min_size = max(2, int(self._config.region_min_size_px))
        if selection.width() < min_size or selection.height() < min_size:
            self._drag_start = None
            self._drag_end = None
            self._hint.setText(
                f"Vùng quá nhỏ. Hãy kéo vùng ít nhất {min_size} x {min_size}px  |  Esc để hủy"
            )
            self._hint.adjustSize()
            self.update()
            event.accept()
            return

        try:
            result = self._capture_selection(selection)
        except Exception as exc:
            job_id = self._job_id
            self._reset_state()
            self.failed.emit(job_id, f"Không thể lấy ảnh vùng đã chọn: {exc}")
            return

        self._reset_state()
        self.captured.emit(result)
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: ANN001 - Qt virtual method
        del event
        painter = QPainter(self)
        opacity = max(0, min(220, int(self._config.region_overlay_opacity)))
        painter.fillRect(self.rect(), QColor(0, 0, 0, opacity))

        selection = self._selection_rect()
        if not selection.isNull() and selection.width() > 0 and selection.height() > 0:
            # Punch a transparent hole so the selected desktop region remains visible.
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#38BDF8"), 2))
            painter.drawRect(selection.adjusted(0, 0, -1, -1))

            size_text = f"{selection.width()} x {selection.height()}"
            label_rect = QRect(selection.left(), max(0, selection.top() - 26), 150, 24)
            painter.fillRect(label_rect, QColor(8, 14, 26, 240))
            painter.setPen(QColor("#6EE7B7"))
            painter.drawText(label_rect.adjusted(6, 0, -4, 0), Qt.AlignVCenter, size_text)

    def _selection_rect(self) -> QRect:
        if self._drag_start is None or self._drag_end is None:
            return QRect()
        return QRect(self._drag_start, self._drag_end).normalized().intersected(self.rect())

    def _clamp_point(self, point: QPoint) -> QPoint:
        return QPoint(
            min(max(point.x(), 0), max(0, self.width() - 1)),
            min(max(point.y(), 0), max(0, self.height() - 1)),
        )

    def _capture_selection(self, selection: QRect) -> RegionCaptureResult:
        if self._screenshot is None or self._screen is None:
            raise RuntimeError("Region selector has no screenshot")

        logical_width = max(1, self._screen_geometry.width())
        logical_height = max(1, self._screen_geometry.height())
        scale_x = self._screenshot.width() / logical_width
        scale_y = self._screenshot.height() / logical_height

        left = max(0, int(math.floor(selection.left() * scale_x)))
        top = max(0, int(math.floor(selection.top() * scale_y)))
        right = min(
            self._screenshot.width(),
            int(math.ceil((selection.right() + 1) * scale_x)),
        )
        bottom = min(
            self._screenshot.height(),
            int(math.ceil((selection.bottom() + 1) * scale_y)),
        )
        pixel_rect = QRect(left, top, max(1, right - left), max(1, bottom - top))
        cropped = self._screenshot.copy(pixel_rect)
        if cropped.isNull():
            raise RuntimeError("Qt returned an empty crop")

        raw = QByteArray()
        buffer = QBuffer(raw)
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            raise RuntimeError("Cannot open PNG memory buffer")
        try:
            if not cropped.save(buffer, "PNG"):
                raise RuntimeError("Qt failed to encode captured region as PNG")
        finally:
            buffer.close()

        return RegionCaptureResult(
            job_id=self._job_id,
            image_png=bytes(raw),
            screen_name=str(self._screen.name()),
            width_px=cropped.width(),
            height_px=cropped.height(),
        )

    def _reset_state(self) -> None:
        self.hide()
        self._job_id = ""
        self._screen = None
        self._screen_geometry = QRect()
        self._screenshot = None
        self._drag_start = None
        self._drag_end = None
        self._dragging = False
        self._hint.setText(
            "Kéo chuột để chọn vùng cần dịch  |  Esc / chuột phải để hủy"
        )
        self._hint.adjustSize()
