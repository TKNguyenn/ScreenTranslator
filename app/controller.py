from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QMessageBox
from dotenv import load_dotenv

from app.config import (
    AppConfig,
    parse_hotkey_section,
    ProviderSection,
    QuickUxSection,
    parse_quick_ux_section,
    provider_profile_from_dict,
    provider_profile_to_dict,
    profile_override_entry,
    portable_provider_entry,
    resolve_config_path,
    resolve_provider_catalog_path,
    resolve_prompt_catalog_path,
)
from app.languages import TRAY_TARGET_LANGUAGE_CODES
from app.models import (
    HotkeyAction,
    OcrResult,
    PasteResult,
    RegionCaptureResult,
    RequestMode,
    SelectionResult,
    TranslationProgress,
    TranslationRequest,
    TranslationResult,
)
from app.providers.factory import create_translation_provider, resolve_provider_profile
from app.ocr.factory import create_ocr_engine
from app.providers.unavailable_provider import UnavailableTranslationProvider
from app.services.cache import TranslationCache
from app.services.config_store import ConfigFileStore
from app.services.provider_catalog import ProviderCatalogStore
from app.services.prompt_catalog import PromptCatalogStore
from app.services.clipboard import ClipboardSelectionService
from app.services.foreground_tracker import ForegroundWindowTracker
from app.services.hotkeys import HotkeyService
from app.services.runtime_settings import RuntimeSettingsStore
from app.services.trial_usage import TrialUsageStore
from app.services.window_service import WindowService
from app.services.updates import UpdateManager, Release, installed_app_root, launch_installer, version_tuple
from app.version import APP_VERSION
from app.quickux.selection import MouseSelectionCandidate, QuickSelectionProbe, QuickSelectionCheck, SelectionSnapshot
from app.quickux.mouse_monitor import MouseSelectionMonitor
from app.quickux.selection_worker import QuickSelectionWorker
from app.ui.quick_toolbar import QuickToolbar
from app.ui.quick_popup import QuickTranslationPopup
from app.prompts import prompt_is_custom, validate_prompt_template
from app.ui.main_window import MainWindow
from app.ui.usage_guide import UsageGuideDialog
from app.ui.popup import TranslationPopup
from app.ui.region_selector import RegionSelectorOverlay
from app.ui.tray import TrayIcon
from app.workers.input_worker import InputWorker
from app.workers.ocr_worker import OcrWorker
from app.workers.translation_worker import TranslationWorker


logger = logging.getLogger(__name__)


class WorkerBridge(QObject):
    hotkey = Signal(object)
    hotkey_ready = Signal()
    hotkey_error = Signal(str)
    selection = Signal(object)
    ocr = Signal(object)
    paste = Signal(object)
    translation_progress = Signal(object)
    translation = Signal(object)
    provider_test_result = Signal(object)
    quick_mouse = Signal(object)
    quick_external_press = Signal()
    quick_probe = Signal(object)
    quick_check = Signal(object)
    quick_error = Signal(str)
    quick_escape = Signal()


@dataclass
class PendingJob:
    mode: RequestMode
    restore_main_window: bool = False
    quick: bool = False
    quick_snapshot: SelectionSnapshot | None = None


