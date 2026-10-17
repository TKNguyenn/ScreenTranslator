from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = application_root()

DEFAULT_ENDPOINT_PATHS = {
    "responses": "/responses",
    "chat_completions": "/chat/completions",
    "completions": "/completions",
}
DEFAULT_AUTO_ORDER = ("responses", "chat_completions", "completions")
DEFAULT_PROVIDER_CATALOG = "providers.json"
DEFAULT_PROMPT_CATALOG = "prompts.json"


@dataclass(frozen=True)
class AppSection:
    name: str = "AI Screen Translator"
    data_dir: str = "data"
    log_level: str = "INFO"


@dataclass(frozen=True)
class HotkeySection:
    translate_selection: str = "alt+t"
    translate_and_replace: str = "alt+shift+t"
    live_toggle: str = "alt+l"
    region_translate: str = "alt+s"
    target_vi: str = "alt+1"
    target_en: str = "alt+2"
    target_zh_hant: str = "alt+3"
    release_delay_ms: int = 60
    suppress_hotkeys: bool = True

    def as_json(self) -> dict[str, Any]:
        return {
            "translate_selection": self.translate_selection,
            "translate_and_replace": self.translate_and_replace,
            "live_toggle": self.live_toggle,
            "region_translate": self.region_translate,
            "target_vi": self.target_vi,
            "target_en": self.target_en,
            "target_zh_hant": self.target_zh_hant,
            "release_delay_ms": self.release_delay_ms,
            "suppress_hotkeys": self.suppress_hotkeys,
        }


def parse_hotkey_section(raw: Any) -> HotkeySection:
    """Validate hotkeys before they are written or registered globally."""
    if not isinstance(raw, dict):
        raise ValueError("hotkeys must be an object")
    defaults = HotkeySection()
    names = (
        "translate_selection", "translate_and_replace", "live_toggle",
        "region_translate", "target_vi", "target_en", "target_zh_hant",
    )
    values: dict[str, str] = {}
    for name in names:
        value = str(raw.get(name, getattr(defaults, name))).strip().lower().replace(" ", "")
        if not value:
            raise ValueError(f"hotkeys.{name} cannot be empty")
        values[name] = value
    if len(set(values.values())) != len(values):
        raise ValueError("Mỗi hotkey phải khác nhau để tránh đăng ký nhầm hành động.")
    delay = raw.get("release_delay_ms", defaults.release_delay_ms)
    if isinstance(delay, bool) or not isinstance(delay, int) or not 0 <= delay <= 1000:
        raise ValueError("hotkeys.release_delay_ms must be an integer from 0 to 1000")
    suppress = raw.get("suppress_hotkeys", defaults.suppress_hotkeys)
    if not isinstance(suppress, bool):
        raise ValueError("hotkeys.suppress_hotkeys must be true/false")
    return HotkeySection(**values, release_delay_ms=delay, suppress_hotkeys=suppress)


@dataclass(frozen=True)
class ClipboardSection:
    copy_timeout_ms: int = 900
    copy_poll_ms: int = 10
    paste_restore_delay_ms: int = 350


@dataclass(frozen=True)
class TranslationSection:
    source_language: str = "auto"
    target_language: str = "vi"
    context_preset: str = "engineering"
    prompt_version: str = "v4"
    cache_enabled: bool = True
    performance_mode: str = "fast"
    prompt_catalog_path: str = DEFAULT_PROMPT_CATALOG
    streaming: dict[str, bool] = field(
        default_factory=lambda: {
            "ultra_fast": True,
            "fast": False,
            "quality": False,
        }
    )

    def streaming_enabled_for(self, performance_mode: str) -> bool:
        mode = str(performance_mode).strip().lower()
        return bool(self.streaming.get(mode, False))


