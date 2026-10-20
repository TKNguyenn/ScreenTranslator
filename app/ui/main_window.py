from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QKeySequenceEdit,
)

from app.config import (AppConfig, HotkeySection, ProviderProfile, QuickUxSection,
                        parse_hotkey_section, parse_quick_ux_section,
                        provider_profile_to_dict, provider_profile_from_dict)
from app.prompts import (
    CONTEXT_LABELS,
    PERFORMANCE_LABELS,
    default_prompt_template,
    normalize_prompt_overrides,
    render_prompt_template,
    resolve_prompt_template,
    validate_prompt_template,
)
from app.version import APP_VERSION
from app.ui.theme import asset_icon, dark_titlebar
from app.ui.aurora import AuroraHero, OceanBackdrop
from app.providers.google_translate_addon import GOOGLE_PROVIDER_PRESETS
from app.providers.microsoft_provider import MICROSOFT_PRESET, MICROSOFT_TYPE
from app.trial import TRIAL_TYPE, TRIAL_BASE_URL, TRIAL_MODELS, trial_profile_values, trial_model_label
from app.services.trial_usage import TrialUsageStore


_STREAM_OPTIONS = (
    ("Kế thừa cấu hình chung", None),
    ("Bật streaming", True),
    ("Tắt streaming", False),
)


