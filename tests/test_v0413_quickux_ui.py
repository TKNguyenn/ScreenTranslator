from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QMouseEvent
    from PySide6.QtWidgets import QApplication
    from app.config import QuickUxSection
    from app.ui.quick_popup import QuickTranslationPopup
    from app.ui.quick_toolbar import QuickToolbar, clamp_floating_position
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "PySide6 required for widget tests")
class QuickUxWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.popup = QuickTranslationPopup(QuickUxSection())
        self.toolbar = QuickToolbar(QuickUxSection())
        self.addCleanup(self.popup.close)
        self.addCleanup(self.toolbar.close)

    def start(self, job="job"):
        self.popup.start(job, "Original selection", "vi", "Engineer", "Fast",
                         "Local test", "test-model", QPoint(20, 20), True)
        self.app.processEvents()

    def send_mouse(self, widget, kind, local, global_pos, button, buttons):
        event = QMouseEvent(kind, QPointF(local), QPointF(global_pos), button, buttons,
                            Qt.NoModifier)
        QApplication.sendEvent(widget, event)
        self.app.processEvents()

    def test_toolbar_and_popup_paint_opaque_card_background(self):
        for widget in (self.toolbar, self.popup):
            widget.show()
            self.app.processEvents()
            image = QImage(widget.size(), QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            widget.render(image)
            pixel = image.pixelColor(widget.width() // 2, 3)
            self.assertEqual(pixel.alpha(), 255)
            self.assertLess(pixel.red(), 30)
            self.assertLess(pixel.green(), 60)
            self.assertGreater(pixel.blue(), pixel.red())

    def test_drag_header_moves_popup_without_changing_size(self):
        self.start()
        old_position, old_size = self.popup.pos(), self.popup.size()
        local = QPoint(20, 10)
        global_pos = self.popup._headline.mapToGlobal(local)
        self.send_mouse(self.popup._headline, QEvent.MouseButtonPress, local, global_pos,
                        Qt.LeftButton, Qt.LeftButton)
        shift = QPoint(70, 40)
        self.send_mouse(self.popup._headline, QEvent.MouseMove, local, global_pos + shift,
                        Qt.NoButton, Qt.LeftButton)
        self.send_mouse(self.popup._headline, QEvent.MouseButtonRelease, local, global_pos + shift,
                        Qt.LeftButton, Qt.NoButton)
        self.assertEqual(self.popup.pos(), old_position + shift)
        self.assertEqual(self.popup.size(), old_size)

    def test_border_resize_grows_both_dimensions(self):
        self.start()
        old_position, old_size = self.popup.pos(), self.popup.size()
        local = QPoint(self.popup.width() - 3, self.popup.height() - 3)
        global_pos = self.popup.mapToGlobal(local)
        self.send_mouse(self.popup, QEvent.MouseButtonPress, local, global_pos,
                        Qt.LeftButton, Qt.LeftButton)
        shift = QPoint(90, 65)
        self.send_mouse(self.popup, QEvent.MouseMove, local + shift, global_pos + shift,
                        Qt.NoButton, Qt.LeftButton)
        self.send_mouse(self.popup, QEvent.MouseButtonRelease, local + shift, global_pos + shift,
                        Qt.LeftButton, Qt.NoButton)
        self.assertEqual(self.popup.width(), old_size.width() + shift.x())
        self.assertEqual(self.popup.height(), old_size.height() + shift.y())
        self.assertEqual(self.popup.pos(), old_position)

    def test_left_resize_respects_minimum_and_keeps_right_edge(self):
        self.start()
        right = self.popup.geometry().right()
        local = QPoint(2, self.popup.height() // 2)
        global_pos = self.popup.mapToGlobal(local)
        self.send_mouse(self.popup, QEvent.MouseButtonPress, local, global_pos,
                        Qt.LeftButton, Qt.LeftButton)
        self.send_mouse(self.popup, QEvent.MouseMove, local, global_pos + QPoint(1000, 0),
                        Qt.NoButton, Qt.LeftButton)
        self.assertEqual(self.popup.width(), self.popup.minimumWidth())
        self.assertEqual(self.popup.geometry().right(), right)

    def test_size_grip_resizes_popup(self):
        self.start()
        old_size = self.popup.size()
        grip = self.popup._size_grip
        local = grip.rect().center()
        global_pos = grip.mapToGlobal(local)
        self.send_mouse(grip, QEvent.MouseButtonPress, local, global_pos,
                        Qt.LeftButton, Qt.LeftButton)
        shift = QPoint(75, 45)
        self.send_mouse(grip, QEvent.MouseMove, local + shift, global_pos + shift,
                        Qt.NoButton, Qt.LeftButton)
        self.send_mouse(grip, QEvent.MouseButtonRelease, local + shift, global_pos + shift,
                        Qt.LeftButton, Qt.NoButton)
        self.assertEqual(self.popup.width(), old_size.width() + shift.x())
        self.assertEqual(self.popup.height(), old_size.height() + shift.y())

    def test_stream_and_final_keep_user_geometry(self):
        self.start()
        self.popup.setGeometry(80, 90, 590, 480)
        expected = self.popup.geometry()
        self.popup.append_delta("job", "Partial translation")
        self.popup._flush_stream()
        self.popup.finish("job", "Completed translation", False)
        self.app.processEvents()
        self.assertEqual(self.popup.geometry(), expected)
        self.assertTrue(self.popup._copy.isEnabled())
        self.popup.start("second", "Another selection", "en", "Chat", "Fast",
                         "Local test", "test-model", QPoint(5, 5), False)
        self.assertEqual(self.popup.size(), expected.size())

    def test_error_keeps_user_geometry(self):
        self.start()
        self.popup.setGeometry(40, 50, 520, 440)
        expected = self.popup.geometry()
        self.popup.fail("job", "Synthetic error")
        self.assertEqual(self.popup.geometry(), expected)

    def test_closed_popup_not_reopened_by_late_result(self):
        self.start()
        self.popup.force_close()
        self.popup.append_delta("job", "late delta")
        self.popup.finish("job", "late result", False)
        self.assertFalse(self.popup.isVisible())
        self.assertEqual(self.popup._stream_buffer, "")

    def test_pin_and_original_toggle(self):
        self.start()
        self.popup._pin.click()
        self.popup.dismiss_if_unpinned()
        self.assertTrue(self.popup.isVisible())
        self.popup._show_original.click()
        self.assertTrue(self.popup._original_view.isVisible())
        self.popup._show_original.click()
        self.assertFalse(self.popup._original_view.isVisible())

    def test_language_click_still_emits_one_shot_target(self):
        targets = []
        self.toolbar.language_requested.connect(targets.append)
        self.toolbar._buttons["en"].click()
        self.assertEqual(targets, ["en"])

    def test_screen_clamp_supports_negative_monitor_coordinates(self):
        from PySide6.QtCore import QRect
        available = QRect(-1280, -100, 1280, 900)
        position = clamp_floating_position(QPoint(-20, 770), 460, 360, available)
        self.assertTrue(available.contains(position))
        self.assertTrue(available.contains(position + QPoint(459, 359)))


if __name__ == "__main__":
    unittest.main()