@dataclass(frozen=True)
class ProviderProfile:
    """Resolved runtime provider profile.

    Portable connection data comes from providers.json. App-specific behavior
    (endpoint mode, streaming override, active model, timeouts, etc.) comes from
    config.json profile_overrides. The two sources are merged at load time.
    """

    type: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    api_key_env: str = ""
    allow_no_api_key: bool = False
    model: str = ""
    models: tuple[str, ...] = ()
    endpoint_mode: str = "auto"
    endpoint_paths: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ENDPOINT_PATHS))
    auto_order: tuple[str, ...] = DEFAULT_AUTO_ORDER
    timeout_s: float = 45.0
    connect_timeout_s: float = 10.0
    verify_ssl: bool = True
    temperature: float | None = None
    max_output_tokens: int | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)
    endpoint_extra_body: dict[str, dict[str, Any]] = field(default_factory=dict)
    streaming_override: dict[str, bool] = field(default_factory=dict)

    def streaming_override_for(self, performance_mode: str) -> bool | None:
        mode = str(performance_mode).strip().lower()
        if mode not in self.streaming_override:
            return None
        return bool(self.streaming_override[mode])

    def available_models(self) -> tuple[str, ...]:
        values: list[str] = []
        for item in (*self.models, self.model):
            value = str(item).strip()
            if value and value not in values:
                values.append(value)
        return tuple(values)


@dataclass(frozen=True)
class ProviderSection:
    active_profile: str = "mock"
    catalog_path: str = DEFAULT_PROVIDER_CATALOG
    profile_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    profiles: dict[str, ProviderProfile] = field(
        default_factory=lambda: {
            "mock": ProviderProfile(
                type="mock", model="mock-v2", models=("mock-v2",), allow_no_api_key=True
            )
        }
    )

    def active(self) -> tuple[str, ProviderProfile]:
        profile = self.profiles.get(self.active_profile)
        if profile is None:
            available = ", ".join(sorted(self.profiles)) or "<none>"
            raise ValueError(
                f"Provider profile '{self.active_profile}' does not exist. Available: {available}"
            )
        return self.active_profile, profile


@dataclass(frozen=True)
class OcrSection:
    """Local OCR settings used by Region Translate.

    ``rapidocr`` is the default local engine. It is loaded lazily by the OCR
    worker so app startup stays fast and provider-only workflows still start
    even if the optional OCR runtime has a problem.
    """

    engine: str = "rapidocr"
    min_confidence: float = 0.45


@dataclass(frozen=True)
class UiSection:
    popup_width: int = 620
    popup_height: int = 430
    popup_offset_x: int = 16
    popup_offset_y: int = 18
    main_width: int = 1040
    main_height: int = 720
    region_capture_delay_ms: int = 140
    region_min_size_px: int = 12
    region_overlay_opacity: int = 120


@dataclass(frozen=True)
class QuickUxSection:
    """Opt-out auto-selection toolbar. No API calls occur until a toolbar action."""

    auto_show_toolbar: bool = True
    selection_delay_ms: int = 250
    languages: tuple[str, ...] = ("vi", "en", "zh-Hant")
    dismiss_popup_on_blur: bool = True
    toolbar_timeout_ms: int = 8000
    max_selection_chars: int = 6000

    def as_json(self) -> dict[str, Any]:
        return {
            "auto_show_toolbar": self.auto_show_toolbar,
            "selection_delay_ms": self.selection_delay_ms,
            "languages": list(self.languages),
            "dismiss_popup_on_blur": self.dismiss_popup_on_blur,
            "toolbar_timeout_ms": self.toolbar_timeout_ms,
            "max_selection_chars": self.max_selection_chars,
        }


def parse_quick_ux_section(raw: Any) -> QuickUxSection:
    """Validate GUI/JSON input before persisting a Quick UX configuration."""
    if not isinstance(raw, dict):
        raise ValueError("quick_ux must be an object")
    allowed = {"vi", "en", "zh-Hant"}
    raw_languages = raw.get("languages", ["vi", "en", "zh-Hant"])
    if not isinstance(raw_languages, (tuple, list)):
        raise ValueError("quick_ux.languages must be an array")
    languages = tuple(dict.fromkeys(str(item) for item in raw_languages))
    if not languages or any(item not in allowed for item in languages):
        raise ValueError("quick_ux.languages must contain vi, en, or zh-Hant (at least one)")
    auto_show = raw.get("auto_show_toolbar", True)
    dismiss = raw.get("dismiss_popup_on_blur", True)
    if not isinstance(auto_show, bool) or not isinstance(dismiss, bool):
        raise ValueError("quick_ux toggle values must be true/false")

    def bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
        value = raw.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"quick_ux.{name} must be an integer from {minimum} to {maximum}")
        return value

    return QuickUxSection(
        auto_show_toolbar=auto_show,
        selection_delay_ms=bounded_int("selection_delay_ms", 250, 150, 600),
        languages=languages,
        dismiss_popup_on_blur=dismiss,
        toolbar_timeout_ms=bounded_int("toolbar_timeout_ms", 8000, 2000, 20000),
        max_selection_chars=bounded_int("max_selection_chars", 6000, 200, 20000),
    )


