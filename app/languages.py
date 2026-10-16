from __future__ import annotations

# Human-readable names used by prompts and the tray UI.
LANGUAGE_NAMES: dict[str, str] = {
    "auto": "auto-detected source language",
    "vi": "Vietnamese",
    "en": "English",
    "zh-Hant": "Traditional Chinese",
    "zh-Hans": "Simplified Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}

# Keep this list small and practical for the tray context menu. Translation
# providers can still accept another language code programmatically later.
TRAY_TARGET_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("vi", "Tiếng Việt"),
    ("en", "English"),
    ("zh-Hant", "繁體中文 (Traditional Chinese)"),
    ("zh-Hans", "简体中文 (Simplified Chinese)"),
    ("ja", "日本語 (Japanese)"),
    ("ko", "한국어 (Korean)"),
)

TRAY_TARGET_LANGUAGE_CODES = frozenset(code for code, _ in TRAY_TARGET_LANGUAGES)
