"""Local, offline walkthrough; demonstrations never submit translation jobs."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMenu, QPushButton,
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
            QFrame#guidePopup, QFrame#guideTrayMenuDemo { background: #0B1627; border: 1px solid #32788B; border-radius: 10px; }
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
        self._counter = self._label('', color='#86D9F7')
        heading.addWidget(self._counter)
        body.addLayout(heading)
        self._title = self._label('', name='guideTitle')
        self._description = self._label('', name='guideDescription')
        body.addWidget(self._title)
        body.addWidget(self._description)
        self._pages = QStackedWidget()
        for builder in (self._selection_page, self._ocr_page, self._replace_page,
                        self._popup_page, self._provider_page, self._help_page):
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
                                        'Sử dụng popup', 'Thêm provider và model',
                                        'Menu khay hệ thống và trợ giúp')):
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
        layout.addWidget(self._label('Screen Translator · Kết quả', color='#9FB8CD'))
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
        explain = self._button('💡', lambda: result.setText(
            'Giải thích: Câu này yêu cầu kiểm tra bản vẽ trước khi bắt đầu sản xuất, '
            'để xác nhận các chi tiết cần thực hiện. Đây là bước kiểm tra trước khi làm.'),
            name='guideExplainDemo')
        explain.setToolTip('Explain — Thử giải thích nội dung được chọn')
        explain.setAccessibleName('Explain — Thử giải thích')
        toolbar.addWidget(explain)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        layout.addWidget(bubble)
        layout.addWidget(self._label('① Bôi đen văn bản       ② Chọn VI / EN / 繁 để dịch, hoặc 💡 để giải thích', color='#BBD5E6'))
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

    def _provider_page(self):
        stage, layout = self._stage()
        layout.setSpacing(10)
        for title, detail in (
            ('① Thêm provider',
             'Bấm + Thêm dưới danh sách bên trái, đặt tên rồi chọn provider vừa tạo. '
             'Trong Kết nối API, chọn Type: openai_compatible; nhập Base URL và API key của dịch vụ. '
             'Endpoint chọn auto hoặc loại dịch vụ hỗ trợ; Explain cần Responses hoặc Chat Completions.'),
            ('② Thêm và chọn model',
             'Trong Models, bấm + Thêm model rồi nhập đúng Model ID từ nhà cung cấp. '
             'Chọn model đó ở Model đang dùng.'),
            ('③ Kiểm tra, lưu và áp dụng',
             'Bấm Test provider / model hiện tại để kiểm tra kết nối (có thể phát sinh phí API). '
             'Chọn đúng Provider đang áp dụng, rồi bấm Lưu & áp dụng.'),
        ):
            layout.addWidget(self._label(title, color='#86D9F7'))
            layout.addWidget(self._label(detail, color='#D8E8F6'))
        status = self._label('Minh họa: chưa thêm model.', name='guideProviderModelDemo', color='#A9B9CC')
        demo = self._button('+ Thêm model (mẫu)', lambda: status.setText(
            'Model mẫu: your-model-id → chọn ở Model đang dùng → Lưu & áp dụng. '
            'Trong app thật, dùng Model ID của dịch vụ bạn đăng ký.'), name='guideAddModelDemo')
        demo.setToolTip('Chỉ minh họa, không thay đổi provider/model thật hoặc gọi API')
        layout.addWidget(demo, alignment=Qt.AlignLeft)
        layout.addWidget(status)
        return stage

    def _help_page(self):
        stage, layout = self._stage()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        layout.addWidget(self._label('Thử menu minh họa bên dưới', color='#9DB2C8'))
        menu_frame = QFrame()
        menu_frame.setObjectName('guideTrayMenuDemo')
        menu_layout = QVBoxLayout(menu_frame)
        menu_layout.setContentsMargins(8, 6, 8, 6)
        menu_layout.setSpacing(0)
        status = self._label('Chọn một mục để xem cách sử dụng.',
                             name='guideTrayStatusDemo', color='#A9B9CC')
        for title, detail, name in (
            ('Mở cửa sổ chính', 'Mở cửa sổ chính để chỉnh cấu hình và phím tắt.', ''),
            ('Hướng dẫn sử dụng', 'Mở lại hướng dẫn này bất cứ lúc nào.', ''),
            ('Dịch sang', '', 'guideTrayLanguageDemo'),
            ('Kiểu dịch    ›', 'Chọn Engineer, Chat hoặc Email theo nội dung cần dịch.', ''),
            ('API / Model    ›', 'Chọn dịch vụ và model đã cấu hình trong app.', ''),
            ('Tốc độ dịch    ›', 'Chọn Cực nhanh, Nhanh hoặc Chuẩn.', ''),
            ('Thoát ứng dụng', 'Chọn mục này trong menu thật để thoát hẳn ứng dụng.', 'guideTrayQuitDemo'),
        ):
            button = self._button(title, lambda checked=False, text=detail: status.setText(text), name=name)
            button.setStyleSheet('''
                QPushButton { text-align: left; padding: 6px 12px; border: 1px solid transparent; background: transparent; }
                QPushButton:hover { background: #174457; }
                QPushButton:focus { border-color: #7DD3FC; }
            ''')
            button.setMinimumHeight(32)
            menu_layout.addWidget(button)
            if name == 'guideTrayLanguageDemo':
                menu = QMenu(button)
                group = QActionGroup(menu)
                group.setExclusive(True)
                for language in ('Tiếng Việt', 'English', '繁體中文 (Traditional Chinese)'):
                    action = menu.addAction(language)
                    action.setCheckable(True)
                    action.setChecked(language == 'Tiếng Việt')
                    group.addAction(action)
                    action.triggered.connect(lambda checked=False, text=language:
                                             status.setText('Ví dụ: đã chọn Dịch sang → ' + text + '.'))
                button.setMenu(menu)
        layout.addWidget(menu_frame)

        taskbar = QFrame()
        taskbar.setObjectName('guidePopup')
        bar = QHBoxLayout(taskbar)
        bar.setContentsMargins(12, 5, 12, 5)
        bar.addWidget(self._label('Khay hệ thống', color='#9DB2C8'), 1)
        bar.addWidget(self._label('⌃', color='#D8E8F6'))
        def toggle_menu(*_):
            menu_frame.setVisible(not menu_frame.isVisible())

        icon = self._button('', toggle_menu, name='guideTrayIconDemo')
        icon.setIcon(asset_icon())
        icon.setIconSize(QSize(26, 26))
        icon.setFixedSize(42, 36)
        icon.setStyleSheet('''
            QPushButton { background: #174457; border: 1px solid #38BDF8; border-radius: 6px; padding: 3px; }
            QPushButton:focus { border: 2px solid #E5F6FA; }
        ''')
        icon.setAccessibleName('Icon Screen Translator: nhấp chuột phải để mở menu minh họa')
        icon.setToolTip('Nhấp chuột phải vào icon app (hoặc bấm để thử)')
        icon.setContextMenuPolicy(Qt.CustomContextMenu)
        icon.customContextMenuRequested.connect(toggle_menu)
        bar.addWidget(icon)
        bar.addWidget(self._label('  ◖  09:41', color='#D8E8F6'))
        layout.addWidget(taskbar)
        layout.addWidget(self._label('Nhấp chuột phải vào icon app cạnh đồng hồ.', color='#D8E8F6'))
        layout.addWidget(status)
        return stage

    def _go(self, index):
        last_page = self._pages.count() - 1
        index = max(0, min(last_page, index))
        hotkeys = self._hotkeys
        pages = (
            ('Bôi đen để dịch hoặc giải thích.',
             'Bấm VI, EN hoặc 繁 để dịch; bấm 💡 Explain để hiểu ý nghĩa của từ, thuật ngữ, code hoặc lỗi. Thử các nút mẫu bên dưới.',
             'Explain cần model AI trong Provider & Model; mặc định trả lời tiếng Việt. Popup chỉ có Sao chép / Ghim / Đóng, không thay thế văn bản. '
             f'Toolbar không xuất hiện? Nhấn {hotkeys.translate_selection.title()} để dịch.'),
            ('Có chữ trong ảnh? Khoanh vùng để dịch.',
             f'Nhấn {hotkeys.region_translate.title()}, kéo chọn vùng chứa chữ rồi thả chuột. App sẽ nhận diện chữ và mở bản dịch.',
             'Dùng cho ảnh, bản vẽ và nội dung không thể bôi đen hoặc sao chép.'),
            ('Viết một ngôn ngữ. Gửi bằng ngôn ngữ khác.',
             f'Bôi đen chữ trong ô nhập, rồi nhấn {hotkeys.translate_and_replace.title()} để thay bằng bản dịch theo ngôn ngữ đích đang chọn.',
             'App chỉ thay văn bản đang chọn. Bạn kiểm tra lại rồi tự bấm Gửi.'),
            ('Giữ bản dịch ngay bên cạnh công việc.',
             'Ghim để giữ cửa sổ, sao chép bản dịch hoặc kéo cạnh và góc cửa sổ để đổi kích thước.',
             'Kéo thanh tiêu đề để di chuyển popup đến vị trí thuận tiện.'),
            ('Thêm provider và model của bạn.',
             'Mở Provider & Model ở sidebar. Làm theo ba bước dưới đây để kết nối dịch vụ AI của bạn.',
             'Các nút + Trial / + Google Free / + Google Cloud / + Microsoft thêm cấu hình có sẵn. '
             'Trial có danh sách model cố định; Google/Microsoft là dịch máy, không hỗ trợ Explain. '
             'Nút mẫu ở trên không gọi API hoặc lưu cấu hình thật.'),
            ('Đổi thiết lập ngay từ icon app.',
             'Nhấp chuột phải vào icon Screen Translator ở góc phải thanh taskbar để mở menu và đổi nhanh thiết lập dịch.',
             'Không thấy icon? Bấm dấu ^ cạnh đồng hồ. Mở lại hướng dẫn bằng mục Hướng dẫn sử dụng trong menu này hoặc sidebar.'),
        )
        title, description, note = pages[index]
        self._pages.setCurrentIndex(index)
        self._title.setText(title)
        self._description.setText(description)
        self._note.setText('ⓘ  ' + note)
        self._counter.setText(f'{index + 1} / {self._pages.count()}')
        self._previous.setEnabled(index > 0)
        self._next.setText('Bắt đầu sử dụng' if index == last_page else 'Tiếp theo →')
        for i, dot in enumerate(self._dots):
            dot.setStyleSheet('padding: 0; border: none; background: transparent; color: ' +
                             ('#38BDF8;' if i == index else '#52647B;'))
        self._scroll.verticalScrollBar().setValue(0)

    def _advance(self):
        if self._pages.currentIndex() == self._pages.count() - 1:
            self.accept()
        else:
            self._go(self._pages.currentIndex() + 1)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Left, Qt.Key_Right):
            self._go(self._pages.currentIndex() + (1 if event.key() == Qt.Key_Right else -1))
            event.accept()
        else:
            super().keyPressEvent(event)
