from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class FloatingSurface(QWidget):
    """Paint the card explicitly: custom QWidget styles alone can be transparent."""

    def __init__(self, *, resizable: bool = False) -> None:
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self._resizable = resizable
        self._resize_edges = Qt.Edges()
        self._resize_origin = QPoint()
        self._resize_geometry = QRect()
        self._drag_offset: QPoint | None = None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # An opaque fill separates the text from every source-app background.
        fill = QLinearGradient(0, 0, self.width(), self.height())
        fill.setColorAt(0, QColor("#0D2032"))
        fill.setColorAt(.5, QColor("#080E1A"))
        fill.setColorAt(1, QColor("#0B292B"))
        rim = QLinearGradient(0, 0, self.width(), self.height())
        rim.setColorAt(0, QColor("#38BDF8"))
        rim.setColorAt(1, QColor("#10B981"))
        painter.setBrush(fill)
        painter.setPen(QPen(rim, 1.0))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)

    def make_drag_handle(self, widget: QWidget) -> None:
        widget.setCursor(Qt.SizeAllCursor)
        widget.setToolTip("Kéo để di chuyển popup")
        widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            return True
        if event.type() == QEvent.MouseMove and self._drag_offset is not None:
            if event.buttons() & Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
            return True
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self._drag_offset is not None:
                self._drag_offset = None
                return True
        return super().eventFilter(watched, event)

    def _edges_at(self, position: QPoint) -> Qt.Edges:
        edges = Qt.Edges()
        if not self._resizable:
            return edges
        if position.x() < 7:
            edges |= Qt.LeftEdge
        elif position.x() >= self.width() - 7:
            edges |= Qt.RightEdge
        if position.y() < 7:
            edges |= Qt.TopEdge
        elif position.y() >= self.height() - 7:
            edges |= Qt.BottomEdge
        return edges

    @staticmethod
    def _cursor_for_edges(edges: Qt.Edges):
        if edges in (Qt.TopEdge | Qt.LeftEdge, Qt.BottomEdge | Qt.RightEdge):
            return Qt.SizeFDiagCursor
        if edges in (Qt.TopEdge | Qt.RightEdge, Qt.BottomEdge | Qt.LeftEdge):
            return Qt.SizeBDiagCursor
        if edges & (Qt.LeftEdge | Qt.RightEdge):
            return Qt.SizeHorCursor
        if edges & (Qt.TopEdge | Qt.BottomEdge):
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event) -> None:
        edges = self._edges_at(event.position().toPoint())
        if event.button() == Qt.LeftButton and edges:
            self._resize_edges = edges
            self._resize_origin = event.globalPosition().toPoint()
            self._resize_geometry = self.geometry()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resize_edges and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._resize_origin
            rect = QRect(self._resize_geometry)
            if self._resize_edges & Qt.LeftEdge:
                rect.setLeft(min(rect.left() + delta.x(), rect.right() - self.minimumWidth() + 1))
            if self._resize_edges & Qt.RightEdge:
                rect.setRight(max(rect.right() + delta.x(), rect.left() + self.minimumWidth() - 1))
            if self._resize_edges & Qt.TopEdge:
                rect.setTop(min(rect.top() + delta.y(), rect.bottom() - self.minimumHeight() + 1))
            if self._resize_edges & Qt.BottomEdge:
                rect.setBottom(max(rect.bottom() + delta.y(), rect.top() + self.minimumHeight() - 1))
            self.setGeometry(rect)
            event.accept()
            return
        self.setCursor(self._cursor_for_edges(self._edges_at(event.position().toPoint())))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._resize_edges:
            self._resize_edges = Qt.Edges()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def hideEvent(self, event) -> None:
        self._drag_offset = None
        self._resize_edges = Qt.Edges()
        super().hideEvent(event)
