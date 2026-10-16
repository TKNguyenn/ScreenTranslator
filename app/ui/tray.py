from __future__ import annotations

from collections.abc import Callable, Mapping

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from app.config import ProviderProfile
from app.languages import TRAY_TARGET_LANGUAGES
from app.version import APP_VERSION
from app.ui.theme import asset_icon


PERFORMANCE_MODES = (
    ("ultra_fast", "Cực nhanh - tối ưu độ trễ"),
    ("fast", "Nhanh - ưu tiên tốc độ"),
    ("quality", "Chuẩn - ưu tiên chất lượng"),
)

CONTEXT_PRESETS = (
    ("engineering", "Engineer - kỹ thuật"),
    ("chat", "Chat - hội thoại"),
    ("email", "Email - công việc"),
)


class TrayIcon:
    def __init__(
        self,
        app: QApplication,
        provider_profiles: Mapping[str, ProviderProfile],
        active_provider: str,
        active_target_language: str,
        active_performance_mode: str,
        active_context_preset: str,
        cache_enabled: bool,
        on_open_main_window: Callable[[], None],
        on_translate: Callable[[], None],
        on_translate_replace: Callable[[], None],
        on_region_translate: Callable[[], None],
        region_translate_enabled: bool,
        quick_auto_enabled: bool,
        on_quick_auto_toggle: Callable[[bool], None],
        on_open_quick_settings: Callable[[], None],
        on_target_language: Callable[[str], None],
        on_provider: Callable[[str], None],
        on_performance_mode: Callable[[str], None],
        on_context_preset: Callable[[str], None],
        on_cache_enabled: Callable[[bool], None],
        on_show_diagnostics: Callable[[], None],
        on_reload_config: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        icon = asset_icon()
        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip("AI Screen Translator")
        self._on_open_main_window = on_open_main_window
        self._tray.activated.connect(self._on_activated)

        self._menu = QMenu()
        self._language_actions: dict[str, QAction] = {}
        self._provider_actions: dict[str, QAction] = {}
        self._performance_actions: dict[str, QAction] = {}
        self._context_actions: dict[str, QAction] = {}

        self._version_action = QAction(f"AI Screen Translator v{APP_VERSION}", self._menu)
        self._version_action.setEnabled(False)
        self._menu.addAction(self._version_action)

        self._open_action = QAction(
            app.style().standardIcon(QStyle.SP_TitleBarNormalButton),
            "Mở cửa sổ chính",
            self._menu,
        )
        open_font = self._open_action.font()
        open_font.setBold(True)
        self._open_action.setFont(open_font)
        self._open_action.triggered.connect(on_open_main_window)
        self._menu.addAction(self._open_action)
        self._menu.addSeparator()

        self._translate_action = QAction("Dịch văn bản đang bôi đen", self._menu)
        self._translate_replace_action = QAction(
            "Dịch và thay thế văn bản đang bôi đen", self._menu
        )
        self._translate_action.triggered.connect(on_translate)
        self._translate_replace_action.triggered.connect(on_translate_replace)
        self._menu.addAction(self._translate_action)
        self._menu.addAction(self._translate_replace_action)

        self._region_action = QAction("Dịch vùng màn hình", self._menu)
        self._region_action.setEnabled(bool(region_translate_enabled))
        self._region_action.setToolTip(
            "Kéo chọn một vùng trên monitor hiện tại, OCR local rồi dịch text."
        )
        self._region_action.triggered.connect(on_region_translate)
        self._menu.addAction(self._region_action)

        self._quick_auto_action = QAction("Tự hiện Quick Toolbar khi bôi đen", self._menu)
        self._quick_auto_action.setCheckable(True)
        self._quick_auto_action.setChecked(quick_auto_enabled)
        self._quick_auto_action.triggered.connect(
            lambda checked=False: on_quick_auto_toggle(bool(checked))
        )
        self._menu.addAction(self._quick_auto_action)
        self._quick_settings_action = QAction("Cài đặt Quick UX...", self._menu)
        self._quick_settings_action.triggered.connect(on_open_quick_settings)
        self._menu.addAction(self._quick_settings_action)

        self._reload_action = QAction(
            app.style().standardIcon(QStyle.SP_BrowserReload),
            "Reload config.json",
            self._menu,
        )
        self._reload_action.setToolTip(
            "Đọc lại config.json + providers.json + prompts.json + .env và áp dụng provider, model, prompt, streaming, cache, "
            "hotkey mà không cần khởi động lại app."
        )
        self._reload_action.triggered.connect(on_reload_config)
        self._menu.addAction(self._reload_action)
        self._menu.addSeparator()

        language_menu = self._menu.addMenu("Dịch sang")
        language_group = QActionGroup(language_menu)
        language_group.setExclusive(True)
        for code, label in TRAY_TARGET_LANGUAGES:
            action = QAction(label, language_menu)
            action.setCheckable(True)
            action.setData(code)
            action.setChecked(code == active_target_language)
            action.triggered.connect(
                lambda checked=False, language=code: on_target_language(language)
            )
            language_group.addAction(action)
            language_menu.addAction(action)
            self._language_actions[code] = action

        context_menu = self._menu.addMenu("Kiểu dịch")
        context_group = QActionGroup(context_menu)
        context_group.setExclusive(True)
        for preset, label in CONTEXT_PRESETS:
            action = QAction(label, context_menu)
            action.setCheckable(True)
            action.setData(preset)
            action.setChecked(preset == active_context_preset)
            action.triggered.connect(
                lambda checked=False, selected=preset: on_context_preset(selected)
            )
            context_group.addAction(action)
            context_menu.addAction(action)
            self._context_actions[preset] = action

        self._provider_menu = self._menu.addMenu("API / Model")
        self._on_provider = on_provider
        self._provider_group: QActionGroup | None = None
        self.update_provider_profiles(provider_profiles, active_provider)

        performance_menu = self._menu.addMenu("Tốc độ dịch")
        performance_group = QActionGroup(performance_menu)
        performance_group.setExclusive(True)
        for mode, label in PERFORMANCE_MODES:
            action = QAction(label, performance_menu)
            action.setCheckable(True)
            action.setData(mode)
            action.setChecked(mode == active_performance_mode)
            action.triggered.connect(
                lambda checked=False, selected_mode=mode: on_performance_mode(selected_mode)
            )
            performance_group.addAction(action)
            performance_menu.addAction(action)
            self._performance_actions[mode] = action

        self._cache_action = QAction("Bật cache bản dịch", self._menu)
        self._cache_action.setCheckable(True)
        self._cache_action.setChecked(cache_enabled)
        self._cache_action.setToolTip(
            "Tắt để luôn gọi API (hữu ích khi benchmark). Cache cũ không bị xóa."
        )
        self._cache_action.triggered.connect(
            lambda checked=False: on_cache_enabled(bool(checked))
        )
        self._menu.addAction(self._cache_action)

        self._menu.addSeparator()
        self._status_action = QAction("", self._menu)
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)

        self._diagnostics_action = QAction("Chẩn đoán / cấu hình", self._menu)
        self._diagnostics_action.triggered.connect(on_show_diagnostics)
        self._menu.addAction(self._diagnostics_action)

        self._live_action = QAction("Live screen translate (V0.4.5)", self._menu)
        self._live_action.setEnabled(False)
        self._menu.addSeparator()
        self._menu.addAction(self._live_action)

        self._menu.addSeparator()
        self._quit_action = QAction(
            app.style().standardIcon(QStyle.SP_DialogCloseButton),
            "Thoát ứng dụng",
            self._menu,
        )
        font = self._quit_action.font()
        font.setBold(True)
        self._quit_action.setFont(font)
        self._quit_action.triggered.connect(on_quit)
        self._menu.addAction(self._quit_action)

        self._tray.setContextMenu(self._menu)
        self.update_state(
            active_target_language,
            active_provider,
            provider_profiles,
            active_performance_mode,
            active_context_preset,
            cache_enabled,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._on_open_main_window()

    @staticmethod
    def _provider_label(profile_name: str, profile: ProviderProfile) -> str:
        model = profile.model or "<no model>"
        return f"{profile_name}  [{model}]"

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def notify(self, title: str, message: str, timeout_ms: int = 3500) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.Information, timeout_ms)

    def set_target_language(self, language: str) -> None:
        for code, action in self._language_actions.items():
            action.setChecked(code == language)

    def update_provider_profiles(
        self,
        provider_profiles: Mapping[str, ProviderProfile],
        active_provider: str,
    ) -> None:
        self._provider_menu.clear()
        self._provider_actions.clear()
        self._provider_group = QActionGroup(self._provider_menu)
        self._provider_group.setExclusive(True)
        for profile_name, profile in provider_profiles.items():
            action = QAction(self._provider_label(profile_name, profile), self._provider_menu)
            action.setCheckable(True)
            action.setData(profile_name)
            action.setChecked(profile_name == active_provider)
            action.triggered.connect(
                lambda checked=False, name=profile_name: self._on_provider(name)
            )
            self._provider_group.addAction(action)
            self._provider_menu.addAction(action)
            self._provider_actions[profile_name] = action

    def set_provider(self, profile_name: str) -> None:
        for name, action in self._provider_actions.items():
            action.setChecked(name == profile_name)

    def set_performance_mode(self, mode: str) -> None:
        for name, action in self._performance_actions.items():
            action.setChecked(name == mode)

    def set_context_preset(self, preset: str) -> None:
        for name, action in self._context_actions.items():
            action.setChecked(name == preset)

    def set_cache_enabled(self, enabled: bool) -> None:
        self._cache_action.setChecked(bool(enabled))

    def set_quick_auto_enabled(self, enabled: bool) -> None:
        self._quick_auto_action.setChecked(bool(enabled))

    def set_region_translate_enabled(self, enabled: bool) -> None:
        self._region_action.setEnabled(bool(enabled))

    def update_state(
        self,
        target_language: str,
        provider_name: str,
        provider_profiles: Mapping[str, ProviderProfile],
        performance_mode: str,
        context_preset: str,
        cache_enabled: bool,
        streaming_enabled: bool = False,
        streaming_source: str = "global",
    ) -> None:
        self.set_target_language(target_language)
        current_profiles = set(self._provider_actions)
        new_profiles = set(provider_profiles)
        labels_changed = any(
            name in self._provider_actions
            and self._provider_actions[name].text() != self._provider_label(name, profile)
            for name, profile in provider_profiles.items()
        )
        if current_profiles != new_profiles or labels_changed:
            self.update_provider_profiles(provider_profiles, provider_name)
        self.set_provider(provider_name)
        self.set_performance_mode(performance_mode)
        self.set_context_preset(context_preset)
        self.set_cache_enabled(cache_enabled)
        profile = provider_profiles.get(provider_name)
        google = profile is not None and profile.type in {"google_translate_web", "google_cloud_translate"}
        for action in (*self._context_actions.values(), *self._performance_actions.values()):
            action.setEnabled(not google)
        if google:
            context_preset = "Dịch trực tiếp"
            performance_mode = "Không dùng tốc độ AI"
        model = profile.model if profile is not None else "<invalid>"
        cache_text = "cache:on" if cache_enabled else "cache:off"
        stream_text = f"stream:{'on' if streaming_enabled else 'off'}({streaming_source})"
        self._status_action.setText(
            f"Đang dùng: {target_language} | {context_preset} | {provider_name} | "
            f"{model} | {performance_mode} | {stream_text} | {cache_text}"
        )
        self._tray.setToolTip(
            f"AI Screen Translator | {target_language} | {context_preset} | "
            f"{provider_name} | {model} | {performance_mode} | {stream_text} | {cache_text}"
        )