class AppController(QObject):
    def __init__(self, app: QApplication, config: AppConfig) -> None:
        super().__init__()
        self._app = app
        self._config = config
        self._pending: dict[str, PendingJob] = {}
        self._visible_job_id: str | None = None
        self._startup_provider_error: str | None = None

        self._runtime_settings = RuntimeSettingsStore(
            config.data_dir / "runtime_settings.json"
        )
        saved = self._runtime_settings.load()

        saved_language = str(saved.get("target_language", ""))
        self._target_language = (
            saved_language
            if saved_language in TRAY_TARGET_LANGUAGE_CODES
            else config.translation.target_language
        )

        saved_performance = str(saved.get("performance_mode", "")).strip().lower()
        configured_performance = config.translation.performance_mode.strip().lower()
        self._performance_mode = (
            saved_performance
            if saved_performance in {"ultra_fast", "fast", "quality"}
            else configured_performance
            if configured_performance in {"ultra_fast", "fast", "quality"}
            else "fast"
        )

        saved_context = str(saved.get("context_preset", "")).strip().lower()
        configured_context = config.translation.context_preset.strip().lower()
        self._context_preset = (
            saved_context
            if saved_context in {"engineering", "chat", "email"}
            else configured_context
            if configured_context in {"engineering", "chat", "email"}
            else "engineering"
        )

        self._cache_enabled = bool(config.translation.cache_enabled)
        self._config_store = ConfigFileStore(resolve_config_path())
        self._provider_catalog_store = ProviderCatalogStore(
            resolve_provider_catalog_path(
                config.providers.catalog_path, config_path=resolve_config_path()
            )
        )
        self._prompt_catalog_store = PromptCatalogStore(
            resolve_prompt_catalog_path(
                config.translation.prompt_catalog_path, config_path=resolve_config_path()
            )
        )
        self._prompt_overrides = self._prompt_catalog_store.read_overrides()

        saved_profile = str(saved.get("provider_profile", ""))
        initial_profile_name = (
            saved_profile
            if saved_profile in config.providers.profiles
            else config.providers.active_profile
        )

        try:
            self._profile_name, self._profile = resolve_provider_profile(
                config, initial_profile_name
            )
        except Exception as exc:
            self._profile_name = "invalid"
            self._profile = None
            self._startup_provider_error = str(exc)

        self._bridge = WorkerBridge()
        self._bridge.hotkey.connect(self._on_hotkey)
        self._bridge.hotkey_ready.connect(self._on_hotkey_ready)
        self._bridge.hotkey_error.connect(self._on_hotkey_error)
        self._bridge.selection.connect(self._on_selection)
        self._bridge.ocr.connect(self._on_ocr)
        self._bridge.paste.connect(self._on_paste)
        self._bridge.translation_progress.connect(self._on_translation_progress)
        self._bridge.translation.connect(self._on_translation)
        self._bridge.provider_test_result.connect(self._on_provider_test_result)
        self._bridge.quick_mouse.connect(self._on_quick_mouse_candidate)
        self._bridge.quick_external_press.connect(self._on_quick_external_press)
        self._bridge.quick_probe.connect(self._on_quick_probe)
        self._bridge.quick_check.connect(self._on_quick_check)
        self._bridge.quick_error.connect(self._on_quick_error)
        self._bridge.quick_escape.connect(self._on_quick_escape)

        self._quick_serial = 0
        self._quick_last_status = "Chua nhan selection gesture tu mouse hook"
        self._quick_candidate: MouseSelectionCandidate | None = None
        self._quick_anchor = QCursor.pos()
        self._quick_snapshot: SelectionSnapshot | None = None
        self._quick_popup_snapshot: SelectionSnapshot | None = None
        self._quick_visible_job_id: str | None = None
        # Keep a tombstone until every async translation response has returned.
        # Otherwise a canceled Quick UX result could fall into the legacy path.
        self._quick_translation_ids: set[str] = set()
        self._quick_replace_text: dict[str, str] = {}
        self._quick_replace_cancel: dict[str, threading.Event] = {}
        self._quick_timer = QTimer(self)
        self._quick_timer.setSingleShot(True)
        self._quick_timer.timeout.connect(self._inspect_quick_selection)
        self._quick_selection_worker = QuickSelectionWorker(
            on_probe=self._bridge.quick_probe.emit,
            on_check=self._bridge.quick_check.emit,
            on_error=self._bridge.quick_error.emit,
        )
        self._quick_selection_worker.update_max_characters(config.quick_ux.max_selection_chars)
        self._mouse_selection_monitor = MouseSelectionMonitor(
            on_selection_candidate=self._bridge.quick_mouse.emit,
            on_external_press=self._bridge.quick_external_press.emit,
            on_error=self._bridge.quick_error.emit,
            enabled=config.quick_ux.auto_show_toolbar,
        )

        clipboard_service = ClipboardSelectionService(config.clipboard, config.hotkeys)
        self._input_worker = InputWorker(
            service=clipboard_service,
            on_selection=self._bridge.selection.emit,
            on_paste=self._bridge.paste.emit,
        )
        self._ocr_worker = OcrWorker(
            engine=create_ocr_engine(config.ocr),
            on_result=self._bridge.ocr.emit,
        )

        try:
            provider = create_translation_provider(config, initial_profile_name)
        except Exception as exc:
            self._startup_provider_error = str(exc)
            logger.exception("Provider initialization failed")
            provider = UnavailableTranslationProvider(
                error_message=self._startup_provider_error,
                model=getattr(self._profile, "model", "unavailable"),
            )

        self._cache = TranslationCache(config.cache_db_path, enabled=self._cache_enabled)
        self._translation_worker = TranslationWorker(
            provider=provider,
            cache=self._cache,
            config=config.translation,
            on_result=self._bridge.translation.emit,
            on_progress=self._bridge.translation_progress.emit,
            prompt_overrides=self._prompt_overrides,
        )

        self._foreground_tracker = ForegroundWindowTracker()
        self._hotkeys = HotkeyService(
            config.hotkeys,
            self._bridge.hotkey.emit,
            on_ready=self._bridge.hotkey_ready.emit,
            on_error=self._bridge.hotkey_error.emit,
            on_escape=self._bridge.quick_escape.emit,
        )
        self._popup = TranslationPopup(config.ui)
        self._popup.replace_requested.connect(self._on_popup_replace)
        self._quick_toolbar = QuickToolbar(config.quick_ux)
        self._quick_popup = QuickTranslationPopup(config.quick_ux)
        self._quick_toolbar.language_requested.connect(self._translate_quick_selection)
        self._quick_popup.replace_requested.connect(self._on_quick_popup_replace)
        self._quick_popup.closed.connect(self._on_quick_popup_closed)
        self._region_selector = RegionSelectorOverlay(config.ui)
        self._region_selector.captured.connect(self._on_region_captured)
        self._region_selector.cancelled.connect(self._on_region_cancelled)
        self._region_selector.failed.connect(self._on_region_failed)

        self._main_window = MainWindow(app=app, config=config)
        self._usage_guide: UsageGuideDialog | None = None
        self._main_window.usage_guide_requested.connect(self._show_usage_guide)
        self._available_update: Release | None = None
        self._updates = UpdateManager(self)
        self._updates.checked.connect(self._on_update_checked)
        self._updates.failed.connect(self._on_update_failed)
        self._updates.progress.connect(self._on_update_progress)
        self._updates.downloaded.connect(self._on_update_downloaded)
        self._main_window.check_updates_requested.connect(self._on_update_clicked)
        self._main_window.exit_requested.connect(app.quit)
        self._main_window.quick_ux_settings_requested.connect(self._save_quick_ux_settings)
        self._main_window.hotkeys_settings_requested.connect(self._save_hotkey_settings)
        self._main_window.reload_requested.connect(self._reload_config)
        self._main_window.save_providers_requested.connect(self._save_provider_configuration)
        self._main_window.save_prompt_requested.connect(self._save_prompt_override)
        self._main_window.reset_prompt_requested.connect(self._reset_prompt_override)
        self._main_window.reset_all_prompts_requested.connect(self._reset_all_prompt_overrides)
        self._main_window.test_provider_requested.connect(self._test_provider_configuration)
        self._main_window.import_providers_requested.connect(self._import_provider_catalog)
        self._main_window.export_providers_requested.connect(self._export_provider_catalog)
        self._main_window.region_translate_requested.connect(
            lambda: self._begin_region_job(restore_main_window=True)
        )
        self._main_window.load_config(
            config,
            active_profile=self._profile_name,
            target_language=self._target_language,
            context_preset=self._context_preset,
            performance_mode=self._performance_mode,
            cache_enabled=self._cache_enabled,
            prompt_overrides=self._prompt_overrides,
        )

        self._tray = TrayIcon(
            app=app,
            provider_profiles=config.providers.profiles,
            active_provider=self._profile_name,
            active_target_language=self._target_language,
            active_performance_mode=self._performance_mode,
            active_context_preset=self._context_preset,
            cache_enabled=self._cache_enabled,
            on_open_main_window=self._main_window.show_from_tray,
            on_translate=lambda: self._begin_selection_job(
                RequestMode.POPUP,
                preferred_hwnd=self._foreground_tracker.last_external_window(),
            ),
            on_translate_replace=lambda: self._begin_selection_job(
                RequestMode.REPLACE,
                preferred_hwnd=self._foreground_tracker.last_external_window(),
            ),
            on_region_translate=lambda: self._begin_region_job(restore_main_window=False),
            region_translate_enabled=config.features.region_translate_enabled,
            quick_auto_enabled=config.quick_ux.auto_show_toolbar,
            on_quick_auto_toggle=self._set_quick_auto_enabled,
            on_open_quick_settings=self._main_window.show_quick_ux_settings,
            on_target_language=self._set_target_language,
            on_provider=self._set_provider_profile,
            on_performance_mode=self._set_performance_mode,
            on_context_preset=self._set_context_preset,
            on_cache_enabled=self._set_cache_enabled,
            on_show_diagnostics=self._show_diagnostics,
            on_reload_config=self._reload_config,
            on_quit=app.quit,
            on_open_usage_guide=self._show_usage_guide,
        )

    @property
    def _log_path(self) -> str:
        return str(self._config.logs_dir / "app.log")

    @Slot()
    def show_main_window(self) -> None:
        self._main_window.show_from_tray()

    def start(self) -> None:
        self._foreground_tracker.start()
        self._quick_selection_worker.start()
        self._mouse_selection_monitor.start()
        self._input_worker.start()
        self._ocr_worker.start()
        self._translation_worker.start()
        self._hotkeys.start()
        self._tray.show()
        self._refresh_tray_state()
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

        model = getattr(self._profile, "model", "<invalid>")
        self._tray.notify(
            self._config.app.name,
            f"Ready | provider={self._profile_name} | model={model} | target={self._target_language}",
        )
        logger.info("Application started")
        QTimer.singleShot(0, self._check_updates_on_startup)

        if self._startup_provider_error:
            self._show_error_dialog(
                "Provider configuration error",
                self._startup_provider_error,
            )
        QTimer.singleShot(0, self._show_usage_guide_on_startup)

    def _show_usage_guide_on_startup(self) -> None:
        if self._runtime_settings.load().get('onboarding_seen') is not True:
            self._show_usage_guide()

    @Slot()
    def _show_usage_guide(self) -> None:
        if self._usage_guide is not None and self._usage_guide.isVisible():
            self._usage_guide.raise_()
            self._usage_guide.activateWindow()
            return
        try:
            self._main_window.show_from_tray()
            guide = UsageGuideDialog(self._config.hotkeys, self._main_window)
            screen = self._main_window.screen().availableGeometry()
            guide.resize(min(700, screen.width() - 40), min(740, screen.height() - 80))
            guide.show()
            if self._usage_guide is not None:
                self._usage_guide.deleteLater()
            self._usage_guide = guide
        except Exception:
            logger.exception('Cannot open usage guide')
            return
        try:
            self._runtime_settings.update(onboarding_seen=True)
        except OSError:
            logger.warning('Cannot persist usage guide marker; guide may appear again', exc_info=True)

    @Slot()
    def shutdown(self) -> None:
        logger.info("Application shutting down")
        self._updates.close()
        self._main_window.allow_close()
        self._tray.hide()
        self._hotkeys.stop()
        self._mouse_selection_monitor.stop()
        self._quick_timer.stop()
        self._quick_toolbar.hide()
        self._quick_popup.force_close()
        self._quick_selection_worker.stop()
        self._foreground_tracker.stop()
        self._region_selector.hide()
        self._input_worker.stop()
        self._ocr_worker.stop()
        self._translation_worker.stop()

    def _check_updates_on_startup(self) -> None:
        try:
            due = TrialUsageStore(self._config.data_dir / "trial_usage.json").claim_update_check()
        except OSError:
            logger.warning("Cannot persist daily update check; skipping automatic check", exc_info=True)
            return
        if due:
            self._check_for_updates()

    def _check_for_updates(self) -> None:
        self._main_window.set_update_state("Đang kiểm tra GitHub…", "Checking…", busy=True)
        self._updates.check()

    @Slot()
    def _on_update_clicked(self) -> None:
        if self._available_update is None:
            self._check_for_updates()
            return
        try:
            installed_app_root()
        except RuntimeError as exc:
            self._on_update_failed(str(exc))
            QMessageBox.information(self._main_window, "Cập nhật ứng dụng", str(exc))
            return
        self._main_window.set_update_state("Đang tải bộ cài…", "Downloading…", busy=True, progress=0)
        self._updates.download(self._available_update)

    @Slot(object)
    def _on_update_checked(self, release: Release) -> None:
        self._available_update = release if version_tuple(release.version) > version_tuple(APP_VERSION) else None
        if self._available_update:
            self._main_window.set_update_state(f"Có phiên bản mới: v{release.version}", f"Update to v{release.version}")
        else:
            status = f"Latest version: v{release.version}"
            if version_tuple(APP_VERSION) > version_tuple(release.version):
                status += f"\nĐang dùng bản mới hơn: v{APP_VERSION}"
            self._main_window.set_update_state(status)

    @Slot(int)
    def _on_update_progress(self, percent: int) -> None:
        self._main_window.set_update_state(f"Đang tải bản cập nhật: {percent}%", "Downloading…",
                                           busy=True, progress=percent)

    @Slot(str)
    def _on_update_failed(self, message: str) -> None:
        logger.warning("Update failed: %s", message)
        button = f"Update to v{self._available_update.version}" if self._available_update else "Check for updates"
        self._main_window.set_update_state(message, button)

    @Slot(str)
    def _on_update_downloaded(self, path: str) -> None:
        try:
            launch_installer(Path(path), self._available_update.sha256)
        except (OSError, RuntimeError) as exc:
            self._updates.close()
            self._on_update_failed(str(exc))
            return
        self._updates.keep_download_for_installer()
        self._app.quit()

    @Slot()
    def _on_hotkey_ready(self) -> None:
        logger.info("Global hotkeys are ready")

    @Slot(str)
    def _on_hotkey_error(self, message: str) -> None:
        self._show_error_dialog("Global hotkey error", message)

    @Slot(object)
    def _on_hotkey(self, action: HotkeyAction) -> None:
        logger.info("Hotkey action received: %s", action.value)
        if action == HotkeyAction.TRANSLATE_SELECTION:
            self._quick_toolbar.hide()
            self._begin_selection_job(RequestMode.POPUP)
            return
        if action == HotkeyAction.TRANSLATE_AND_REPLACE:
            self._quick_toolbar.hide()
            self._begin_selection_job(RequestMode.REPLACE)
            return
        if action == HotkeyAction.TARGET_VI:
            self._set_target_language("vi")
            return
        if action == HotkeyAction.TARGET_EN:
            self._set_target_language("en")
            return
        if action == HotkeyAction.TARGET_ZH_HANT:
            self._set_target_language("zh-Hant")
            return
        if action == HotkeyAction.LIVE_TOGGLE:
            self._tray.notify(
                "Live translation", "Chưa triển khai trong V0.4.0; dự kiến V0.4.5."
            )
            return
        if action == HotkeyAction.REGION_TRANSLATE:
            self._begin_region_job(restore_main_window=False)

    def _begin_region_job(self, restore_main_window: bool = False) -> None:
        self._quick_toolbar.hide()
        self._quick_popup.dismiss_if_unpinned()
        if not self._config.features.region_translate_enabled:
            self._tray.notify(
                "Region Translate",
                "Tính năng đang tắt. Bật features.region_translate_enabled trong config.json.",
                3200,
            )
            return
        if self._region_selector.is_selecting():
            self._tray.notify("Region Translate", "Đang có một vùng chọn chưa hoàn tất.", 2200)
            return

        job_id = uuid4().hex
        self._pending[job_id] = PendingJob(
            mode=RequestMode.REGION,
            restore_main_window=bool(restore_main_window and self._main_window.isVisible()),
        )
        self._popup.hide()
        if restore_main_window and self._main_window.isVisible():
            self._main_window.hide()

        delay_ms = max(0, int(self._config.ui.region_capture_delay_ms))
        logger.info(
            "Region job started id=%s screen_delay_ms=%s ocr=%s",
            job_id,
            delay_ms,
            self._config.ocr.engine,
        )
        QTimer.singleShot(delay_ms, lambda selected_job=job_id: self._start_region_selector(selected_job))

    def _start_region_selector(self, job_id: str) -> None:
        pending = self._pending.get(job_id)
        if pending is None or pending.mode != RequestMode.REGION:
            return
        try:
            self._region_selector.begin(job_id)
        except Exception as exc:
            logger.exception("Region selector failed to start")
            self._pending.pop(job_id, None)
            self._restore_main_window_if_needed(pending)
            self._show_error_dialog("Region capture failed", str(exc))

    @Slot(object)
    def _on_region_captured(self, result: RegionCaptureResult) -> None:
        pending = self._pending.get(result.job_id)
        if pending is None or pending.mode != RequestMode.REGION:
            return
        if result.error:
            self._pending.pop(result.job_id, None)
            self._restore_main_window_if_needed(pending)
            self._show_error_dialog("Region capture failed", result.error)
            return

        self._restore_main_window_if_needed(pending)
        model = getattr(self._profile, "model", "unavailable")
        self._visible_job_id = result.job_id
        self._popup.show_ocr_processing(
            provider_name=self._profile_name,
            model=model,
            ocr_engine=self._config.ocr.engine,
            image_size=(result.width_px, result.height_px),
        )
        logger.info(
            "Region captured id=%s screen=%s size=%sx%s png_bytes=%s",
            result.job_id,
            result.screen_name,
            result.width_px,
            result.height_px,
            len(result.image_png),
        )
        self._ocr_worker.submit(result.job_id, result.image_png)

    @Slot(str)
    def _on_region_cancelled(self, job_id: str) -> None:
        pending = self._pending.pop(job_id, None)
        if pending is not None:
            self._restore_main_window_if_needed(pending)
        if job_id == self._visible_job_id:
            self._visible_job_id = None
        logger.info("Region selection cancelled id=%s", job_id)

    @Slot(str, str)
    def _on_region_failed(self, job_id: str, message: str) -> None:
        pending = self._pending.pop(job_id, None)
        if pending is not None:
            self._restore_main_window_if_needed(pending)
        if job_id == self._visible_job_id:
            self._visible_job_id = None
        self._show_error_dialog("Region capture failed", message)

    @Slot(object)
    def _on_ocr(self, result: OcrResult) -> None:
        pending = self._pending.get(result.job_id)
        if pending is None or pending.mode != RequestMode.REGION:
            return
        if result.error:
            self._pending.pop(result.job_id, None)
            if result.job_id == self._visible_job_id:
                self._visible_job_id = None
            self._popup.show_error(
                original="Region OCR",
                error_message=result.error,
                log_path=self._log_path,
                foreground_hwnd=None,
            )
            return

        model = getattr(self._profile, "model", "unavailable")
        self._popup.show_processing(
            original=result.text,
            target_language=self._target_language,
            provider_name=self._profile_name,
            model=model,
            foreground_hwnd=None,
            allow_replace=False,
        )
        request = TranslationRequest(
            job_id=result.job_id,
            source_text=result.text,
            source_language=self._config.translation.source_language,
            target_language=self._target_language,
            context_preset=self._context_preset,
            performance_mode=self._performance_mode,
            mode=RequestMode.REGION,
            foreground_hwnd=None,
        )
        logger.info(
            "OCR completed id=%s blocks=%s chars=%s; translation queued",
            result.job_id,
            len(result.blocks),
            len(result.text),
        )
        self._translation_worker.submit(request)

    def _restore_main_window_if_needed(self, pending: PendingJob) -> None:
        if pending.restore_main_window:
            pending.restore_main_window = False
            self._main_window.show_from_tray()

    def _begin_selection_job(
        self,
        mode: RequestMode,
        preferred_hwnd: int | None = None,
    ) -> None:
        job_id = uuid4().hex
        self._pending[job_id] = PendingJob(mode=mode)
        logger.info(
            "Selection job started id=%s mode=%s preferred_hwnd=%s",
            job_id,
            mode.value,
            preferred_hwnd,
        )
        self._input_worker.capture_selection(job_id, preferred_hwnd=preferred_hwnd)

    @Slot(object)
    def _on_selection(self, result: SelectionResult) -> None:
        pending = self._pending.get(result.job_id)
        if pending is None:
            return
        if result.error:
            self._pending.pop(result.job_id, None)
            self._show_error_dialog("Selection capture failed", result.error)
            return

        model = getattr(self._profile, "model", "unavailable")
        self._visible_job_id = result.job_id
        self._popup.show_processing(
            original=result.text,
            target_language=self._target_language,
            provider_name=self._profile_name,
            model=model,
            foreground_hwnd=result.foreground_hwnd,
        )

        request = TranslationRequest(
            job_id=result.job_id,
            source_text=result.text,
            source_language=self._config.translation.source_language,
            target_language=self._target_language,
            context_preset=self._context_preset,
            performance_mode=self._performance_mode,
            mode=pending.mode,
            foreground_hwnd=result.foreground_hwnd,
        )
        self._translation_worker.submit(request)

    @Slot(object)
    def _on_translation_progress(self, progress: TranslationProgress) -> None:
        pending = self._pending.get(progress.request.job_id)
        if pending is None:
            return
        if pending.quick:
            if progress.request.job_id == self._quick_visible_job_id:
                self._quick_popup.append_delta(progress.request.job_id, progress.delta_text)
            return
        if progress.request.job_id != self._visible_job_id:
            return
        self._popup.append_stream_delta(progress.delta_text)

    @Slot(object)
    def _on_translation(self, result: TranslationResult) -> None:
        self._main_window.refresh_trial_quota()
        self._main_window.refresh_microsoft_usage()
        job_id = result.request.job_id
        # Closed/canceled Quick UX jobs must NEVER be rerouted to legacy Replace.
        if job_id in self._quick_translation_ids:
            self._quick_translation_ids.discard(job_id)
            pending = self._pending.get(job_id)
            if pending is None or not pending.quick:
                return
            self._on_quick_translation(result, pending)
            return
        pending = self._pending.get(job_id)
        if result.error:
            self._pending.pop(result.request.job_id, None)
            if result.request.job_id == self._visible_job_id:
                self._visible_job_id = None
                self._popup.show_error(
                    original=result.request.source_text,
                    error_message=result.error,
                    log_path=self._log_path,
                    foreground_hwnd=result.request.foreground_hwnd,
                )
            else:
                self._tray.notify("Translation failed", result.error, 3500)
            return

        if result.request.mode == RequestMode.REPLACE:
            self._input_worker.paste_text(
                job_id=result.request.job_id,
                text=result.translated_text,
                foreground_hwnd=result.request.foreground_hwnd,
            )
            return

        self._popup.show_translation(
            original=result.request.source_text,
            translated=result.translated_text,
            target_language=result.request.target_language,
            cached=result.cached,
            foreground_hwnd=result.request.foreground_hwnd,
            allow_replace=result.request.mode != RequestMode.REGION,
        )
        self._pending.pop(result.request.job_id, None)
        if result.request.job_id == self._visible_job_id:
            self._visible_job_id = None

    @Slot(object)
    def _on_paste(self, result: PasteResult) -> None:
        self._quick_replace_cancel.pop(result.job_id, None)
        pending = self._pending.pop(result.job_id, None)
        # A Quick UX operation canceled by user must not trigger old legacy UI.
        if pending is None:
            return
        if pending is not None and pending.quick:
            self._quick_replace_text.pop(result.job_id, None)
            self._quick_popup.show_replace_feedback(
                "Đã thay thế văn bản được bôi đen." if result.success else
                f"Không thay thế được: {result.error or 'Unknown paste error'}",
                result.success,
            )
            return
        # Legacy hotkey/selection replace path.
        # Previous behavior remains unchanged.
        # (pending popped above).
        if result.job_id == self._visible_job_id:
            self._visible_job_id = None
        if result.success:
            self._tray.notify("Translation", "Translated text replaced the selected text.", 1800)
            self._popup.hide()
        else:
            self._show_error_dialog("Replace failed", result.error or "Unknown paste error")

    @Slot(str, object)
    def _on_popup_replace(self, translated_text: str, foreground_hwnd: object) -> None:
        job_id = uuid4().hex
        self._pending[job_id] = PendingJob(mode=RequestMode.REPLACE)
        hwnd = int(foreground_hwnd) if foreground_hwnd else None
        self._input_worker.paste_text(job_id, translated_text, hwnd)

    # ---------------------------------------------------------------- Quick UX
    @Slot(object)
    def _on_quick_mouse_candidate(self, candidate: MouseSelectionCandidate) -> None:
        if not self._config.quick_ux.auto_show_toolbar:
            return
        if self._region_selector.is_selecting():
            return
        if WindowService.is_own_process_window(candidate.hwnd):
            return
        self._quick_serial += 1
        self._quick_last_status = "Mouse gesture detected; reading UI Automation"
        self._quick_candidate = candidate
        self._quick_anchor = QCursor.pos()  # Qt logical screen coordinates, DPI-safe.
        self._quick_timer.start(self._config.quick_ux.selection_delay_ms)

    @Slot()
    def _on_quick_external_press(self) -> None:
        self._cancel_quick_replacements()
        self._quick_serial += 1
        self._quick_timer.stop()
        self._quick_toolbar.hide()
        if self._config.quick_ux.dismiss_popup_on_blur and not self._quick_popup.pinned:
            self._quick_popup.dismiss_if_unpinned()
            self._quick_visible_job_id = None
            self._quick_popup_snapshot = None
        # No clipboard or API activity for passive selection changes.

    def _inspect_quick_selection(self) -> None:
        candidate = self._quick_candidate
        if candidate is not None and self._config.quick_ux.auto_show_toolbar:
            self._quick_selection_worker.probe(
                self._quick_serial, candidate.hwnd, candidate.x, candidate.y
            )

    @Slot(object)
    def _on_quick_probe(self, result: QuickSelectionProbe) -> None:
        if result.serial != self._quick_serial or not self._config.quick_ux.auto_show_toolbar:
            return
        self._quick_snapshot = result.snapshot
        if result.snapshot is None:
            self._quick_last_status = result.status or "UIA could not read selected text from the target application"
            logger.info("Quick UX UI Automation did not expose selected text; toolbar not shown (%s)",
                        self._quick_last_status)
            self._quick_toolbar.hide()
            return
        self._quick_last_status = f"UIA read selection successfully ({len(result.snapshot.text)} characters)"
        self._quick_toolbar.set_config(self._config.quick_ux)
        self._quick_toolbar.show_at(self._quick_anchor)
        logger.debug("Quick UX toolbar shown (selection characters=%d)", len(result.snapshot.text))

    @Slot()
    def _on_quick_escape(self) -> None:
        if not self._quick_toolbar.isVisible() and not self._quick_popup.isVisible():
            return
        self._cancel_quick_replacements()
        self._quick_serial += 1
        self._quick_timer.stop()
        self._quick_toolbar.hide()
        self._quick_popup.force_close()
        self._quick_visible_job_id = None
        self._quick_popup_snapshot = None

    @Slot(str)
    def _on_quick_error(self, error: str) -> None:
        self._quick_last_status = f"Mouse/UIA error: {error}"
        logger.warning("Quick UX auto-selection unavailable: %s", error)
        self._tray.notify("Quick Toolbar", "Auto-select không khả dụng. Alt+T vẫn hoạt động.", 3500)

    @Slot(str)
    def _translate_quick_selection(self, language: str) -> None:
        self._begin_quick_translation(language, mode=RequestMode.POPUP)

    def _begin_quick_translation(self, language: str, *, mode: RequestMode) -> None:
        self._cancel_quick_replacements()
        snapshot = self._quick_snapshot
        if snapshot is None or not snapshot.text:
            self._quick_toolbar.hide()
            return
        if WindowService.get_foreground_window() != snapshot.hwnd:
            self._quick_toolbar.hide()
            self._tray.notify("Quick UX", "Vùng chọn không còn được focus. Hãy chọn lại chữ.", 2600)
            return
        if mode == RequestMode.REPLACE and not snapshot.replace_allowed:
            self._quick_toolbar.hide()
            self._tray.notify("Quick UX", "Trường hiện tại chỉ đọc, không thể thay thế.", 2600)
            return
        job_id = uuid4().hex
        self._pending[job_id] = PendingJob(mode=mode, quick=True, quick_snapshot=snapshot)
        self._quick_translation_ids.add(job_id)
        self._quick_visible_job_id = job_id
        self._quick_popup_snapshot = snapshot
        anchor = self._quick_anchor
        self._quick_toolbar.hide()
        google = self._profile is not None and self._profile.type in {"google_translate_web", "google_cloud_translate", "microsoft_translator"}
        self._quick_popup.start(
            job_id, snapshot.text, language,
            "Dịch trực tiếp" if google else self._context_preset,
            "Không dùng prompt / tốc độ AI" if google else self._performance_mode,
            self._profile_name, getattr(self._profile, "model", "unavailable"), anchor,
            replace_allowed=snapshot.replace_allowed,
        )
        request = TranslationRequest(
            job_id=job_id,
            source_text=snapshot.text,
            source_language=self._config.translation.source_language,
            target_language=language,
            context_preset=self._context_preset,
            performance_mode=self._performance_mode,
            mode=mode,
            foreground_hwnd=snapshot.hwnd,
        )
        self._translation_worker.submit(request)
        logger.info("Quick UX translation requested id=%s target=%s mode=%s", job_id, language, mode.value)

    def _on_quick_translation(self, result: TranslationResult, pending: PendingJob) -> None:
        job_id = result.request.job_id
        # Protect current popup/replacement from old asynchronous results.
        if job_id != self._quick_visible_job_id:
            self._pending.pop(job_id, None)
            return
        if result.error:
            self._pending.pop(job_id, None)
            self._quick_popup.fail(job_id, result.error)
            return
        self._quick_popup.finish(job_id, result.translated_text, result.cached)
        if pending.mode == RequestMode.REPLACE:
            self._schedule_quick_replace(job_id, result.translated_text, pending.quick_snapshot)
        else:
            self._pending.pop(job_id, None)

    @Slot(str)
    def _on_quick_popup_replace(self, translated_text: str) -> None:
        snapshot = self._quick_popup_snapshot
        if snapshot is None or not snapshot.replace_allowed:
            self._quick_popup.show_replace_feedback("Không có vùng chọn hợp lệ để thay thế.", False)
            return
        job_id = uuid4().hex
        self._pending[job_id] = PendingJob(mode=RequestMode.REPLACE, quick=True, quick_snapshot=snapshot)
        self._schedule_quick_replace(job_id, translated_text, snapshot)

    def _cancel_quick_replacements(self) -> None:
        """Invalidate all uncommitted Quick UX replace attempts on dismissal.

        Translation callbacks are tombstoned separately until their HTTP result
        returns, so canceled REPLACE requests cannot fall into legacy paste.
        """
        for event in self._quick_replace_cancel.values():
            event.set()
        for job_id, pending in list(self._pending.items()):
            if pending.quick and pending.mode == RequestMode.REPLACE:
                self._pending.pop(job_id, None)
                self._quick_replace_text.pop(job_id, None)
        self._quick_replace_cancel.clear()

    @Slot()
    def _on_quick_popup_closed(self) -> None:
        self._cancel_quick_replacements()
        self._quick_visible_job_id = None
        self._quick_popup_snapshot = None

    def _schedule_quick_replace(
        self, job_id: str, translated_text: str, snapshot: SelectionSnapshot | None
    ) -> None:
        if snapshot is None or not snapshot.replace_allowed:
            self._pending.pop(job_id, None)
            self._quick_popup.show_replace_feedback("Không thể xác minh nguồn để thay thế.", False)
            return
        self._quick_replace_text[job_id] = translated_text
        self._quick_replace_cancel[job_id] = threading.Event()
        self._quick_selection_worker.verify(job_id, snapshot)

    @Slot(object)
    def _on_quick_check(self, result: QuickSelectionCheck) -> None:
        pending = self._pending.get(result.job_id)
        text = self._quick_replace_text.pop(result.job_id, None)
        if pending is None or not pending.quick or text is None:
            return
        if not result.valid:
            self._quick_replace_cancel.pop(result.job_id, None)
            self._pending.pop(result.job_id, None)
            self._quick_popup.show_replace_feedback(result.reason, False)
            return
        snapshot = pending.quick_snapshot
        if snapshot is None or WindowService.get_foreground_window() != snapshot.hwnd:
            self._quick_replace_cancel.pop(result.job_id, None)
            self._pending.pop(result.job_id, None)
            self._quick_popup.show_replace_feedback("Đã chuyển cửa sổ. Hủy dán để tránh thay nhầm.", False)
            return
        self._input_worker.paste_text(
            result.job_id, text, snapshot.hwnd,
            expected_selected_text=snapshot.text,
            cancel_event=self._quick_replace_cancel.get(result.job_id),
        )

    @Slot(object)
    def _save_quick_ux_settings(self, raw: object) -> None:
        try:
            if not isinstance(raw, dict):
                raise ValueError("Quick UX settings must be a JSON object")
            new_section = parse_quick_ux_section(raw)
            self._config_store.replace_section("quick_ux", new_section.as_json())
        except Exception as exc:
            logger.exception("Saving Quick UX settings failed")
            self._show_error_dialog("Quick UX", str(exc))
            self._main_window.set_quick_ux_settings(self._config.quick_ux)
            self._tray.set_quick_auto_enabled(self._config.quick_ux.auto_show_toolbar)
            return
        self._apply_quick_ux(new_section)
        self._tray.notify("Quick UX", "Đã lưu và áp dụng Quick Toolbar.", 1800)

    @Slot(object)
    def _save_hotkey_settings(self, raw: object) -> None:
        try:
            new_section = parse_hotkey_section(raw)
            self._config_store.replace_section("hotkeys", new_section.as_json())
        except Exception as exc:
            logger.exception("Saving hotkey settings failed")
            self._show_error_dialog("Hotkey", str(exc))
            self._main_window.set_hotkey_settings(self._config.hotkeys)
            return
        if not self._reload_config_internal():
            self._main_window.set_hotkey_settings(self._config.hotkeys)
            return
        self._tray.notify("Hotkey", "Đã lưu và đăng ký lại hotkey.", 1800)

    def _apply_quick_ux(self, section: QuickUxSection) -> None:
        self._config = replace(self._config, quick_ux=section)
        self._mouse_selection_monitor.set_enabled(section.auto_show_toolbar)
        self._quick_selection_worker.update_max_characters(section.max_selection_chars)
        self._quick_toolbar.set_config(section)
        self._quick_popup.set_config(section)
        self._main_window.set_quick_ux_settings(section)
        self._tray.set_quick_auto_enabled(section.auto_show_toolbar)
        if not section.auto_show_toolbar:
            self._quick_serial += 1
            self._quick_timer.stop()
            self._quick_toolbar.hide()

    def _set_quick_auto_enabled(self, enabled: bool) -> None:
        values = self._config.quick_ux.as_json()
        values["auto_show_toolbar"] = bool(enabled)
        self._save_quick_ux_settings(values)

    def _set_target_language(self, language: str) -> None:
        if language not in TRAY_TARGET_LANGUAGE_CODES:
            self._show_error_dialog("Unsupported target language", language)
            self._tray.set_target_language(self._target_language)
            return

        self._target_language = language
        self._runtime_settings.update(target_language=language)
        self._refresh_tray_state()
        self._tray.notify("Ngôn ngữ đích", f"Đã chuyển sang: {language}", 1800)
        logger.info("Target language changed to %s", language)

    def _set_provider_profile(self, profile_name: str) -> None:
        old_name = self._profile_name
        try:
            new_name, new_profile = resolve_provider_profile(self._config, profile_name)
            new_provider = create_translation_provider(self._config, new_name)
        except Exception as exc:
            logger.exception("Cannot switch provider profile to %s", profile_name)
            self._tray.set_provider(old_name)
            self._show_error_dialog("Provider switch failed", str(exc))
            return

        self._translation_worker.replace_provider(new_provider)
        self._profile_name = new_name
        self._profile = new_profile
        self._startup_provider_error = None
        self._runtime_settings.update(provider_profile=new_name)
        self._refresh_tray_state()
        self._tray.notify(
            "API / Model",
            f"Đã chuyển sang {new_name} | {new_profile.model}",
            2200,
        )
        logger.info(
            "Provider selection changed to profile=%s model=%s",
            new_name,
            new_profile.model,
        )

    def _set_performance_mode(self, mode: str) -> None:
        normalized = mode.strip().lower()
        if normalized not in {"ultra_fast", "fast", "quality"}:
            self._show_error_dialog("Unsupported performance mode", mode)
            self._tray.set_performance_mode(self._performance_mode)
            return

        self._performance_mode = normalized
        self._runtime_settings.update(performance_mode=normalized)
        self._refresh_tray_state()
        labels = {
            "ultra_fast": "Cực nhanh",
            "fast": "Nhanh",
            "quality": "Chuẩn",
        }
        self._tray.notify(
            "Tốc độ dịch",
            f"Đã chuyển sang chế độ: {labels[normalized]}",
            1800,
        )
        logger.info("Translation performance mode changed to %s", normalized)

    def _set_context_preset(self, preset: str) -> None:
        normalized = preset.strip().lower()
        if normalized not in {"engineering", "chat", "email"}:
            self._show_error_dialog("Unsupported translation style", preset)
            self._tray.set_context_preset(self._context_preset)
            return

        self._context_preset = normalized
        self._runtime_settings.update(context_preset=normalized)
        self._refresh_tray_state()
        labels = {
            "engineering": "Engineer - kỹ thuật",
            "chat": "Chat - hội thoại",
            "email": "Email - công việc",
        }
        self._tray.notify("Kiểu dịch", f"Đã chuyển sang: {labels[normalized]}", 1800)
        logger.info("Translation context preset changed to %s", normalized)

    def _set_cache_enabled(self, enabled: bool) -> None:
        requested = bool(enabled)
        old_value = self._cache_enabled
        if requested == old_value:
            return

        try:
            self._cache.set_enabled(requested)
            self._config_store.update_nested(("translation", "cache_enabled"), requested)
        except Exception as exc:
            logger.exception("Cannot change cache setting to %s", requested)
            try:
                self._cache.set_enabled(old_value)
            except Exception:
                logger.exception("Failed to restore previous cache state")
            self._tray.set_cache_enabled(old_value)
            self._show_error_dialog("Cache setting failed", str(exc))
            return

        self._cache_enabled = requested
        self._refresh_tray_state()
        state = "BẬT" if requested else "TẮT"
        self._tray.notify(
            "Cache bản dịch",
            f"Cache đã {state}. Thiết lập đã lưu vào config.json.",
            2200,
        )
        logger.info("Translation cache enabled changed to %s", requested)

    @Slot(object, str)
    def _save_provider_configuration(
        self,
        raw_profiles: object,
        active_profile: str,
    ) -> None:
        if not isinstance(raw_profiles, dict) or not raw_profiles:
            self._show_error_dialog("Provider configuration", "Phải có ít nhất một provider.")
            return
        try:
            parsed_profiles = {
                str(name): provider_profile_from_dict(dict(values))
                for name, values in raw_profiles.items()
                if isinstance(values, dict)
            }
            if not parsed_profiles:
                raise ValueError("Phải có ít nhất một provider hợp lệ.")
            if active_profile not in parsed_profiles:
                raise ValueError(f"Active provider '{active_profile}' không tồn tại.")

            candidate = replace(
                self._config,
                providers=ProviderSection(
                    active_profile=active_profile,
                    profiles=parsed_profiles,
                ),
            )
            # Provider construction validates model/base URL/key configuration
            # before we overwrite config.json. It does not make a network request.
            validation_provider = create_translation_provider(candidate, active_profile)
            close = getattr(validation_provider, "close", None)
            if callable(close):
                close()

            # providers.json is the portable source of truth for connection data.
            # It intentionally contains only: base_url, api_key, models.
            portable_catalog = {
                name: portable_provider_entry(profile)
                for name, profile in parsed_profiles.items()
            }
            self._provider_catalog_store.replace_all(portable_catalog)

            # config.json keeps only app-specific provider behavior.
            provider_json = {
                "catalog_path": self._config.providers.catalog_path,
                "active_profile": active_profile,
                "profile_overrides": {
                    name: profile_override_entry(profile)
                    for name, profile in parsed_profiles.items()
                },
            }
            self._config_store.replace_section("providers", provider_json)
        except Exception as exc:
            logger.exception("Saving provider configuration failed")
            self._show_error_dialog("Lưu provider thất bại", str(exc))
            return

        self._runtime_settings.update(provider_profile=active_profile)
        if not self._reload_config_internal(preferred_profile=active_profile):
            return
        self._tray.notify(
            "Provider & Model",
            f"Đã lưu và áp dụng {active_profile} | {self._profile.model}",
            2600,
        )
        logger.info("Provider configuration saved from desktop manager")

    @Slot(str, str, str)
    def _save_prompt_override(self, performance_mode: str, context_preset: str, template: str) -> None:
        try:
            validate_prompt_template(template)
            self._prompt_catalog_store.set_override(performance_mode, context_preset, template)
            self._prompt_overrides = self._prompt_catalog_store.read_overrides()
            self._translation_worker.reload_prompts(self._prompt_overrides)
            self._main_window.set_prompt_overrides(self._prompt_overrides)
            self._tray.notify(
                "Prompt Editor",
                f"Đã lưu prompt tùy chỉnh: {performance_mode} / {context_preset}",
                2400,
            )
            logger.info("Custom prompt saved mode=%s style=%s", performance_mode, context_preset)
        except Exception as exc:
            logger.exception("Saving custom prompt failed")
            self._show_error_dialog("Lưu prompt thất bại", str(exc))

    @Slot(str, str)
    def _reset_prompt_override(self, performance_mode: str, context_preset: str) -> None:
        try:
            self._prompt_catalog_store.reset_override(performance_mode, context_preset)
            self._prompt_overrides = self._prompt_catalog_store.read_overrides()
            self._translation_worker.reload_prompts(self._prompt_overrides)
            self._main_window.set_prompt_overrides(self._prompt_overrides)
            self._tray.notify(
                "Prompt Editor",
                f"Đã reset về mặc định: {performance_mode} / {context_preset}",
                2200,
            )
            logger.info("Prompt reset mode=%s style=%s", performance_mode, context_preset)
        except Exception as exc:
            logger.exception("Reset prompt failed")
            self._show_error_dialog("Reset prompt thất bại", str(exc))

    @Slot()
    def _reset_all_prompt_overrides(self) -> None:
        try:
            self._prompt_catalog_store.reset_all()
            self._prompt_overrides = {}
            self._translation_worker.reload_prompts(self._prompt_overrides)
            self._main_window.set_prompt_overrides(self._prompt_overrides)
            self._tray.notify("Prompt Editor", "Đã reset toàn bộ prompt về mặc định.", 2400)
            logger.info("All custom prompts reset")
        except Exception as exc:
            logger.exception("Reset all prompts failed")
            self._show_error_dialog("Reset prompt thất bại", str(exc))

    @Slot(str, object)
    def _test_provider_configuration(self, profile_name: str, raw_profile: object) -> None:
        if not isinstance(raw_profile, dict):
            self._main_window.show_provider_test_result(False, "Profile không hợp lệ.")
            return
        self._main_window.set_provider_test_busy(True)
        threading.Thread(
            target=self._run_provider_test,
            args=(profile_name, dict(raw_profile)),
            name="ProviderTestWorker",
            daemon=True,
        ).start()

    def _run_provider_test(self, profile_name: str, raw_profile: dict[str, object]) -> None:
        provider = None
        started = time.perf_counter()
        try:
            profile = provider_profile_from_dict(raw_profile)
            candidate = replace(
                self._config,
                providers=ProviderSection(
                    active_profile=profile_name,
                    profiles={profile_name: profile},
                ),
            )
            provider = create_translation_provider(candidate, profile_name)
            request = TranslationRequest(
                job_id="provider-test",
                source_text="Hello",
                source_language="en",
                target_language="vi",
                context_preset="chat",
                performance_mode="ultra_fast",
                mode=RequestMode.POPUP,
                foreground_hwnd=None,
            )
            response = provider.translate(request, "Translate from English to Vietnamese. Return only the translation.")
            elapsed = time.perf_counter() - started
            self._bridge.provider_test_result.emit(
                {
                    "success": True,
                    "profile": profile_name,
                    "model": profile.model,
                    "elapsed": elapsed,
                    "response": response[:200],
                }
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self._bridge.provider_test_result.emit(
                {
                    "success": False,
                    "profile": profile_name,
                    "elapsed": elapsed,
                    "error": str(exc),
                }
            )
        finally:
            if provider is not None:
                close = getattr(provider, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        logger.exception("Failed to close provider test client")

    @Slot(object)
    def _on_provider_test_result(self, result: object) -> None:
        self._main_window.refresh_trial_quota()
        self._main_window.refresh_microsoft_usage()
        if not isinstance(result, dict):
            self._main_window.show_provider_test_result(False, "Kết quả test không hợp lệ.")
            return
        success = bool(result.get("success"))
        elapsed = float(result.get("elapsed", 0.0))
        if success:
            text = (
                f"OK | {result.get('profile')} | {result.get('model')} | "
                f"{elapsed:.2f}s | response: {result.get('response', '')}"
            )
        else:
            text = f"FAIL | {result.get('profile')} | {elapsed:.2f}s | {result.get('error', '')}"
        self._main_window.show_provider_test_result(success, text)

    @Slot(str)
    def _import_provider_catalog(self, source_path: str) -> None:
        try:
            incoming = ProviderCatalogStore(Path(source_path)).read()
            if not incoming:
                raise ValueError("File provider import không có provider hợp lệ.")
            self._provider_catalog_store.replace_all(incoming)
        except Exception as exc:
            logger.exception("Import providers failed")
            self._show_error_dialog("Import providers thất bại", str(exc))
            return
        self._reload_config_internal()
        self._tray.notify("Provider & Model", f"Đã import {len(incoming)} provider.", 2600)

    @Slot(str)
    def _export_provider_catalog(self, destination_path: str) -> None:
        try:
            data = self._provider_catalog_store.read()
            if not data:
                raise ValueError("Không có provider để export.")
            ProviderCatalogStore(Path(destination_path)).replace_all(data)
        except Exception as exc:
            logger.exception("Export providers failed")
            self._show_error_dialog("Export providers thất bại", str(exc))
            return
        self._tray.notify("Provider & Model", f"Đã export providers.json tới {destination_path}", 2600)

    def _effective_streaming(self) -> tuple[bool, str]:
        global_value = self._config.translation.streaming_enabled_for(self._performance_mode)
        if self._profile is None:
            return global_value, "global"
        if self._profile.type in {"google_translate_web", "google_cloud_translate", "microsoft_translator"}:
            return False, "provider"
        override = self._profile.streaming_override_for(self._performance_mode)
        if override is None:
            return global_value, "global"
        return bool(override), "profile"

    def _reload_config(self) -> None:
        self._reload_config_internal()

    def _reload_config_internal(self, preferred_profile: str | None = None) -> bool:
        """Reload runtime-safe configuration without restarting the application.

        Applied live: provider definitions, current provider config/model/base URL,
        translation/streaming settings, cache flag, hotkeys, clipboard timing,
        OCR engine/settings and Region Translate feature state.
        Main-window geometry and app/data/log paths still require a restart.
        """
        try:
            env_path = resolve_config_path().parent / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=True)
            new_config = AppConfig.load()

            # Save & Apply from the desktop manager may explicitly request a new
            # active profile. A plain Reload keeps the current runtime provider
            # when it still exists, matching previous behavior.
            if preferred_profile and preferred_profile in new_config.providers.profiles:
                new_profile_name = preferred_profile
            elif self._profile_name in new_config.providers.profiles:
                new_profile_name = self._profile_name
            else:
                new_profile_name = new_config.providers.active_profile

            new_profile_name, new_profile = resolve_provider_profile(
                new_config, new_profile_name
            )
            new_provider = create_translation_provider(new_config, new_profile_name)
            new_prompt_store = PromptCatalogStore(
                resolve_prompt_catalog_path(
                    new_config.translation.prompt_catalog_path,
                    config_path=resolve_config_path(),
                )
            )
            new_prompt_overrides = new_prompt_store.read_overrides()
            new_input_service = ClipboardSelectionService(
                new_config.clipboard, new_config.hotkeys
            )
            new_ocr_engine = create_ocr_engine(new_config.ocr)
        except Exception as exc:
            logger.exception("Config reload validation failed")
            self._show_error_dialog("Reload config failed", str(exc))
            return False

        # Cache flag is config-authoritative and should reflect edits immediately.
        try:
            self._cache.set_enabled(new_config.translation.cache_enabled)
        except Exception as exc:
            logger.exception("Config reload failed while applying cache setting")
            try:
                close = getattr(new_provider, "close", None)
                if callable(close):
                    close()
                new_ocr_engine.close()
            except Exception:
                logger.exception("Failed to close newly-created runtime resources after reload failure")
            self._show_error_dialog("Reload config failed", str(exc))
            return False

        old_hotkey_config = self._config.hotkeys
        self._config = new_config
        self._provider_catalog_store = ProviderCatalogStore(
            resolve_provider_catalog_path(
                new_config.providers.catalog_path, config_path=resolve_config_path()
            )
        )
        self._prompt_catalog_store = new_prompt_store
        self._prompt_overrides = new_prompt_overrides
        self._profile_name = new_profile_name
        self._profile = new_profile
        self._cache_enabled = bool(new_config.translation.cache_enabled)
        self._startup_provider_error = None

        # Queue runtime changes behind any translation/input work already in flight.
        self._translation_worker.reload_runtime(
            new_provider, new_config.translation, new_prompt_overrides
        )
        self._input_worker.replace_service(new_input_service)
        self._ocr_worker.replace_engine(new_ocr_engine)
        self._region_selector.update_config(new_config.ui)
        self._apply_quick_ux(new_config.quick_ux)

        # Re-register hotkeys only when their config changed.
        if new_config.hotkeys != old_hotkey_config:
            self._hotkeys.stop()
            self._hotkeys = HotkeyService(
                new_config.hotkeys,
                self._bridge.hotkey.emit,
                on_ready=self._bridge.hotkey_ready.emit,
                on_error=self._bridge.hotkey_error.emit,
                on_escape=self._bridge.quick_escape.emit,
            )
            self._hotkeys.start()

        if self._runtime_settings.load().get("provider_profile") != new_profile_name:
            self._runtime_settings.update(provider_profile=new_profile_name)

        self._refresh_tray_state()
        streaming, source = self._effective_streaming()
        self._tray.notify(
            "Reload cấu hình",
            f"Đã cập nhật | {new_profile_name} | {new_profile.model} | "
            f"stream={'on' if streaming else 'off'} ({source}) | "
            f"cache={'on' if self._cache_enabled else 'off'}",
            3200,
        )
        logger.info(
            "Config reloaded profile=%s model=%s streaming=%s source=%s cache=%s",
            new_profile_name,
            new_profile.model,
            streaming,
            source,
            self._cache_enabled,
        )
        self._main_window.load_config(
            self._config,
            active_profile=self._profile_name,
            target_language=self._target_language,
            context_preset=self._context_preset,
            performance_mode=self._performance_mode,
            cache_enabled=self._cache_enabled,
            prompt_overrides=self._prompt_overrides,
        )
        return True

    def _refresh_tray_state(self) -> None:
        streaming, source = self._effective_streaming()
        self._tray.set_region_translate_enabled(self._config.features.region_translate_enabled)
        self._tray.set_quick_auto_enabled(self._config.quick_ux.auto_show_toolbar)
        self._tray.update_state(
            target_language=self._target_language,
            provider_name=self._profile_name,
            provider_profiles=self._config.providers.profiles,
            performance_mode=self._performance_mode,
            context_preset=self._context_preset,
            cache_enabled=self._cache_enabled,
            streaming_enabled=streaming,
            streaming_source=source,
        )
        self._main_window.update_runtime_state(
            active_profile=self._profile_name,
            profiles=self._config.providers.profiles,
            target_language=self._target_language,
            context_preset=self._context_preset,
            performance_mode=self._performance_mode,
            cache_enabled=self._cache_enabled,
        )

    def _show_error_dialog(self, title: str, message: str) -> None:
        logger.error("%s: %s", title, message)
        box = QMessageBox(self._main_window)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle(title)
        box.setText(message)
        box.setDetailedText(f"Log file: {self._log_path}")
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.exec()

    def _show_diagnostics(self) -> None:
        if self._profile is None:
            details = f"Active profile: {self._profile_name}\nProvider configuration is invalid."
        else:
            direct_key = str(getattr(self._profile, "api_key", "") or "")
            api_env = getattr(self._profile, "api_key_env", "")
            env_value = os.getenv(api_env, "") if api_env else ""
            api_value = direct_key or env_value
            if direct_key:
                key_state = f"set directly in config ({len(direct_key)} chars)"
            elif not api_env:
                key_state = "not required/empty env name"
            elif not api_value:
                key_state = f"MISSING ({api_env})"
            elif api_value.lower().startswith("replace_me"):
                key_state = f"PLACEHOLDER ({api_env})"
            else:
                key_state = f"set ({api_env}, {len(api_value)} chars)"
            effective_streaming, streaming_source = self._effective_streaming()
            details = (
                f"Active profile: {self._profile_name}\n"
                f"Type: {self._profile.type}\n"
                f"Base URL: {self._profile.base_url}\n"
                f"Model: {self._profile.model}\n"
                f"Endpoint mode: {self._profile.endpoint_mode}\n"
                f"API key: {key_state}\n"
                f"Target language: {self._target_language}\n"
                f"Translation style: {self._context_preset}\n"
                f"Performance mode: {self._performance_mode}\n"
                f"Streaming effective: {effective_streaming} ({streaming_source})\n"
                f"Streaming global config: {self._config.translation.streaming}\n"
                f"Streaming profile override: {self._profile.streaming_override}\n"
                f"Cache enabled: {self._cache_enabled}\n"
                f"Config path: {self._config_store.path}\n"
                f"Provider catalog: {self._provider_catalog_store.path}\n"
                f"Prompt catalog: {self._prompt_catalog_store.path}\n"
                f"Prompt current: {'custom' if prompt_is_custom(self._performance_mode, self._context_preset, self._prompt_overrides) else 'default'}\n"
                f"OCR engine: {self._config.ocr.engine} (min_confidence={self._config.ocr.min_confidence})\n"
                f"Region enabled: {self._config.features.region_translate_enabled}\n"
                f"Region hotkey: {self._config.hotkeys.region_translate}\n"
                f"Quick Toolbar: {self._config.quick_ux.auto_show_toolbar} (delay={self._config.quick_ux.selection_delay_ms}ms)\n"
                f"Quick UX mouse hook running: {self._mouse_selection_monitor.is_running()}\n"
                f"Quick UX last probe: {self._quick_last_status}\n"
                f"Hotkey: {self._config.hotkeys.translate_selection}\n"
                f"Suppress hotkey: {self._config.hotkeys.suppress_hotkeys}\n"
                f"Runtime settings: {self._config.data_dir / 'runtime_settings.json'}\n"
                f"Log: {self._log_path}"
            )

        box = QMessageBox(self._main_window)
        box.setWindowTitle("AI Screen Translator - Diagnostics")
        box.setIcon(QMessageBox.Information)
        box.setText(details)
        box.exec()