class MainWindow(QMainWindow):
    """Main desktop manager.

    Startup behavior:
    - shown as a normal desktop window;
    - minimize => hide to System Tray;
    - window X => exit the application;
    - tray double-click => show/restore this window.

    Provider edits are kept in a local working copy until Save & Apply is pressed.
    """

    exit_requested = Signal()
    reload_requested = Signal()
    save_providers_requested = Signal(object, str)
    save_prompt_requested = Signal(str, str, str)
    reset_prompt_requested = Signal(str, str)
    reset_all_prompts_requested = Signal()
    test_provider_requested = Signal(str, object)
    import_providers_requested = Signal(str)
    export_providers_requested = Signal(str)
    region_translate_requested = Signal()
    quick_ux_settings_requested = Signal(object)
    hotkeys_settings_requested = Signal(object)
    check_updates_requested = Signal()

    def __init__(self, app: QApplication, config: AppConfig) -> None:
        super().__init__()
        self._app = app
        self._config = config
        self._working_profiles: dict[str, dict[str, Any]] = {}
        self._active_profile = config.providers.active_profile
        self._current_profile_name: str | None = None
        self._loading_form = False
        self._allow_close = False
        self._prompt_overrides: dict[str, dict[str, str]] = {}
        self._runtime_target_language = config.translation.target_language
        self._runtime_context_preset = config.translation.context_preset
        self._runtime_performance_mode = config.translation.performance_mode

        self.setWindowTitle(f"AI Screen Translator v{APP_VERSION}")
        self.setWindowIcon(asset_icon())
        self.resize(config.ui.main_width, config.ui.main_height)
        self.setMinimumSize(900, 620)
        dark_titlebar(self)

        self._build_ui()
        self.load_config(config, active_profile=config.providers.active_profile)

    # ------------------------------------------------------------------ UI build
    def _build_ui(self) -> None:
        root = OceanBackdrop(self)
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(13, 24, 13, 18)
        side.setSpacing(20)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(asset_icon().pixmap(44, 44))
        logo.setFixedSize(44, 44)
        brand.addWidget(logo)
        brand_text = QVBoxLayout()
        name = QLabel("Screen Translator")
        name.setObjectName("brandTitle")
        tagline = QLabel("AI · OCR · QUICK TRANSLATE")
        tagline.setObjectName("brandSubtitle")
        brand_text.addWidget(name)
        brand_text.addWidget(tagline)
        brand.addLayout(brand_text)
        side.addLayout(brand)
        self._nav = QListWidget()
        self._nav.setObjectName("navList")
        self._nav.setIconSize(QSize(20, 20))
        self._nav.setSelectionMode(QAbstractItemView.SingleSelection)
        self._nav.addItem("Tổng quan")
        self._nav.addItem("Provider & Model")
        self._nav.addItem("Prompt Editor")
        self._nav.addItem("Dịch vùng màn hình")
        self._nav.addItem("Quick UX")
        self._nav.addItem("Dịch PDF (sắp có)")
        self._nav.addItem("Cài đặt")
        for index, icon in enumerate(("tab_overview.svg", "tab_provider.svg", "tab_prompt.svg",
                                      "tab_region_capture.svg", "tab_quick_ux.svg", "tab_pdf.svg",
                                      "tab_settings.svg")):
            self._nav.item(index).setIcon(asset_icon("icons/" + icon))
        self._nav.setCurrentRow(0)
        side.addWidget(self._nav, 1)
        footer = QFrame()
        footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(10, 10, 10, 10)
        footer_layout.setSpacing(8)
        self._check_updates_button = QPushButton("Check for updates")
        self._check_updates_button.setObjectName("checkUpdatesButton")
        self._check_updates_button.setCursor(Qt.PointingHandCursor)
        self._check_updates_button.clicked.connect(self.check_updates_requested.emit)
        self._update_status = QLabel(f"Đang dùng v{APP_VERSION}")
        self._update_status.setObjectName("updateStatus")
        self._update_status.setWordWrap(True)
        self._update_status.setTextFormat(Qt.PlainText)
        self._update_progress = QProgressBar()
        self._update_progress.setRange(0, 100)
        self._update_progress.setTextVisible(False)
        self._update_progress.setFixedHeight(4)
        self._update_progress.hide()
        footer_layout.addWidget(self._check_updates_button)
        footer_layout.addWidget(self._update_status)
        footer_layout.addWidget(self._update_progress)
        side.addWidget(footer)

        self._pages = QStackedWidget()
        for builder in (self._build_overview_page, self._build_provider_page, self._build_prompt_page,
                        self._build_screen_translate_page, self._build_quick_ux_page, self._build_pdf_page,
                        self._build_settings_page):
            page = builder()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(page)
            self._pages.addWidget(scroll)
        self._nav.currentRowChanged.connect(self._pages.setCurrentIndex)

        outer.addWidget(sidebar)
        outer.addWidget(self._pages, 1)

    def set_update_state(self, status: str, button: str = "Check for updates", *,
                         busy: bool = False, progress: int | None = None) -> None:
        self._check_updates_button.setText(button)
        self._check_updates_button.setEnabled(not busy)
        self._update_status.setText(status)
        self._update_progress.setVisible(progress is not None)
        if progress is not None:
            self._update_progress.setValue(progress)

    def _page_container(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setProperty("pageTitle", True)
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setProperty("pageSubtitle", True)
            layout.addWidget(subtitle_label)
        return page, layout

    def _build_overview_page(self) -> QWidget:
        page, layout = self._page_container(
            "AI Screen Translator",
            "Cấu hình app ở đây. Thu nhỏ cửa sổ để app tiếp tục chạy trong System Tray; "
            "nhấn X để thoát hoàn toàn.",
        )

        hero = AuroraHero()
        hero.setMinimumHeight(174)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        eyebrow = QLabel("DỊCH NHANH · ĐỌC DỄ HƠN")
        eyebrow.setStyleSheet("color: #67E8CF; font-size: 11px; font-weight: 600;")
        headline = QLabel("Ngôn ngữ không còn là giới hạn.")
        headline.setStyleSheet("font-size: 25px; font-weight: 700; color: #EFFBFF;")
        headline.setWordWrap(True)
        description = QLabel("Bôi đen văn bản hoặc chọn vùng màn hình.\n"
                             "Bản dịch xuất hiện ngay trong luồng làm việc của bạn.")
        description.setStyleSheet("color: #B5D5E3; font-size: 12px;")
        description.setWordWrap(True)
        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(headline)
        hero_layout.addWidget(description)
        hero_layout.addStretch(1)
        layout.addWidget(hero)
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self._overview_provider = QLabel("-")
        self._overview_model = QLabel("-")
        self._overview_target = QLabel("-")
        self._overview_style = QLabel("-")
        self._overview_performance = QLabel("-")
        self._overview_cache = QLabel("-")
        for caption, value, detail, icon in (
            ("MODEL ĐANG DÙNG", self._overview_model, self._overview_provider, "status_gemini_star.svg"),
            ("CHẾ ĐỘ DỊCH", self._overview_performance, self._overview_style, "status_speed_bars.svg"),
            ("NGÔN NGỮ ĐÍCH", self._overview_target, self._overview_cache, "tab_quick_ux.svg"),
        ):
            card = QFrame()
            card.setProperty("glassCard", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 14, 10, 14)
            card_layout.setSpacing(7)
            top = QHBoxLayout()
            glyph = QLabel()
            glyph.setPixmap(asset_icon("icons/" + icon).pixmap(20, 20))
            top.addWidget(glyph)
            label = QLabel(caption)
            label.setProperty("statCaption", True)
            top.addWidget(label, 1)
            card_layout.addLayout(top)
            value.setProperty("statValue", True)
            value.setWordWrap(True)
            value.setMinimumWidth(0)
            detail.setProperty("statDetail", True)
            detail.setWordWrap(True)
            card_layout.addWidget(value)
            card_layout.addWidget(detail)
            cards.addWidget(card, 1)
        layout.addLayout(cards)
        actions = QGroupBox("Bắt đầu dịch")
        buttons = QGridLayout(actions)
        buttons.setSpacing(10)
        region_btn = QPushButton("Chọn vùng màn hình và dịch")
        region_btn.setProperty("primaryCta", True)
        region_btn.setMinimumHeight(46)
        region_btn.clicked.connect(self.region_translate_requested.emit)
        self._overview_region_button = region_btn
        buttons.addWidget(region_btn, 0, 0, 1, 2)
        quick_btn = QPushButton("Cài đặt Quick Toolbar")
        quick_btn.clicked.connect(lambda: self._nav.setCurrentRow(4))
        provider_btn = QPushButton("Provider & Model")
        provider_btn.clicked.connect(lambda: self._nav.setCurrentRow(1))
        reload_btn = QPushButton("Reload cấu hình")
        reload_btn.clicked.connect(self.reload_requested.emit)
        prompt_btn = QPushButton("Prompt Editor")
        prompt_btn.clicked.connect(lambda: self._nav.setCurrentRow(2))
        for row, left, right in ((1, quick_btn, provider_btn), (2, prompt_btn, reload_btn)):
            buttons.addWidget(left, row, 0)
            buttons.addWidget(right, row, 1)
        layout.addWidget(actions)
        hint = QLabel()
        self._overview_shortcuts = hint
        hint.setProperty("infoBanner", True)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    def _build_provider_page(self) -> QWidget:
        page, layout = self._page_container(
            "Provider & Model",
            "",
        )

        catalog_buttons = QHBoxLayout()
        import_btn = QPushButton("Import providers.json")
        export_btn = QPushButton("Export providers.json")
        import_btn.clicked.connect(self._choose_import_provider_catalog)
        export_btn.clicked.connect(self._choose_export_provider_catalog)
        catalog_buttons.addWidget(import_btn)
        catalog_buttons.addWidget(export_btn)
        trial_btn = QPushButton("+ Trial")
        trial_btn.clicked.connect(self._add_trial_provider)
        catalog_buttons.addWidget(trial_btn)
        for caption, name in (("+ Google Free", "Google Translate Free"),
                              ("+ Google Cloud", "Google Cloud Translate")):
            button = QPushButton(caption)
            button.clicked.connect(lambda checked=False, preset=name: self._add_google_provider(preset))
            catalog_buttons.addWidget(button)
        microsoft_btn = QPushButton("+ Microsoft")
        microsoft_btn.clicked.connect(self._add_microsoft_provider)
        microsoft_buttons = QHBoxLayout()
        microsoft_buttons.addWidget(microsoft_btn)
        microsoft_buttons.addStretch(1)
        catalog_buttons.addStretch(1)
        layout.addLayout(catalog_buttons)
        layout.addLayout(microsoft_buttons)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        # Left provider list ----------------------------------------------------
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        self._provider_list = QListWidget()
        self._provider_list.currentItemChanged.connect(self._on_provider_selection_changed)
        left_layout.addWidget(self._provider_list, 1)

        row = QHBoxLayout()
        add_btn = QPushButton("+ Thêm")
        rename_btn = QPushButton("Đổi tên")
        del_btn = QPushButton("Xóa")
        add_btn.clicked.connect(self._add_provider)
        rename_btn.clicked.connect(self._rename_provider)
        del_btn.clicked.connect(self._delete_provider)
        row.addWidget(add_btn)
        row.addWidget(rename_btn)
        row.addWidget(del_btn)
        left_layout.addLayout(row)
        splitter.addWidget(left)

        # Right editor ---------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(8, 0, 8, 0)

        connection = QGroupBox("Kết nối API")
        connection_form = QFormLayout(connection)
        self._connection_group = connection
        self._connection_form = connection_form
        self._profile_name_label = QLabel("-")
        self._type_combo = QComboBox()
        self._type_combo.addItems(["openai_compatible", "google_translate_web", "google_cloud_translate", "microsoft_translator", "mock"])
        self._type_combo.currentTextChanged.connect(self._on_provider_type_changed)
        self._base_url_edit = QLineEdit()
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_box = QWidget()
        self._api_key_box = api_key_box
        api_key_layout = QHBoxLayout(api_key_box)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.addWidget(self._api_key_edit, 1)
        self._show_key = QCheckBox("Hiện")
        self._show_key.toggled.connect(
            lambda checked: self._api_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_key_layout.addWidget(self._show_key)
        self._api_key_env_edit = QLineEdit()
        self._region_edit = QLineEdit()
        self._region_edit.setPlaceholderText("southeastasia; để trống nếu resource global")
        self._allow_no_key = QCheckBox("Cho phép không có API key (gateway local)")
        self._endpoint_combo = QComboBox()
        self._endpoint_combo.addItems(["auto", "responses", "chat_completions", "completions"])
        self._timeout_spin = QDoubleSpinBox()
        self._timeout_spin.setRange(1.0, 600.0)
        self._timeout_spin.setDecimals(1)
        self._timeout_spin.setSuffix(" s")
        self._connect_timeout_spin = QDoubleSpinBox()
        self._connect_timeout_spin.setRange(1.0, 120.0)
        self._connect_timeout_spin.setDecimals(1)
        self._connect_timeout_spin.setSuffix(" s")
        self._verify_ssl = QCheckBox("Verify SSL")

        connection_form.addRow("Tên profile:", self._profile_name_label)
        connection_form.addRow("Type:", self._type_combo)
        connection_form.addRow("Base URL:", self._base_url_edit)
        connection_form.addRow("API key:", api_key_box)
        connection_form.addRow("Region:", self._region_edit)
        connection_form.addRow("API key env (tùy chọn):", self._api_key_env_edit)
        connection_form.addRow("", self._allow_no_key)
        connection_form.addRow("Endpoint:", self._endpoint_combo)
        connection_form.addRow("Read timeout:", self._timeout_spin)
        connection_form.addRow("Connect timeout:", self._connect_timeout_spin)
        connection_form.addRow("", self._verify_ssl)
        editor_layout.addWidget(connection)
        self._google_provider_note = QLabel()
        self._google_provider_note.setWordWrap(True)
        self._google_provider_note.setProperty("infoBanner", True)
        editor_layout.addWidget(self._google_provider_note)

        models_group = QGroupBox("Models")
        self._models_group = models_group
        models_layout = QVBoxLayout(models_group)
        active_row = QHBoxLayout()
        self._active_model_label = QLabel("Model đang dùng:")
        active_row.addWidget(self._active_model_label)
        self._active_model_combo = QComboBox()
        active_row.addWidget(self._active_model_combo, 1)
        models_layout.addLayout(active_row)
        self._models_list = QListWidget()
        models_layout.addWidget(self._models_list)
        model_buttons = QHBoxLayout()
        add_model_btn = QPushButton("+ Thêm model")
        remove_model_btn = QPushButton("Xóa model")
        self._model_buttons = (add_model_btn, remove_model_btn)
        add_model_btn.clicked.connect(self._add_model)
        remove_model_btn.clicked.connect(self._remove_model)
        model_buttons.addWidget(add_model_btn)
        model_buttons.addWidget(remove_model_btn)
        model_buttons.addStretch(1)
        models_layout.addLayout(model_buttons)
        editor_layout.addWidget(models_group)

        stream_group = QGroupBox("Streaming override theo profile")
        self._stream_group = stream_group
        stream_form = QFormLayout(stream_group)
        self._stream_ultra = self._make_stream_combo()
        self._stream_fast = self._make_stream_combo()
        self._stream_quality = self._make_stream_combo()
        stream_form.addRow("Ultra Fast:", self._stream_ultra)
        stream_form.addRow("Fast:", self._stream_fast)
        stream_form.addRow("Quality:", self._stream_quality)
        editor_layout.addWidget(stream_group)

        self._trial_group = QWidget()
        trial_layout = QVBoxLayout(self._trial_group)
        trial_layout.setContentsMargins(0, 0, 0, 0)
        trial_layout.setSpacing(10)
        trial_layout.addWidget(QLabel("Hạn mức sử dụng"))
        self._trial_quota = QProgressBar()
        self._trial_quota.setObjectName("trialQuota")
        self._trial_quota.setRange(0, 100)
        self._trial_quota.setValue(100)
        self._trial_quota.setTextVisible(False)
        self._trial_quota.setFixedHeight(10)
        self._trial_quota.setAccessibleName("Hạn mức sử dụng")
        self._trial_quota.setAccessibleDescription("Hạn mức ước lượng, không chính xác")
        trial_layout.addWidget(self._trial_quota)
        self._trial_quota_status = QLabel("Hạn mức ước lượng, không chính xác. Chi phí thực tế tùy độ dài văn bản.")
        self._trial_quota_status.setWordWrap(True)
        self._trial_quota_status.setObjectName("trialQuotaStatus")
        trial_layout.addWidget(self._trial_quota_status)
        trial_hint = QLabel("Liên hệ người phát triển để nhận API key Trial riêng.")
        trial_hint.setWordWrap(True)
        trial_layout.addWidget(trial_hint)
        editor_layout.addWidget(self._trial_group)
        self._microsoft_usage_group = QGroupBox("Microsoft — sử dụng trên máy này")
        usage_layout = QVBoxLayout(self._microsoft_usage_group)
        self._microsoft_usage_status = QLabel()
        self._microsoft_usage_status.setWordWrap(True)
        usage_layout.addWidget(self._microsoft_usage_status)
        usage_note = QLabel("Mốc tham khảo F0: 2.000.000 ký tự/tháng. Chỉ tính request thành công của app trên máy này; "
                           "Thống kê cục bộ dùng chung các profile Microsoft trên máy này; tháng theo giờ Việt Nam.")
        usage_note.setWordWrap(True)
        usage_layout.addWidget(usage_note)
        editor_layout.addWidget(self._microsoft_usage_group)
        self._api_key_edit.textChanged.connect(self.refresh_trial_quota)
        self._trial_quota_timer = QTimer(self)
        self._trial_quota_timer.setInterval(60_000)
        self._trial_quota_timer.timeout.connect(
            lambda: self.refresh_trial_quota() if self._trial_group.isVisible() else None)
        self._trial_quota_timer.start()
        self._trial_quota_timer.timeout.connect(self.refresh_microsoft_usage)

        test_group = QGroupBox("Kiểm tra provider/model")
        test_layout = QVBoxLayout(test_group)
        test_hint = QLabel(
            "Gửi một request rất ngắn để kiểm tra Base URL, API key, endpoint và model hiện đang chọn. "
            "Request test có thể phát sinh chi phí nhỏ tùy provider."
        )
        test_hint.setWordWrap(True)
        self._provider_test_hint = test_hint
        self._provider_test_button = QPushButton("Test provider / model hiện tại")
        self._provider_test_button.clicked.connect(self._test_current_provider)
        self._provider_test_status = QLabel("Chưa test")
        self._provider_test_status.setWordWrap(True)
        test_layout.addWidget(test_hint)
        test_layout.addWidget(self._provider_test_button)
        test_layout.addWidget(self._provider_test_status)
        editor_layout.addWidget(test_group)

        editor_layout.addStretch(1)
        scroll.setWidget(editor)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 700])

        bottom = QVBoxLayout()
        self._active_profile_combo = QComboBox()
        active_row = QHBoxLayout()
        active_row.addWidget(QLabel("Provider đang áp dụng:"))
        active_row.addWidget(self._active_profile_combo, 1)
        bottom.addLayout(active_row)
        reload_btn = QPushButton("Bỏ thay đổi / Reload file")
        reload_btn.clicked.connect(self.reload_requested.emit)
        save_btn = QPushButton("Lưu & áp dụng")
        save_btn.setProperty("primaryCta", True)
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_apply)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(reload_btn)
        buttons.addWidget(save_btn)
        bottom.addLayout(buttons)
        layout.addLayout(bottom)
        return page

    def _build_prompt_page(self) -> QWidget:
        page, layout = self._page_container(
            "Prompt Editor",
            "Tùy chỉnh prompt độc lập theo 3 tốc độ và 3 kiểu dịch. Mặc định app dùng prompt gốc; "
            "chỉ khi bấm Lưu tùy chỉnh thì prompts.json mới lưu override cho đúng cặp đang chọn.",
        )
        self._google_prompt_note = QLabel("Google dịch trực tiếp, không dùng prompt / Engineer / Chat / Email hay tốc độ AI. "
                                          "Các prompt đã lưu được giữ lại cho provider AI.")
        self._google_prompt_note.setWordWrap(True)
        self._google_prompt_note.setProperty("infoBanner", True)
        self._google_prompt_note.hide()
        layout.addWidget(self._google_prompt_note)

        selector = QGroupBox("Chọn prompt cần chỉnh")
        selector_form = QFormLayout(selector)
        self._prompt_mode_combo = QComboBox()
        for mode in ("ultra_fast", "fast", "quality"):
            self._prompt_mode_combo.addItem(PERFORMANCE_LABELS[mode], mode)
        self._prompt_style_combo = QComboBox()
        for style in ("engineering", "chat", "email"):
            self._prompt_style_combo.addItem(CONTEXT_LABELS[style], style)
        self._prompt_status = QLabel("Mặc định")
        self._prompt_status.setStyleSheet("font-weight: 600;")
        selector_form.addRow("Tốc độ:", self._prompt_mode_combo)
        selector_form.addRow("Kiểu dịch:", self._prompt_style_combo)
        selector_form.addRow("Trạng thái:", self._prompt_status)
        layout.addWidget(selector)

        help_label = QLabel(
            "Placeholder hỗ trợ: {source_language}, {target_language}, {style}, "
            "{engineering_terms}, {glossary}. {glossary} hiện để trống và được dành sẵn cho Glossary ở bản sau."
        )
        help_label.setWordWrap(True)
        help_label.setProperty("infoBanner", True)
        layout.addWidget(help_label)

        editor_group = QGroupBox("Prompt template")
        editor_layout = QVBoxLayout(editor_group)
        self._prompt_editor = QPlainTextEdit()
        self._prompt_editor.setPlaceholderText("Prompt template...")
        self._prompt_editor.setMinimumHeight(210)
        editor_layout.addWidget(self._prompt_editor)
        buttons = QGridLayout()
        save_btn = QPushButton("Lưu tùy chỉnh")
        save_btn.setProperty("primaryCta", True)
        reset_btn = QPushButton("Reset cặp này về mặc định")
        reset_all_btn = QPushButton("Reset toàn bộ")
        default_btn = QPushButton("Nạp lại prompt mặc định vào editor")
        save_btn.clicked.connect(self._save_prompt_editor)
        reset_btn.clicked.connect(self._reset_prompt_editor)
        reset_all_btn.clicked.connect(self._reset_all_prompts)
        default_btn.clicked.connect(self._load_default_prompt_into_editor)
        buttons.addWidget(save_btn, 0, 0)
        buttons.addWidget(reset_btn, 0, 1)
        buttons.addWidget(reset_all_btn, 1, 0, 1, 2)
        editor_layout.addLayout(buttons)
        editor_layout.addWidget(default_btn)
        layout.addWidget(editor_group)

        preview_group = QGroupBox("Preview prompt thực tế")
        preview_layout = QVBoxLayout(preview_group)
        preview_note = QLabel(
            "Preview dùng source=Auto, target hiện tại của config và đúng style đang chọn. "
            "Bản dịch thật sẽ render lại target/source theo request lúc đó."
        )
        preview_note.setWordWrap(True)
        self._prompt_preview = QPlainTextEdit()
        self._prompt_preview.setReadOnly(True)
        self._prompt_preview.setMinimumHeight(150)
        preview_btn = QPushButton("Cập nhật Preview")
        preview_btn.clicked.connect(self._refresh_prompt_preview)
        preview_layout.addWidget(preview_note)
        preview_layout.addWidget(self._prompt_preview)
        preview_layout.addWidget(preview_btn)
        layout.addWidget(preview_group)
        layout.addStretch(1)

        self._prompt_mode_combo.currentIndexChanged.connect(self._load_selected_prompt)
        self._prompt_style_combo.currentIndexChanged.connect(self._load_selected_prompt)
        self._prompt_sections = (selector, editor_group, preview_group)
        return page

    def _build_screen_translate_page(self) -> QWidget:
        page, layout = self._page_container(
            "Dịch vùng màn hình",
            "V0.4.0: kéo chọn một vùng trên màn hình, OCR chạy local rồi gửi phần chữ nhận dạng "
            "qua TranslationWorker hiện tại. Không upload ảnh lên provider dịch.",
        )

        status = QGroupBox("Region Translate")
        form = QFormLayout(status)
        self._region_hotkey_label = QLabel("-")
        self._region_ocr_engine_label = QLabel("-")
        self._region_ocr_confidence_label = QLabel("-")
        self._region_scope_label = QLabel("Một monitor/lần")
        form.addRow("Hotkey:", self._region_hotkey_label)
        form.addRow("OCR engine:", self._region_ocr_engine_label)
        form.addRow("Min confidence:", self._region_ocr_confidence_label)
        form.addRow("Phạm vi capture:", self._region_scope_label)
        layout.addWidget(status)

        workflow = QLabel(
            "Luồng xử lý: chọn vùng → chụp PNG local → RapidOCR local → text → AI translation → popup. "
            "Ảnh chỉ đi vào OCR local; provider AI chỉ nhận text OCR. Lần OCR đầu tiên có thể chậm hơn "
            "vì model OCR được khởi tạo lazy."
        )
        workflow.setWordWrap(True)
        workflow.setProperty("infoBanner", True)
        layout.addWidget(workflow)

        usage = QLabel(
            "Cách dùng:\n"
            "1. Đưa chuột sang monitor có vùng chữ cần dịch.\n"
            "2. Bấm nút bên dưới hoặc hotkey Region Translate.\n"
            "3. Kéo chuột trái để khoanh vùng; Esc/chuột phải để hủy.\n"
            "4. Popup sẽ hiện OCR text rồi bản dịch.\n\n"
            "V0.4.0 hỗ trợ mọi monitor nhưng một vùng chọn không kéo xuyên qua hai monitor. "
            "Giới hạn này giúp mapping DPI ổn định trước khi làm Live Translate."
        )
        usage.setWordWrap(True)
        layout.addWidget(usage)

        self._region_translate_button = QPushButton("Chọn vùng và dịch")
        self._region_translate_button.setProperty("primaryCta", True)
        self._region_translate_button.setMinimumHeight(44)
        self._region_translate_button.clicked.connect(self.region_translate_requested.emit)
        layout.addWidget(self._region_translate_button)

        live = QGroupBox("Live Screen Translate")
        live_layout = QVBoxLayout(live)
        live_note = QLabel(
            "Chưa bật trong V0.4.0. Region Translate là nền tảng capture + OCR được dùng lại "
            "cho Live Translate ở V0.4.5."
        )
        live_note.setWordWrap(True)
        live_layout.addWidget(live_note)
        live_btn = QPushButton("Live Translate - Coming in V0.4.5")
        live_btn.setEnabled(False)
        live_layout.addWidget(live_btn)
        layout.addWidget(live)
        layout.addStretch(1)
        return page

    def _build_pdf_page(self) -> QWidget:
        page, layout = self._page_container(
            "Dịch PDF",
            "Trang này được giữ sẵn cho giai đoạn tiếp theo. V0.4.0 chưa triển khai chức năng PDF.",
        )
        card = QFrame()
        card.setProperty("glassCard", True)
        card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        label = QLabel(
            "Hướng phát triển dự kiến:\n\n"
            "• Mở PDF trong cửa sổ chính\n"
            "• Dịch từng trang / toàn tài liệu\n"
            "• Giữ bố cục gốc hoặc hiển thị song ngữ\n"
            "• OCR fallback cho PDF scan\n"
            "• Tái sử dụng provider/model/cache hiện tại"
        )
        label.setWordWrap(True)
        card_layout.addWidget(label)
        coming = QPushButton("Dịch PDF - Coming soon")
        coming.setEnabled(False)
        card_layout.addWidget(coming)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_quick_ux_page(self) -> QWidget:
        page, layout = self._page_container(
            "Quick UX — Floating Toolbar",
            "Chọn chữ bằng chuột trong ứng dụng khác để hiện thanh VI / EN / 繁. "
            "Việc bôi đen KHÔNG tự gọi API; chỉ dịch khi bạn bấm một nút trên thanh. "
            "Ứng dụng không hỗ trợ UI Automation vẫn có thể dùng Alt+T / Alt+Shift+T.",
        )
        group = QGroupBox("Thiết lập Quick Toolbar")
        form = QFormLayout(group)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self._quick_auto_show = QCheckBox("Hiện toolbar sau khi bôi đen")
        self._quick_auto_show.setToolTip("Mặc định bật. Chỉ phát hiện vùng chọn, không tự gọi API.")
        form.addRow("Tự động:", self._quick_auto_show)
        self._quick_delay = QSpinBox()
        self._quick_delay.setRange(150, 600)
        self._quick_delay.setSingleStep(50)
        self._quick_delay.setSuffix(" ms")
        form.addRow("Đợi sau khi chọn:", self._quick_delay)
        self._quick_timeout = QSpinBox()
        self._quick_timeout.setRange(2, 20)
        self._quick_timeout.setSuffix(" giây")
        form.addRow("Tự ẩn toolbar:", self._quick_timeout)
        languages = QVBoxLayout()
        self._quick_language_boxes: dict[str, QCheckBox] = {}
        for code, label in (("vi", "VI - Tiếng Việt"), ("en", "EN - English"), ("zh-Hant", "繁 - Phồn thể")):
            chk = QCheckBox(label)
            self._quick_language_boxes[code] = chk
            languages.addWidget(chk)
        languages.addStretch(1)
        language_widget = QWidget()
        language_widget.setLayout(languages)
        form.addRow("Nút ngôn ngữ:", language_widget)
        self._quick_dismiss = QCheckBox("Đóng khi click ngoài, trừ khi đã ghim")
        form.addRow("Popup:", self._quick_dismiss)
        self._quick_max_chars = QSpinBox()
        self._quick_max_chars.setRange(200, 20000)
        self._quick_max_chars.setSingleStep(200)
        form.addRow("Giới hạn chữ auto-detect:", self._quick_max_chars)
        layout.addWidget(group)

        privacy = QLabel(
            "Riêng tư: phát hiện selection bằng Windows UI Automation, không thăm dò clipboard "
            "và không gửi API cho tới khi bấm nút. Bỏ qua password fields và vùng không hỗ trợ "
            "TextPattern. Dịch và thay thế sẽ kiểm tra lại vùng chọn trước khi dán."
        )
        privacy.setWordWrap(True)
        privacy.setProperty("infoBanner", True)
        layout.addWidget(privacy)
        action = QHBoxLayout()
        save = QPushButton("Lưu & áp dụng Quick UX")
        save.setProperty("primaryCta", True)
        save.clicked.connect(self._save_quick_ux)
        reset = QPushButton("Khôi phục mặc định")
        reset.clicked.connect(self._reset_quick_ux)
        action.addWidget(save)
        action.addWidget(reset)
        action.addStretch(1)
        layout.addLayout(action)
        self._quick_status = QLabel("Mặc định ON. Mất hỗ trợ UIA ở app nào thì dùng hotkey thông thường.")
        self._quick_status.setWordWrap(True)
        layout.addWidget(self._quick_status)
        layout.addStretch(1)
        return page

    def _build_settings_page(self) -> QWidget:
        page, layout = self._page_container(
            "Cài đặt",
            "Thay đổi các phím tắt toàn app. Bấm vào từng ô rồi nhấn tổ hợp phím muốn dùng.",
        )
        group = QGroupBox("Hotkey")
        form = QFormLayout(group)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self._hotkey_edits: dict[str, QKeySequenceEdit] = {}
        for key, label in (
            ("translate_selection", "Dịch bôi đen"),
            ("translate_and_replace", "Dịch và thay thế"),
            ("live_toggle", "Bật/tắt Live Translate"),
            ("region_translate", "Dịch vùng màn hình"),
            ("target_vi", "Chuyển sang Tiếng Việt"),
            ("target_en", "Chuyển sang English"),
            ("target_zh_hant", "Chuyển sang 繁體中文"),
        ):
            edit = QKeySequenceEdit()
            edit.setMaximumSequenceLength(1)
            edit.setToolTip("Nhấn một tổ hợp phím, ví dụ Alt+T")
            self._hotkey_edits[key] = edit
            form.addRow(label + ":", edit)
        self._hotkey_delay = QSpinBox()
        self._hotkey_delay.setRange(0, 1000)
        self._hotkey_delay.setSingleStep(10)
        self._hotkey_delay.setSuffix(" ms")
        form.addRow("Độ trễ nhả phím:", self._hotkey_delay)
        self._hotkey_suppress = QCheckBox("Chặn tổ hợp hotkey khỏi ứng dụng đang dùng")
        form.addRow("Hành vi:", self._hotkey_suppress)
        layout.addWidget(group)

        note = QLabel(
            "Hotkey được đăng ký toàn hệ thống. Mỗi hotkey phải khác nhau; nếu tổ hợp đã bị ứng dụng "
            "khác chiếm, app sẽ báo lỗi khi áp dụng."
        )
        note.setWordWrap(True)
        note.setProperty("infoBanner", True)
        layout.addWidget(note)
        actions = QHBoxLayout()
        save = QPushButton("Lưu & áp dụng hotkey")
        save.setProperty("primaryCta", True)
        save.clicked.connect(self._save_hotkeys)
        reset = QPushButton("Khôi phục mặc định")
        reset.clicked.connect(self._reset_hotkeys)
        actions.addWidget(save)
        actions.addWidget(reset)
        actions.addStretch(1)
        layout.addLayout(actions)
        self._hotkey_status = QLabel("")
        self._hotkey_status.setWordWrap(True)
        layout.addWidget(self._hotkey_status)
        layout.addStretch(1)
        return page

    @staticmethod
    def _key_sequence_text(edit: QKeySequenceEdit) -> str:
        return edit.keySequence().toString(QKeySequence.PortableText).strip().lower().replace(" ", "")

    def set_hotkey_settings(self, config: HotkeySection) -> None:
        for key, edit in self._hotkey_edits.items():
            edit.setKeySequence(QKeySequence(getattr(config, key)))
        self._hotkey_delay.setValue(config.release_delay_ms)
        self._hotkey_suppress.setChecked(config.suppress_hotkeys)
        self._hotkey_status.setText("Hotkey hiện tại đã được nạp từ config.json.")

    def _hotkey_form_values(self) -> dict[str, Any]:
        values = {key: self._key_sequence_text(edit) for key, edit in self._hotkey_edits.items()}
        values["release_delay_ms"] = self._hotkey_delay.value()
        values["suppress_hotkeys"] = self._hotkey_suppress.isChecked()
        return values

    def _save_hotkeys(self) -> None:
        try:
            parsed = parse_hotkey_section(self._hotkey_form_values())
        except ValueError as exc:
            QMessageBox.warning(self, "Hotkey", str(exc))
            return
        self.hotkeys_settings_requested.emit(parsed.as_json())

    def _reset_hotkeys(self) -> None:
        config = HotkeySection()
        self.set_hotkey_settings(config)
        self.hotkeys_settings_requested.emit(config.as_json())

    def show_quick_ux_settings(self) -> None:
        self.show_from_tray()
        self._nav.setCurrentRow(4)

    def set_quick_ux_settings(self, config: QuickUxSection) -> None:
        self._quick_auto_show.setChecked(config.auto_show_toolbar)
        self._quick_delay.setValue(config.selection_delay_ms)
        self._quick_timeout.setValue(config.toolbar_timeout_ms // 1000)
        self._quick_dismiss.setChecked(config.dismiss_popup_on_blur)
        self._quick_max_chars.setValue(config.max_selection_chars)
        for code, checkbox in self._quick_language_boxes.items():
            checkbox.setChecked(code in config.languages)
        self._quick_status.setText("Thiết lập hiện tại: " + ("Toolbar ON" if config.auto_show_toolbar else "Toolbar OFF"))

    def _save_quick_ux(self) -> None:
        values = {
            "auto_show_toolbar": self._quick_auto_show.isChecked(),
            "selection_delay_ms": self._quick_delay.value(),
            "toolbar_timeout_ms": self._quick_timeout.value() * 1000,
            "dismiss_popup_on_blur": self._quick_dismiss.isChecked(),
            "max_selection_chars": self._quick_max_chars.value(),
            "languages": [code for code, box in self._quick_language_boxes.items() if box.isChecked()],
        }
        try:
            parsed = parse_quick_ux_section(values)
        except ValueError as exc:
            QMessageBox.warning(self, "Quick UX", str(exc))
            return
        self.quick_ux_settings_requested.emit(parsed.as_json())

    def _reset_quick_ux(self) -> None:
        config = QuickUxSection()
        self.set_quick_ux_settings(config)
        self.quick_ux_settings_requested.emit(config.as_json())

    @staticmethod
    def _make_stream_combo() -> QComboBox:
        combo = QComboBox()
        for label, value in _STREAM_OPTIONS:
            combo.addItem(label, value)
        return combo

    # ------------------------------------------------------------- config state
    def load_config(
        self,
        config: AppConfig,
        active_profile: str,
        target_language: str | None = None,
        context_preset: str | None = None,
        performance_mode: str | None = None,
        cache_enabled: bool | None = None,
        prompt_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._config = config
        self._prompt_overrides = normalize_prompt_overrides(prompt_overrides)
        hotkeys = config.hotkeys
        self._overview_shortcuts.setText(
            f"{hotkeys.translate_selection.upper()}  Dịch bôi đen   ·   "
            f"{hotkeys.translate_and_replace.upper()}  Dịch và thay thế   ·   "
            f"{hotkeys.region_translate.upper()}  Chọn vùng"
        )
        self._working_profiles = {
            name: provider_profile_to_dict(profile)
            for name, profile in config.providers.profiles.items()
        }
        self._active_profile = (
            active_profile if active_profile in self._working_profiles else config.providers.active_profile
        )
        if self._active_profile not in self._working_profiles and self._working_profiles:
            self._active_profile = next(iter(self._working_profiles))

        self._rebuild_provider_list(select=self._active_profile)
        self._rebuild_active_profile_combo()
        self.update_runtime_state(
            active_profile=self._active_profile,
            profiles=config.providers.profiles,
            target_language=target_language or config.translation.target_language,
            context_preset=context_preset or config.translation.context_preset,
            performance_mode=performance_mode or config.translation.performance_mode,
            cache_enabled=config.translation.cache_enabled if cache_enabled is None else cache_enabled,
        )
        if hasattr(self, "_prompt_mode_combo"):
            self._load_selected_prompt()
        self._refresh_region_config_summary()
        self.set_quick_ux_settings(config.quick_ux)
        self.set_hotkey_settings(config.hotkeys)

    def update_runtime_state(
        self,
        active_profile: str,
        profiles: Mapping[str, ProviderProfile],
        target_language: str,
        context_preset: str,
        performance_mode: str,
        cache_enabled: bool,
    ) -> None:
        profile = profiles.get(active_profile)
        self._runtime_target_language = target_language
        self._runtime_context_preset = context_preset
        self._runtime_performance_mode = performance_mode
        self._overview_provider.setText(active_profile)
        self._overview_model.setText(profile.model if profile else "<invalid>")
        languages = {"vi": "Tiếng Việt", "en": "English", "zh-Hant": "繁體中文"}
        self._overview_target.setText(languages.get(target_language, target_language))
        self._overview_style.setText(CONTEXT_LABELS.get(context_preset, context_preset))
        self._overview_performance.setText(PERFORMANCE_LABELS.get(performance_mode, performance_mode))
        self._overview_cache.setText("Cache đang bật" if cache_enabled else "Cache đang tắt")
        google = profile is not None and profile.type in {"google_translate_web", "google_cloud_translate", "microsoft_translator"}
        self._google_prompt_note.setText("Google / Microsoft dịch trực tiếp, không dùng prompt, style hay tốc độ AI.")
        if google:
            self._overview_performance.setText("Dịch trực tiếp")
            self._overview_style.setText("Không dùng style / prompt AI")
        self._google_prompt_note.setVisible(google)
        for section in self._prompt_sections:
            section.setEnabled(not google)
        idx = self._active_profile_combo.findText(active_profile)
        if idx >= 0:
            self._active_profile_combo.setCurrentIndex(idx)
        if hasattr(self, "_prompt_preview"):
            self._refresh_prompt_preview()

    def _rebuild_provider_list(self, select: str | None = None) -> None:
        self._loading_form = True
        try:
            self._provider_list.clear()
            for name in self._working_profiles:
                self._provider_list.addItem(QListWidgetItem(name))
            if select:
                items = self._provider_list.findItems(select, Qt.MatchExactly)
                if items:
                    self._provider_list.setCurrentItem(items[0])
                elif self._provider_list.count():
                    self._provider_list.setCurrentRow(0)
            elif self._provider_list.count():
                self._provider_list.setCurrentRow(0)
        finally:
            self._loading_form = False
        item = self._provider_list.currentItem()
        if item:
            self._load_provider_form(item.text())

    def _rebuild_active_profile_combo(self) -> None:
        current = self._active_profile_combo.currentText() if self._active_profile_combo.count() else self._active_profile
        self._active_profile_combo.blockSignals(True)
        self._active_profile_combo.clear()
        self._active_profile_combo.addItems(list(self._working_profiles))
        target = self._active_profile if self._active_profile in self._working_profiles else current
        idx = self._active_profile_combo.findText(target)
        if idx >= 0:
            self._active_profile_combo.setCurrentIndex(idx)
        self._active_profile_combo.blockSignals(False)

    # -------------------------------------------------------------- form events
    def _on_provider_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._loading_form:
            return
        if previous is not None and self._current_profile_name == previous.text():
            self._commit_current_form()
        if current is not None:
            self._load_provider_form(current.text())

    def _load_provider_form(self, name: str) -> None:
        data = self._working_profiles.get(name)
        if data is None:
            return
        self._loading_form = True
        try:
            self._current_profile_name = name
            self._profile_name_label.setText(name)
            self._set_combo_text(self._type_combo, str(data.get("type", "openai_compatible")))
            self._base_url_edit.setText(str(data.get("base_url", "")))
            self._api_key_edit.setText(str(data.get("api_key", "")))
            self._api_key_env_edit.setText(str(data.get("api_key_env", "")))
            self._region_edit.setText(str(data.get("region", "southeastasia")))
            self._allow_no_key.setChecked(bool(data.get("allow_no_api_key", False)))
            self._set_combo_text(self._endpoint_combo, str(data.get("endpoint_mode", "auto")))
            self._timeout_spin.setValue(float(data.get("timeout_s", 45.0)))
            self._connect_timeout_spin.setValue(float(data.get("connect_timeout_s", 10.0)))
            self._verify_ssl.setChecked(bool(data.get("verify_ssl", True)))

            models = self._normalized_models(data)
            self._models_list.clear()
            self._models_list.addItems(models)
            self._active_model_combo.clear()
            for model in models:
                self._active_model_combo.addItem(trial_model_label(model) if data.get("type") == TRIAL_TYPE else model, model)
            active_model = str(data.get("model", ""))
            idx = self._active_model_combo.findData(active_model)
            if idx >= 0:
                self._active_model_combo.setCurrentIndex(idx)

            override = data.get("streaming_override", {})
            if not isinstance(override, dict):
                override = {}
            self._set_stream_combo(self._stream_ultra, override.get("ultra_fast"))
            self._set_stream_combo(self._stream_fast, override.get("fast"))
            self._set_stream_combo(self._stream_quality, override.get("quality"))
            self._set_provider_form_enabled()
        finally:
            self._loading_form = False


    def _commit_current_form(self) -> None:
        if self._loading_form or not self._current_profile_name:
            return
        name = self._current_profile_name
        data = deepcopy(self._working_profiles.get(name, {}))
        provider_type = self._type_combo.currentText().strip()
        data["type"] = provider_type
        data["base_url"] = self._base_url_edit.text().strip()
        data["api_key"] = self._api_key_edit.text().strip()
        data["api_key_env"] = self._api_key_env_edit.text().strip()
        data["region"] = self._region_edit.text().strip()
        data["allow_no_api_key"] = self._allow_no_key.isChecked()
        data["endpoint_mode"] = self._endpoint_combo.currentText().strip()
        data["timeout_s"] = float(self._timeout_spin.value())
        data["connect_timeout_s"] = float(self._connect_timeout_spin.value())
        data["verify_ssl"] = self._verify_ssl.isChecked()

        models = [self._models_list.item(i).text().strip() for i in range(self._models_list.count())]
        models = list(dict.fromkeys(item for item in models if item))
        active_model = str(self._active_model_combo.currentData() or self._active_model_combo.currentText()).strip()
        if active_model and active_model not in models:
            models.append(active_model)
        data["models"] = models
        data["model"] = active_model or (models[0] if models else "mock-v2" if provider_type == "mock" else "")

        override: dict[str, bool] = {}
        for mode, combo in (
            ("ultra_fast", self._stream_ultra),
            ("fast", self._stream_fast),
            ("quality", self._stream_quality),
        ):
            value = combo.currentData()
            if isinstance(value, bool):
                override[mode] = value
        data["streaming_override"] = override
        if provider_type in (TRIAL_TYPE, MICROSOFT_TYPE):
            data = provider_profile_to_dict(provider_profile_from_dict(data))
        self._working_profiles[name] = data

    def _add_trial_provider(self) -> None:
        self._commit_current_form()
        if "Trial" not in self._working_profiles:
            self._working_profiles["Trial"] = provider_profile_to_dict(
                provider_profile_from_dict(trial_profile_values({})))
        self._rebuild_provider_list(select="Trial")
        self._rebuild_active_profile_combo()

    def _add_google_provider(self, name: str) -> None:
        self._commit_current_form()
        if name not in self._working_profiles:
            preset = deepcopy(GOOGLE_PROVIDER_PRESETS[name])
            self._working_profiles[name] = provider_profile_to_dict(provider_profile_from_dict(preset))
        self._rebuild_provider_list(select=name)
        self._rebuild_active_profile_combo()

    def _add_microsoft_provider(self) -> None:
        self._commit_current_form()
        name = "Microsoft Translator"
        if name not in self._working_profiles:
            self._working_profiles[name] = provider_profile_to_dict(provider_profile_from_dict(MICROSOFT_PRESET))
        self._rebuild_provider_list(select=name)
        self._rebuild_active_profile_combo()

    def _on_provider_type_changed(self, kind: str) -> None:
        if self._loading_form:
            return
        if kind == MICROSOFT_TYPE:
            self._base_url_edit.setText(MICROSOFT_PRESET["base_url"])
            self._models_list.clear()
            self._models_list.addItems(MICROSOFT_PRESET["models"])
            self._active_model_combo.clear()
            self._active_model_combo.addItems(MICROSOFT_PRESET["models"])
        if kind == TRIAL_TYPE:
            self._base_url_edit.setText(TRIAL_BASE_URL)
            self._models_list.clear()
            self._models_list.addItems(TRIAL_MODELS)
            self._active_model_combo.clear()
            for model in TRIAL_MODELS:
                self._active_model_combo.addItem(trial_model_label(model), model)
        if kind in {"google_translate_web", "google_cloud_translate"}:
            name = "Google Translate Free" if kind == "google_translate_web" else "Google Cloud Translate"
            preset = GOOGLE_PROVIDER_PRESETS[name]
            self._base_url_edit.setText(str(preset["base_url"]))
            self._models_list.clear()
            self._models_list.addItems(preset["models"])
            self._active_model_combo.clear()
            self._active_model_combo.addItems(preset["models"])
        self._set_provider_form_enabled()

    def _add_provider(self) -> None:
        name, ok = QInputDialog.getText(self, "Thêm provider", "Tên profile/provider:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self._working_profiles:
            QMessageBox.warning(self, "Tên đã tồn tại", f"Provider '{name}' đã tồn tại.")
            return
        self._commit_current_form()
        self._working_profiles[name] = {
            "type": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "api_key": "",
            "api_key_env": "",
            "allow_no_api_key": False,
            "model": "",
            "models": [],
            "endpoint_mode": "auto",
            "endpoint_paths": {
                "responses": "/responses",
                "chat_completions": "/chat/completions",
                "completions": "/completions",
            },
            "auto_order": ["responses", "chat_completions", "completions"],
            "timeout_s": 45.0,
            "connect_timeout_s": 10.0,
            "verify_ssl": True,
            "temperature": None,
            "max_output_tokens": None,
            "extra_headers": {},
            "extra_body": {},
            "endpoint_extra_body": {},
            "streaming_override": {},
        }
        self._active_profile = name
        self._rebuild_provider_list(select=name)
        self._rebuild_active_profile_combo()

    def _rename_provider(self) -> None:
        item = self._provider_list.currentItem()
        if not item:
            return
        old = item.text()
        new, ok = QInputDialog.getText(self, "Đổi tên provider", "Tên mới:", text=old)
        new = new.strip()
        if not ok or not new or new == old:
            return
        if new in self._working_profiles:
            QMessageBox.warning(self, "Tên đã tồn tại", f"Provider '{new}' đã tồn tại.")
            return
        self._commit_current_form()
        rebuilt: dict[str, dict[str, Any]] = {}
        for name, data in self._working_profiles.items():
            rebuilt[new if name == old else name] = data
        self._working_profiles = rebuilt
        if self._active_profile == old:
            self._active_profile = new
        self._current_profile_name = None
        self._rebuild_provider_list(select=new)
        self._rebuild_active_profile_combo()

    def _delete_provider(self) -> None:
        item = self._provider_list.currentItem()
        if not item:
            return
        if len(self._working_profiles) <= 1:
            QMessageBox.warning(self, "Không thể xóa", "Phải giữ lại ít nhất một provider.")
            return
        name = item.text()
        answer = QMessageBox.question(
            self,
            "Xóa provider",
            f"Xóa provider '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._working_profiles.pop(name, None)
        if self._active_profile == name:
            self._active_profile = next(iter(self._working_profiles))
        self._current_profile_name = None
        self._rebuild_provider_list(select=self._active_profile)
        self._rebuild_active_profile_combo()

    def _add_model(self) -> None:
        model, ok = QInputDialog.getText(self, "Thêm model", "Model ID chính xác từ provider:")
        model = model.strip()
        if not ok or not model:
            return
        existing = [self._models_list.item(i).text() for i in range(self._models_list.count())]
        if model not in existing:
            self._models_list.addItem(model)
            self._active_model_combo.addItem(model)
        self._active_model_combo.setCurrentText(model)

    def _remove_model(self) -> None:
        row = self._models_list.currentRow()
        if row < 0:
            return
        model = self._models_list.item(row).text()
        self._models_list.takeItem(row)
        idx = self._active_model_combo.findText(model)
        if idx >= 0:
            self._active_model_combo.removeItem(idx)
        # An empty model list is allowed while editing; Save & Apply will
        # require a model for non-mock providers.

    def _save_and_apply(self) -> None:
        self._commit_current_form()
        active = self._active_profile_combo.currentText().strip()
        if active not in self._working_profiles:
            QMessageBox.warning(self, "Provider không hợp lệ", "Hãy chọn provider mặc định hợp lệ.")
            return

        for name, data in self._working_profiles.items():
            provider_type = str(data.get("type", "openai_compatible"))
            model = str(data.get("model", "")).strip()
            if not model:
                QMessageBox.warning(self, "Thiếu model", f"Provider '{name}' chưa có model.")
                return
            if provider_type != "mock" and not str(data.get("base_url", "")).strip():
                QMessageBox.warning(self, "Thiếu Base URL", f"Provider '{name}' chưa có Base URL.")
                return

        self._active_profile = active
        self.save_providers_requested.emit(deepcopy(self._working_profiles), active)

    # --------------------------------------------------------- prompt editor
    def set_prompt_overrides(self, overrides: Mapping[str, Any] | None) -> None:
        self._prompt_overrides = normalize_prompt_overrides(overrides)
        if hasattr(self, "_prompt_mode_combo"):
            self._load_selected_prompt()

    def _selected_prompt_key(self) -> tuple[str, str]:
        mode = str(self._prompt_mode_combo.currentData() or "fast")
        style = str(self._prompt_style_combo.currentData() or "engineering")
        return mode, style

    def _load_selected_prompt(self) -> None:
        if not hasattr(self, "_prompt_editor"):
            return
        mode, style = self._selected_prompt_key()
        template, custom = resolve_prompt_template(mode, style, self._prompt_overrides)
        self._prompt_editor.setPlainText(template)
        self._prompt_status.setText("TÙY CHỈNH" if custom else "MẶC ĐỊNH")
        self._prompt_status.setStyleSheet(
            "font-weight: 600; color: #FBBF24;" if custom else "font-weight: 600; color: #34D399;"
        )
        self._refresh_prompt_preview()

    def _save_prompt_editor(self) -> None:
        mode, style = self._selected_prompt_key()
        template = self._prompt_editor.toPlainText().strip()
        try:
            validate_prompt_template(template)
        except Exception as exc:
            QMessageBox.warning(self, "Prompt không hợp lệ", str(exc))
            return
        self.save_prompt_requested.emit(mode, style, template)

    def _reset_prompt_editor(self) -> None:
        mode, style = self._selected_prompt_key()
        answer = QMessageBox.question(
            self,
            "Reset prompt",
            f"Reset {PERFORMANCE_LABELS[mode]} / {CONTEXT_LABELS[style]} về prompt mặc định?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.reset_prompt_requested.emit(mode, style)

    def _reset_all_prompts(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset toàn bộ prompt",
            "Xóa tất cả prompt tùy chỉnh và quay về mặc định cho cả 9 tổ hợp?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.reset_all_prompts_requested.emit()

    def _load_default_prompt_into_editor(self) -> None:
        mode, style = self._selected_prompt_key()
        self._prompt_editor.setPlainText(default_prompt_template(mode, style))
        self._refresh_prompt_preview()

    def _refresh_prompt_preview(self) -> None:
        if not hasattr(self, "_prompt_preview"):
            return
        _, style = self._selected_prompt_key()
        template = self._prompt_editor.toPlainText().strip()
        if not template:
            self._prompt_preview.setPlainText("Prompt đang trống.")
            return
        try:
            rendered = render_prompt_template(
                template,
                source_language=self._config.translation.source_language,
                target_language=self._runtime_target_language,
                context_preset=style,
                glossary="",
            )
        except Exception as exc:
            rendered = f"LỖI PREVIEW: {exc}"
        self._prompt_preview.setPlainText(rendered)

    # ------------------------------------------------------ provider utilities
    def _test_current_provider(self) -> None:
        self._commit_current_form()
        name = self._current_profile_name
        if not name or name not in self._working_profiles:
            QMessageBox.warning(self, "Test provider", "Hãy chọn provider cần test.")
            return
        self.test_provider_requested.emit(name, deepcopy(self._working_profiles[name]))

    def set_provider_test_busy(self, busy: bool) -> None:
        self._provider_test_button.setEnabled(not busy)
        if busy:
            self._provider_test_status.setText("Đang test API/model...")

    def show_provider_test_result(self, success: bool, message: str) -> None:
        self.set_provider_test_busy(False)
        prefix = "✓ " if success else "✗ "
        self._provider_test_status.setText(prefix + message)
        self._provider_test_status.setStyleSheet(
            "color: #4aa564;" if success else "color: #d9534f;"
        )

    def _choose_import_provider_catalog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import providers.json",
            "",
            "JSON files (*.json);;All files (*.*)",
        )
        if path:
            self.import_providers_requested.emit(path)

    def _choose_export_provider_catalog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export providers.json",
            "providers.json",
            "JSON files (*.json);;All files (*.*)",
        )
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            self.export_providers_requested.emit(path)

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _normalized_models(data: dict[str, Any]) -> list[str]:
        raw = data.get("models", [])
        if isinstance(raw, str):
            models = [raw]
        elif isinstance(raw, (list, tuple)):
            models = [str(item).strip() for item in raw if str(item).strip()]
        else:
            models = []
        model = str(data.get("model", "")).strip()
        if model and model not in models:
            models.insert(0, model)
        if not models and data.get("type") == "mock":
            models = ["mock-v2"]
        return list(dict.fromkeys(models))

    @staticmethod
    def _set_combo_text(combo: QComboBox, text: str) -> None:
        idx = combo.findText(text)
        if idx < 0:
            combo.addItem(text)
            idx = combo.findText(text)
        combo.setCurrentIndex(idx)

    @staticmethod
    def _set_stream_combo(combo: QComboBox, value: Any) -> None:
        target = value if isinstance(value, bool) else None
        for i in range(combo.count()):
            if combo.itemData(i) is target:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)

    def _set_provider_form_enabled(self) -> None:
        kind = self._type_combo.currentText()
        trial = kind == TRIAL_TYPE
        enabled = kind != "mock"
        microsoft = kind == MICROSOFT_TYPE
        google = kind in {"google_translate_web", "google_cloud_translate", MICROSOFT_TYPE}
        for widget in (
            self._base_url_edit,
            self._api_key_edit,
            self._api_key_env_edit,
            self._allow_no_key,
            self._endpoint_combo,
            self._timeout_spin,
            self._connect_timeout_spin,
            self._verify_ssl,
        ):
            widget.setEnabled(enabled)
        self._endpoint_combo.setEnabled(enabled and not google)
        self._allow_no_key.setEnabled(enabled and not google)
        self._base_url_edit.setReadOnly(google or trial)
        for widget in (self._api_key_edit, self._api_key_env_edit, self._show_key):
            widget.setEnabled(enabled and kind != "google_translate_web")
        for widget in (self._active_model_combo, self._models_list, *self._model_buttons,
                       self._stream_ultra, self._stream_fast, self._stream_quality):
            widget.setEnabled(not google)
        self._google_provider_note.setVisible(google)
        self._connection_form.setRowVisible(self._region_edit, microsoft)
        self._connection_form.setRowVisible(self._endpoint_combo, not microsoft)
        self._microsoft_usage_group.setVisible(microsoft)
        if microsoft:
            self.refresh_microsoft_usage()
        self._models_group.setVisible(not google)
        self._stream_group.setVisible(not google)
        self._trial_group.setVisible(trial)
        self._connection_group.setTitle("ScreenTranslator AI Trial" if trial else "Kết nối API")
        for widget in (self._profile_name_label, self._type_combo, self._base_url_edit,
                       self._api_key_env_edit, self._allow_no_key,
                       self._timeout_spin, self._connect_timeout_spin, self._verify_ssl):
            self._connection_form.setRowVisible(widget, not trial)
        if microsoft:
            for widget in (self._allow_no_key, self._connect_timeout_spin, self._verify_ssl,
                           self._api_key_env_edit, self._timeout_spin):
                self._connection_form.setRowVisible(widget, False)
        self._models_group.setTitle("Chọn model dịch" if trial else "Models")
        self._active_model_label.setVisible(not trial)
        self._models_list.setVisible(not trial)
        for button in self._model_buttons:
            button.setVisible(not trial)
        self._provider_test_hint.setText(
            "Kiểm tra kết nối bằng key và model đang chọn. Lần kiểm tra có thể sử dụng ngân sách Trial."
            if trial else "Gửi một request rất ngắn để kiểm tra Base URL, API key, endpoint và model hiện đang chọn. "
            "Request test có thể phát sinh chi phí nhỏ tùy provider.")
        self._provider_test_button.setText("Kiểm tra key / model" if trial else "Test provider / model hiện tại")
        if trial:
            self.refresh_trial_quota()
        if microsoft:
            self._google_provider_note.setText("Microsoft Translator Text v3: nhập Key 1 hoặc Key 2 và Region của resource Azure. "
                                               "F0 có mốc 2 triệu ký tự/tháng; quyền và quota do Azure quản lý. "
                                               "Không dùng prompt, model AI hay streaming.")
            self._provider_test_hint.setText("Gửi Hello → Tiếng Việt để kiểm tra key và region; có tính vào usage.")
            self._provider_test_button.setText("Kiểm tra Microsoft Translator")
        elif google:
            service = ("Free: endpoint không chính thức, không cần key; có thể bị giới hạn hoặc ngừng hoạt động. "
                       "Văn bản được gửi đến Google trong URL GET." if kind == "google_translate_web" else
                       "Cloud Basic v2: cần API key, bật Cloud Translation API và billing; có thể phát sinh chi phí.")
            self._google_provider_note.setText(service + " Không dùng prompt, style, tốc độ AI, endpoint OpenAI hay streaming. "
                                               "Không tự chuyển Free sang Cloud khi lỗi.")

    def refresh_microsoft_usage(self) -> None:
        if self._type_combo.currentText() != MICROSOFT_TYPE:
            return
        import sqlite3
        from microsoft_translator_usage import LocalUsageLedger
        try:
            usage = LocalUsageLedger(self._config.data_dir / "microsoft_usage.sqlite3").month_usage()
            self._microsoft_usage_status.setText(
                f"Tháng {usage.month}: {usage.local_total:,} ký tự / {usage.calls:,} request. "
                f"Header request: {usage.verified_characters:,}; ước lượng: {usage.estimated_characters:,}.")
        except (OSError, sqlite3.Error):
            self._microsoft_usage_status.setText("Không đọc được thống kê cục bộ; vẫn có thể dịch.")

    def refresh_trial_quota(self) -> None:
        if self._type_combo.currentText() != TRIAL_TYPE:
            return
        usage = TrialUsageStore(self._config.data_dir / "trial_usage.json")
        self._trial_quota.setValue(usage.remaining(self._api_key_edit.text()))

    def _refresh_region_config_summary(self) -> None:
        if not hasattr(self, "_region_hotkey_label"):
            return
        self._region_hotkey_label.setText(self._config.hotkeys.region_translate)
        self._region_ocr_engine_label.setText(self._config.ocr.engine)
        self._region_ocr_confidence_label.setText(f"{self._config.ocr.min_confidence:.2f}")
        enabled = bool(self._config.features.region_translate_enabled)
        self._region_translate_button.setEnabled(enabled)
        self._overview_region_button.setEnabled(enabled)
        self._region_translate_button.setToolTip(
            "" if enabled else "features.region_translate_enabled đang tắt trong config.json"
        )

    # ------------------------------------------------------ tray/window behavior
    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def allow_close(self) -> None:
        self._allow_close = True

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self.hide)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self.exit_requested.emit()
