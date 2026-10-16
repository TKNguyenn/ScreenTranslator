from __future__ import annotations

from app.config import AppConfig, ProviderProfile
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
    provider_type = profile.type.lower().strip()
    if provider_type in {"openai_compatible", "openai-compatible", "compatible", "auto", ""}:
        provider_type = infer_google_provider_type(profile.base_url) or provider_type
    if provider_type in {"google_translate_web", "google_cloud_translate"}:
        return create_google_provider(name, profile, provider_type=provider_type)

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