@dataclass(frozen=True)
class FeatureSection:
    live_screen_enabled: bool = False
    region_translate_enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    app: AppSection = field(default_factory=AppSection)
    hotkeys: HotkeySection = field(default_factory=HotkeySection)
    clipboard: ClipboardSection = field(default_factory=ClipboardSection)
    translation: TranslationSection = field(default_factory=TranslationSection)
    providers: ProviderSection = field(default_factory=ProviderSection)
    ocr: OcrSection = field(default_factory=OcrSection)
    quick_ux: QuickUxSection = field(default_factory=QuickUxSection)
    ui: UiSection = field(default_factory=UiSection)
    features: FeatureSection = field(default_factory=FeatureSection)

    @classmethod
    def load(cls) -> "AppConfig":
        if getattr(sys, "frozen", False) and not os.getenv("APP_CONFIG_PATH"):
            PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
            for name in ("providers.json", "prompts.json", "config.json"):
                try:
                    with (PROJECT_ROOT / name).open("xb") as handle:
                        handle.write((Path(__file__).parent / "defaults" / name).read_bytes())
                except FileExistsError:
                    pass
        path = resolve_config_path()
        if not path.exists():
            return cls()

        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        return cls(
            app=_build_section(AppSection, raw.get("app", {})),
            hotkeys=parse_hotkey_section(raw.get("hotkeys", {})),
            clipboard=_build_section(ClipboardSection, raw.get("clipboard", {})),
            translation=_build_translation_section(raw.get("translation", {})),
            providers=_build_provider_section(raw.get("providers", {}), config_path=path),
            ocr=_build_ocr_section(raw.get("ocr", {})),
            quick_ux=parse_quick_ux_section(raw.get("quick_ux", {})),
            ui=_build_section(UiSection, raw.get("ui", {})),
            features=_build_section(FeatureSection, raw.get("features", {})),
        )

    @property
    def data_dir(self) -> Path:
        path = Path(self.app.data_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def cache_db_path(self) -> Path:
        return self.data_dir / "translation_cache.sqlite3"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


# --------------------------------------------------------------------------- paths

def resolve_config_path() -> Path:
    explicit_path = os.getenv("APP_CONFIG_PATH")
    return Path(explicit_path) if explicit_path else PROJECT_ROOT / "config.json"


def resolve_provider_catalog_path(
    catalog_path: str | Path | None = None,
    *,
    config_path: Path | None = None,
) -> Path:
    explicit_path = os.getenv("PROVIDER_CATALOG_PATH")
    if explicit_path:
        return Path(explicit_path)

    base_config = config_path or resolve_config_path()
    raw_path = Path(str(catalog_path or DEFAULT_PROVIDER_CATALOG))
    if raw_path.is_absolute():
        return raw_path
    return base_config.parent / raw_path


def resolve_prompt_catalog_path(
    catalog_path: str | Path | None = None,
    *,
    config_path: Path | None = None,
) -> Path:
    explicit_path = os.getenv("PROMPT_CATALOG_PATH")
    if explicit_path:
        return Path(explicit_path)

    base_config = config_path or resolve_config_path()
    raw_path = Path(str(catalog_path or DEFAULT_PROMPT_CATALOG))
    if raw_path.is_absolute():
        return raw_path
    return base_config.parent / raw_path


# ---------------------------------------------------------------- provider parsing

def provider_profile_from_dict(values: dict[str, Any]) -> ProviderProfile:
    """Parse one fully-resolved runtime profile."""
    from app.trial import is_trial_profile, trial_profile_values
    if is_trial_profile(values):
        values = trial_profile_values(values)
    allowed = ProviderProfile.__dataclass_fields__.keys()
    filtered = {key: value for key, value in values.items() if key in allowed}
    from app.providers.google_translate_addon import infer_google_provider_type
    kind = str(filtered.get("type", "openai_compatible")).strip().lower()
    if kind in {"openai_compatible", "openai-compatible", "compatible", "auto", ""}:
        detected = infer_google_provider_type(str(filtered.get("base_url", "")))
        if detected:
            filtered["type"] = detected

    paths = dict(DEFAULT_ENDPOINT_PATHS)
    user_paths = filtered.get("endpoint_paths")
    if isinstance(user_paths, dict):
        paths.update({str(k): str(v) for k, v in user_paths.items()})
    filtered["endpoint_paths"] = paths

    auto_order = filtered.get("auto_order", DEFAULT_AUTO_ORDER)
    if isinstance(auto_order, (list, tuple)):
        filtered["auto_order"] = tuple(str(item) for item in auto_order)
    else:
        filtered["auto_order"] = DEFAULT_AUTO_ORDER

    raw_models = filtered.get("models", ())
    if isinstance(raw_models, str):
        models = [raw_models]
    elif isinstance(raw_models, (list, tuple)):
        models = [str(item).strip() for item in raw_models if str(item).strip()]
    else:
        models = []
    active_model = str(filtered.get("model", "")).strip()
    if not active_model and models:
        active_model = models[0]
        filtered["model"] = active_model
    if active_model and active_model not in models:
        models.insert(0, active_model)
    filtered["models"] = tuple(dict.fromkeys(models))

    raw_override = filtered.get("streaming_override")
    override: dict[str, bool] = {}
    if isinstance(raw_override, dict):
        for mode in ("ultra_fast", "fast", "quality"):
            if mode not in raw_override:
                continue
            value = raw_override[mode]
            if isinstance(value, bool):
                override[mode] = value
            elif isinstance(value, str) and value.strip().lower() in {"true", "false"}:
                override[mode] = value.strip().lower() == "true"
            else:
                raise ValueError(
                    f"streaming_override.{mode} must be true/false, got {value!r}"
                )
    filtered["streaming_override"] = override

    return ProviderProfile(**filtered)


def provider_profile_to_dict(profile: ProviderProfile) -> dict[str, Any]:
    data = asdict(profile)
    data["models"] = list(profile.available_models())
    data["auto_order"] = list(profile.auto_order)
    return data


def portable_provider_entry(profile: ProviderProfile | dict[str, Any]) -> dict[str, Any]:
    """Return the exact portable schema: base_url, api_key, models."""
    from app.trial import is_trial_profile
    values = asdict(profile) if isinstance(profile, ProviderProfile) else profile
    if is_trial_profile(values):
        profile = provider_profile_from_dict(values)
    if isinstance(profile, ProviderProfile):
        base_url = profile.base_url
        api_key = profile.api_key
        models = list(profile.available_models())
    else:
        base_url = str(profile.get("base_url", "")).strip()
        api_key = str(profile.get("api_key", "")).strip()
        raw_models = profile.get("models", [])
        if isinstance(raw_models, str):
            models = [raw_models.strip()] if raw_models.strip() else []
        elif isinstance(raw_models, (list, tuple)):
            models = [str(item).strip() for item in raw_models if str(item).strip()]
        else:
            models = []
        active_model = str(profile.get("model", "")).strip()
        if active_model and active_model not in models:
            models.insert(0, active_model)
    return {
        "base_url": base_url,
        "api_key": api_key,
        "models": list(dict.fromkeys(models)),
    }


def profile_override_entry(profile: ProviderProfile | dict[str, Any]) -> dict[str, Any]:
    """Return app-specific provider settings that must stay out of providers.json."""
    data = provider_profile_to_dict(profile) if isinstance(profile, ProviderProfile) else dict(profile)
    for key in ("base_url", "api_key", "models"):
        data.pop(key, None)

    # Defaults are omitted to keep config.json compact, but active model is kept.
    result: dict[str, Any] = {}
    defaults = ProviderProfile()
    always_keep = {"model"}
    for key, value in data.items():
        if key in always_keep:
            if value not in (None, "", {}, []):
                result[key] = value
            continue
        if not hasattr(defaults, key):
            continue
        default_value = getattr(defaults, key)
        comparable_default = list(default_value) if isinstance(default_value, tuple) else default_value
        comparable_value = list(value) if isinstance(value, tuple) else value
        if comparable_value != comparable_default and comparable_value not in ({}, [], ""):
            result[key] = comparable_value
    return result


def provider_section_to_dict(section: ProviderSection) -> dict[str, Any]:
    return {
        "catalog_path": section.catalog_path,
        "active_profile": section.active_profile,
        "profile_overrides": {
            name: profile_override_entry(profile)
            for name, profile in section.profiles.items()
        },
    }


# -------------------------------------------------------------------- builders

def _build_section(section_type: type, values: dict[str, Any]):
    allowed = section_type.__dataclass_fields__.keys()
    filtered = {key: value for key, value in values.items() if key in allowed}
    return section_type(**filtered)


def _build_ocr_section(values: dict[str, Any]) -> OcrSection:
    allowed = OcrSection.__dataclass_fields__.keys()
    filtered = {key: value for key, value in values.items() if key in allowed}

    engine = str(filtered.get("engine", "rapidocr")).strip().lower() or "rapidocr"
    if engine not in {"rapidocr", "mock"}:
        raise ValueError(f"Unsupported OCR engine: {engine!r}. Supported: rapidocr, mock")
    filtered["engine"] = engine

    confidence = float(filtered.get("min_confidence", 0.45))
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("ocr.min_confidence must be between 0.0 and 1.0")
    filtered["min_confidence"] = confidence
    return OcrSection(**filtered)


def _build_translation_section(values: dict[str, Any]) -> TranslationSection:
    allowed = TranslationSection.__dataclass_fields__.keys()
    filtered = {key: value for key, value in values.items() if key in allowed}

    defaults = {
        "ultra_fast": True,
        "fast": False,
        "quality": False,
    }
    raw_streaming = filtered.get("streaming")
    if isinstance(raw_streaming, dict):
        for mode in tuple(defaults):
            if mode in raw_streaming:
                defaults[mode] = bool(raw_streaming[mode])
    filtered["streaming"] = defaults
    return TranslationSection(**filtered)


def _read_provider_catalog(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"Provider catalog root must be a JSON object: {path}")

    result: dict[str, dict[str, Any]] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        if str(name).casefold() == "trial":
            entry = dict(entry, type="ai_trial")
        result[str(name)] = portable_provider_entry(entry)
    return result


def _build_provider_section(values: dict[str, Any], *, config_path: Path) -> ProviderSection:
    active_profile = str(values.get("active_profile", "")).strip()
    catalog_path_value = str(values.get("catalog_path", DEFAULT_PROVIDER_CATALOG)).strip() or DEFAULT_PROVIDER_CATALOG
    raw_overrides = values.get("profile_overrides", {})
    overrides = raw_overrides if isinstance(raw_overrides, dict) else {}

    catalog_path = resolve_provider_catalog_path(catalog_path_value, config_path=config_path)
    catalog = _read_provider_catalog(catalog_path)
    profiles: dict[str, ProviderProfile] = {}

    if catalog:
        for name, portable in catalog.items():
            override = overrides.get(name, {})
            # App-specific overrides are merged first, then portable catalog-owned
            # fields are applied last so config.json can never shadow base_url,
            # api_key, or models.
            merged = dict(override) if isinstance(override, dict) else {}
            merged.update(portable)
            if name.casefold() == "trial":
                merged["type"] = "ai_trial"

            portable_models = list(portable.get("models", []))
            requested_model = str(merged.get("model", "")).strip()
            if requested_model not in portable_models:
                merged["model"] = portable_models[0] if portable_models else ""

            merged.setdefault("type", "openai_compatible")
            merged.setdefault("endpoint_mode", "auto")
            merged.setdefault("api_key_env", "")
            merged.setdefault("allow_no_api_key", False)
            profiles[name] = provider_profile_from_dict(merged)
    else:
        # Backward compatibility for V0.3.0 and older configs. This does not write
        # files during load; Save & Apply in V0.3.1 migrates to providers.json.
        raw_profiles = values.get("profiles", {})
        if isinstance(raw_profiles, dict):
            for name, raw_profile in raw_profiles.items():
                if isinstance(raw_profile, dict):
                    profiles[str(name)] = provider_profile_from_dict(raw_profile)

    if not profiles:
        profiles["mock"] = ProviderProfile(
            type="mock", model="mock-v2", models=("mock-v2",), allow_no_api_key=True
        )

    if active_profile not in profiles:
        active_profile = next(iter(profiles))

    return ProviderSection(
        active_profile=active_profile,
        catalog_path=catalog_path_value,
        profile_overrides={
            str(name): dict(value)
            for name, value in overrides.items()
            if isinstance(value, dict)
        },
        profiles=profiles,
    )
