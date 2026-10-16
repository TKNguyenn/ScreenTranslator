from __future__ import annotations

import unittest

from app.config import AppConfig, ProviderProfile, ProviderSection
from app.providers.factory import create_translation_provider, resolve_provider_profile


class FactoryProfileSelectionTests(unittest.TestCase):
    def test_explicit_profile_overrides_configured_active_profile(self) -> None:
        config = AppConfig(
            providers=ProviderSection(
                active_profile="a",
                profiles={
                    "a": ProviderProfile(type="mock", model="mock-a"),
                    "b": ProviderProfile(type="mock", model="mock-b"),
                },
            )
        )
        name, profile = resolve_provider_profile(config, "b")
        self.assertEqual(name, "b")
        self.assertEqual(profile.model, "mock-b")
        provider = create_translation_provider(config, "b")
        self.assertEqual(provider.model_id, "mock-b")


if __name__ == "__main__":
    unittest.main()
