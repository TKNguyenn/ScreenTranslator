from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QWidget


class OceanBackdrop(QWidget):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#080E1A"))
        for x, y, color in ((.55, 0, QColor(15, 114, 153, 38)),
                            (1, .85, QColor(16, 185, 129, 24))):
            gradient = QRadialGradient(QPointF(self.width() * x, self.height() * y),
                                       self.width() * .75)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(8, 14, 26, 0))
            painter.fillRect(self.rect(), gradient)


class AuroraHero(QFrame):
    """Responsive native landscape, independent of provider or mockup text."""
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 16, 16)
        painter.setClipPath(clip)
        sky = QLinearGradient(0, 0, self.width(), self.height())
        sky.setColorAt(0, QColor("#0C283C"))
        sky.setColorAt(.65, QColor("#0D2730"))
        sky.setColorAt(1, QColor("#0B3030"))
        painter.fillRect(rect, sky)
        painter.save()
        painter.scale(self.width() / 900, self.height() / 220)
        glow = QRadialGradient(QPointF(670, 20), 280)
        glow.setColorAt(0, QColor(56, 189, 248, 55))
        glow.setColorAt(.6, QColor(16, 185, 129, 22))
        glow.setColorAt(1, QColor(8, 14, 26, 0))
        painter.fillRect(QRectF(0, 0, 900, 220), glow)
        for offset, alpha in ((0, 15), (9, 35), (16, 20)):
            ribbon = QPainterPath(QPointF(420, 25 + offset))
            ribbon.cubicTo(530, 100, 650, -30, 910, 55 + offset)
            painter.setPen(QPen(QColor(43, 220, 194, alpha), 9))
            painter.drawPath(ribbon)
        painter.setPen(Qt.NoPen)
        for points, color in (([(350,220),(490,100),(550,154),(650,80),(760,152),(835,90),(900,130),(900,220)], "#10323D"),
                              ([(350,220),(530,155),(610,188),(730,127),(805,180),(900,152),(900,220)], "#0C202F")):
            mountain = QPainterPath(QPointF(*points[0]))
            for point in points[1:]:
                mountain.lineTo(QPointF(*point))
            mountain.closeSubpath()
            painter.fillPath(mountain, QColor(color))
        painter.restore()
        rim = QLinearGradient(0, 0, self.width(), self.height())
        rim.setColorAt(0, QColor(56, 189, 248, 160))
        rim.setColorAt(1, QColor(16, 185, 129, 100))
        painter.setPen(QPen(rim, 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 16, 16)
