"""Local, offline walkthrough; demonstrations never submit translation jobs."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from app.config import HotkeySection
from app.ui.theme import asset_icon, dark_titlebar


SOURCE = 'Please check the drawing before production.'
TRANSLATION = 'Vui lòng kiểm tra bản vẽ trước khi sản xuất.'


class UsageGuideDialog(QDialog):
    def __init__(self, hotkeys: HotkeySection, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle('Hướng dẫn sử dụng — Screen Translator')
        self.setWindowIcon(asset_icon())
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumSize(540, 420)
        self.resize(700, 740)
        dark_titlebar(self)
        self.setStyleSheet('''
            QDialog { background: #0B1322; }
            QFrame#guideStage { background: #142237; border: 1px solid #263C54; border-radius: 12px; }
            QFrame#guidePaper { background: #F1F4F8; border: 1px solid #D6E1EC; border-radius: 10px; }
            QFrame#guidePaper QLabel { color: #26354B; }
            QFrame#guidePopup { background: #0B1627; border: 1px solid #32788B; border-radius: 10px; }
            QLabel#guideTitle { font-size: 25px; font-weight: 600; color: #EEF5FF; }
            QLabel#guideDescription { font-size: 14px; color: #B6C5D8; }
            QLabel#guideNote { color: #A9B9CC; font-size: 12px; }
            QLabel#guideTranslation, QLabel#guideOcrResult { font-size: 16px; color: #E5F6FA; }
            QPushButton#guideNext { background: #38BDF8; color: #062433; border: 1px solid #38BDF8; }
            QPushButton#guideNext:hover { background: #74D3FC; }
            QPushButton[guideQuiet="true"] { background: transparent; border: 1px solid transparent; font-weight: 400; }
            QPushButton[guideQuiet="true"]:focus { border-color: #7DD3FC; }
            QPushButton#guidePinDemo { border: none; background: transparent; }
        ''')
        self._hotkeys = hotkeys
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(24, 12, 24, 12)
        logo = QLabel()
        logo.setPixmap(asset_icon().pixmap(28, 28))
        header.addWidget(logo)
        header.addWidget(QLabel('Screen Translator'), 1)
        root.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(28, 12, 28, 16)
        body.setSpacing(12)
        heading = QHBoxLayout()
        heading.addWidget(self._label('Hướng dẫn nhanh', color='#A9B9CC'), 1)
        self._counter = self._label('1 / 5', color='#86D9F7')
        heading.addWidget(self._counter)
        body.addLayout(heading)
        self._title = self._label('', name='guideTitle')
        self._description = self._label('', name='guideDescription')
        body.addWidget(self._title)
        body.addWidget(self._description)
        self._pages = QStackedWidget()
        for builder in (self._selection_page, self._ocr_page, self._replace_page,
                        self._popup_page, self._help_page):
            self._pages.addWidget(builder())
        body.addWidget(self._pages)
        self._note = self._label('', name='guideNote')
        body.addWidget(self._note)
        body.addStretch()
        self._scroll.setWidget(content)
        root.addWidget(self._scroll, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(22, 14, 22, 18)
        skip = self._button('Bỏ qua', self.reject, name='guideSkip')
        skip.setProperty('guideQuiet', True)
        footer.addWidget(skip)
        footer.addStretch()
        self._dots = []
        for index, label in enumerate(('Dịch bôi đen', 'Dịch chữ trong ảnh', 'Dịch và thay thế',
                                        'Sử dụng popup', 'Thiết lập và trợ giúp')):
            dot = self._button('●', lambda checked=False, i=index: self._go(i))
            dot.setFixedSize(24, 30)
            dot.setStyleSheet('padding: 0; border: none; background: transparent;')
            dot.setToolTip(label)
            dot.setAccessibleName(f'Trang {index + 1}: {label}')
            footer.addWidget(dot)
            self._dots.append(dot)
        footer.addStretch()
        self._previous = self._button('Quay lại', lambda: self._go(self._pages.currentIndex() - 1))
        self._previous.setProperty('guideQuiet', True)
        self._next = self._button('Tiếp theo →', self._advance, name='guideNext')
        self._next.setDefault(True)
        footer.addWidget(self._previous)
        footer.addWidget(self._next)
        root.addLayout(footer)
        self._go(0)

    @staticmethod
    def _label(text: str, *, name: str = '', color: str = '') -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        if name:
            label.setObjectName(name)
        if color:
            label.setStyleSheet(f'color: {color};')
        return label

    @staticmethod
    def _button(text, callback, *, name='') -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setCursor(Qt.PointingHandCursor)
        button.setAutoDefault(False)
        button.clicked.connect(callback)
        return button

    def _stage(self):
        stage = QFrame()
        stage.setObjectName('guideStage')
        stage.setMinimumHeight(310)
        layout = QVBoxLayout(stage)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        return stage, layout

    def _paper(self, caption, text, *, name=''):
        paper = QFrame()
        paper.setObjectName('guidePaper')
        layout = QVBoxLayout(paper)
        layout.setContentsMargins(18, 14, 18, 16)
        caption_label = self._label(caption)
        caption_label.setStyleSheet('color: #596B80; font-size: 11px;')
        layout.addWidget(caption_label)
        label = self._label(text, name=name)
        label.setStyleSheet('color: #26354B; font-size: 15px; padding: 8px; background: #BEE8FB; border-radius: 3px;')
        layout.addWidget(label)
        return paper, label

    def _bubble(self, text, *, name=''):
        frame = QFrame()
        frame.setObjectName('guidePopup')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.addWidget(self._label('Screen Translator · Kết quả dịch', color='#9FB8CD'))
        result = self._label(text, name=name)
        layout.addWidget(result)
        return frame, result

    def _selection_page(self):
        stage, layout = self._stage()
        paper, _ = self._paper('Ghi chú công việc.txt', SOURCE)
        layout.addWidget(paper)
        toolbar = QHBoxLayout()
        toolbar.addSpacing(28)
        results = (('VI', 'Vi', TRANSLATION), ('EN', 'En', SOURCE),
                   ('繁', 'Zh', '請在生產前檢查圖紙。'))
        bubble, result = self._bubble(TRANSLATION, name='guideTranslation')
        for text, suffix, translation in results:
            button = self._button(text, lambda checked=False, t=translation: result.setText(t),
                                  name='guideLanguage' + suffix)
            button.setAccessibleName('Dịch thử sang ' + text)
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        layout.addWidget(bubble)
        layout.addWidget(self._label('① Bôi đen văn bản       ② Chọn ngôn ngữ trên toolbar', color='#BBD5E6'))
        return stage

    def _ocr_page(self):
        stage, layout = self._stage()
        paper, selected = self._paper('Bản vẽ · Ghi chú kỹ thuật', 'Tighten all bolts before operation.')
        selected.setStyleSheet('color: #163C3F; font-size: 16px; padding: 14px; background: #D8EEE9; border: 2px solid #109A86;')
        layout.addWidget(paper)
        result = self._label('Siết chặt tất cả bu lông trước khi vận hành.', name='guideOcrResult')
        result.hide()
        demo = self._button('Thử thả chuột để xem kết quả', lambda: result.show(), name='guideOcrDemo')
        layout.addWidget(demo, alignment=Qt.AlignRight)
        layout.addWidget(result)
        layout.addWidget(self._label('① Kéo khung bao quanh chữ       ② Thả chuột để dịch', color='#BBD5E6'))
        return stage

    def _replace_page(self):
        stage, layout = self._stage()
        paper, draft = self._paper('Email mới · Gửi đến: Bộ phận sản xuất', TRANSLATION, name='guideDraft')
        layout.addWidget(paper)
        status = self._label('Bản nháp · Chưa gửi', name='guideDraftStatus', color='#A9B9CC')
        layout.addWidget(status)
        layout.addWidget(self._label('Ví dụ: ngôn ngữ đích đang chọn là Tiếng Anh', color='#BBD5E6'))
        def replace_draft():
            draft.setText(SOURCE)
            status.setText('Đã thay bằng tiếng Anh · Chưa gửi')
            demo.setEnabled(False)

        demo = self._button('Thử dịch và thay thế', replace_draft, name='guideReplaceDemo')
        layout.addWidget(demo, alignment=Qt.AlignRight)
        layout.addWidget(self._label('① Chọn chữ trong ô nhập       ② Thay bằng bản dịch', color='#BBD5E6'))
        return stage

    def _popup_page(self):
        stage, layout = self._stage()
        bubble, _ = self._bubble(TRANSLATION)
        tools = QHBoxLayout()
        tools.addWidget(self._label('Tiếng Anh → Tiếng Việt', color='#9FB8CD'), 1)
        status = self._label('Chưa ghim', color='#A9B9CC')
        pin = self._button('📌', lambda checked: status.setText('Đã ghim cửa sổ' if checked else 'Chưa ghim'),
                           name='guidePinDemo')
        pin.setCheckable(True)
        opacity = QGraphicsOpacityEffect(pin)
        opacity.setOpacity(0.5)
        pin.setGraphicsEffect(opacity)
        pin.toggled.connect(lambda checked: opacity.setOpacity(1.0 if checked else 0.5))
        pin.setToolTip('Thử ghim cửa sổ')
        pin.setAccessibleName('Thử ghim cửa sổ')
        tools.addWidget(pin)
        def copy_translation():
            QApplication.clipboard().setText(TRANSLATION)
            status.setText('Đã sao chép bản dịch mẫu')

        copy = self._button('Sao chép', copy_translation, name='guideCopyDemo')
        tools.addWidget(copy)
        bubble.layout().insertLayout(0, tools)
        bubble.layout().addWidget(self._label(SOURCE, color='#A1B7CA'))
        layout.addWidget(bubble)
        layout.addWidget(self._label('① Ghim cửa sổ    ② Sao chép    ③ Kéo góc để đổi cỡ', color='#BBD5E6'))
        layout.addWidget(status)
        return stage

    def _help_page(self):
        stage, layout = self._stage()
        for title, detail in (('Provider & Model', 'Chọn dịch vụ dịch đang sử dụng'),
                              ('Cài đặt', 'Đổi phím tắt theo thói quen của bạn'),
                              ('Hướng dẫn sử dụng', 'Mở lại từ cuối sidebar hoặc menu khay hệ thống')):
            frame = QFrame()
            frame.setObjectName('guidePopup')
            row = QVBoxLayout(frame)
            row.setContentsMargins(16, 10, 16, 10)
            row.addWidget(self._label(title, color='#D8E8F6'))
            row.addWidget(self._label(detail, color='#9DB2C8'))
            layout.addWidget(frame)
        return stage

    def _go(self, index):
        index = max(0, min(4, index))
        hotkeys = self._hotkeys
        pages = (
            ('Bôi đen. Chọn ngôn ngữ. Đọc bản dịch.',
             'Bôi đen đoạn văn bản, rồi bấm VI, EN hoặc 繁 trên thanh công cụ xuất hiện bên cạnh.',
             f'Toolbar không xuất hiện? Bôi đen rồi nhấn {hotkeys.translate_selection.title()} để dịch.'),
            ('Có chữ trong ảnh? Khoanh vùng để dịch.',
             f'Nhấn {hotkeys.region_translate.title()}, kéo chọn vùng chứa chữ rồi thả chuột. App sẽ nhận diện chữ và mở bản dịch.',
             'Dùng cho ảnh, bản vẽ và nội dung không thể bôi đen hoặc sao chép.'),
            ('Viết một ngôn ngữ. Gửi bằng ngôn ngữ khác.',
             f'Bôi đen chữ trong ô nhập, rồi nhấn {hotkeys.translate_and_replace.title()} để thay bằng bản dịch theo ngôn ngữ đích đang chọn.',
             'App chỉ thay văn bản đang chọn. Bạn kiểm tra lại rồi tự bấm Gửi.'),
            ('Giữ bản dịch ngay bên cạnh công việc.',
             'Ghim để giữ cửa sổ, sao chép bản dịch hoặc kéo cạnh và góc cửa sổ để đổi kích thước.',
             'Kéo thanh tiêu đề để di chuyển popup đến vị trí thuận tiện.'),
            ('Bạn đã sẵn sàng. Bắt đầu dịch thôi.',
             'Bạn có thể đổi dịch vụ, phím tắt và xem lại hướng dẫn bất cứ lúc nào trong app.',
             'Hướng dẫn chỉ tự hiện lần đầu. Mở lại bằng Hướng dẫn sử dụng ở sidebar hoặc khay hệ thống.'),
        )
        title, description, note = pages[index]
        self._pages.setCurrentIndex(index)
        self._title.setText(title)
        self._description.setText(description)
        self._note.setText('ⓘ  ' + note)
        self._counter.setText(f'{index + 1} / 5')
        self._previous.setEnabled(index > 0)
        self._next.setText('Bắt đầu sử dụng' if index == 4 else 'Tiếp theo →')
        for i, dot in enumerate(self._dots):
            dot.setStyleSheet('padding: 0; border: none; background: transparent; color: ' +
                             ('#38BDF8;' if i == index else '#52647B;'))
        self._scroll.verticalScrollBar().setValue(0)

    def _advance(self):
        if self._pages.currentIndex() == 4:
            self.accept()
        else:
            self._go(self._pages.currentIndex() + 1)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Left, Qt.Key_Right):
            self._go(self._pages.currentIndex() + (1 if event.key() == Qt.Key_Right else -1))
            event.accept()
        else:
            super().keyPressEvent(event)
