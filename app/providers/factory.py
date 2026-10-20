from __future__ import annotations

from app.config import AppConfig, ProviderProfile, provider_profile_from_dict, provider_profile_to_dict
from app.trial import is_trial_profile
from app.providers.trial_provider import TrialProvider
from app.services.trial_usage import TrialUsageStore
from app.providers.base import TranslationProvider
from app.providers.mock_provider import MockTranslationProvider
from app.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.providers.google_translate_addon import create_google_provider, infer_google_provider_type


def resolve_provider_profile(
    config: AppConfig,
    profile_name: str | None = None,
) -> tuple[str, ProviderProfile]:
    """Resolve either an explicit profile or the configured active profile."""
    name = profile_name or config.providers.active_profile
    profile = config.providers.profiles.get(name)
    if profile is None:
        available = ", ".join(sorted(config.providers.profiles)) or "<none>"
        raise ValueError(
            f"Provider profile '{name}' does not exist. Available: {available}"
        )
    return name, profile


def create_translation_provider(
    config: AppConfig,
    profile_name: str | None = None,
) -> TranslationProvider:
    name, profile = resolve_provider_profile(config, profile_name)
    values = provider_profile_to_dict(profile)
    if name.casefold() == "trial":
        values["type"] = "ai_trial"
    if is_trial_profile(values):
        profile = provider_profile_from_dict(values)
        if not profile.api_key:
            raise RuntimeError("Trial chưa có API key. Liên hệ người phát triển để nhận key riêng.")
        return TrialProvider(profile_name=name, profile=profile,
                             usage=TrialUsageStore(config.data_dir / "trial_usage.json"))
    provider_type = profile.type.lower().strip()
    if provider_type in {"openai_compatible", "openai-compatible", "compatible", "auto", ""}:
        provider_type = infer_google_provider_type(profile.base_url) or provider_type
        from app.providers.microsoft_provider import is_microsoft_url
        if is_microsoft_url(profile.base_url):
            provider_type = "microsoft_translator"
    if provider_type in {"google_translate_web", "google_cloud_translate"}:
        return create_google_provider(name, profile, provider_type=provider_type)
    if provider_type == "microsoft_translator":
        from app.providers.microsoft_provider import MicrosoftTranslationProvider
        from microsoft_translator_usage import LocalUsageLedger
        import logging
        import sqlite3
        usage = None
        try:
            usage = LocalUsageLedger(config.data_dir / "microsoft_usage.sqlite3")
        except (OSError, sqlite3.Error):
            logging.getLogger(__name__).warning("Cannot initialize Microsoft usage ledger", exc_info=True)
        return MicrosoftTranslationProvider(name, profile, usage=usage)

    if provider_type == "mock":
        return MockTranslationProvider(
            model=profile.model,
            streaming_override=profile.streaming_override,
        )
    if provider_type in {"openai_compatible", "openai-compatible", "compatible"}:
        return OpenAICompatibleProvider(profile_name=name, profile=profile)

    raise ValueError(
        f"Unsupported provider type '{profile.type}' in profile '{name}'."
    )
