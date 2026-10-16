from __future__ import annotations

import unittest

from app.config import AppConfig, ProviderProfile


class ConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = AppConfig()
        self.assertEqual(config.translation.target_language, "vi")
        self.assertEqual(config.translation.context_preset, "engineering")
        self.assertFalse(config.features.live_screen_enabled)
        self.assertEqual(config.providers.active_profile, "mock")
        self.assertTrue(config.translation.streaming_enabled_for("ultra_fast"))
        self.assertFalse(config.translation.streaming_enabled_for("fast"))
        self.assertFalse(config.translation.streaming_enabled_for("quality"))

    def test_provider_profile_allows_arbitrary_model(self) -> None:
        deepseek = ProviderProfile(model="deepseek-whatever-v99", endpoint_mode="chat_completions")
        glm = ProviderProfile(model="glm-custom-provider-id", endpoint_mode="responses")
        self.assertEqual(deepseek.model, "deepseek-whatever-v99")
        self.assertEqual(glm.model, "glm-custom-provider-id")

    def test_profile_streaming_override_defaults_to_none(self) -> None:
        profile = ProviderProfile()
        self.assertIsNone(profile.streaming_override_for("ultra_fast"))

    def test_profile_streaming_override_can_force_on_or_off(self) -> None:
        profile = ProviderProfile(streaming_override={"ultra_fast": False, "fast": True})
        self.assertFalse(profile.streaming_override_for("ultra_fast"))
        self.assertTrue(profile.streaming_override_for("fast"))
        self.assertIsNone(profile.streaming_override_for("quality"))
