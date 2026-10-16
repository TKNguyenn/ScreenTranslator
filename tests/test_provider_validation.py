from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import ProviderProfile
from app.providers.openai_compatible_provider import OpenAICompatibleProvider


class ProviderValidationTests(unittest.TestCase):
    def test_placeholder_base_url_is_rejected(self) -> None:
        profile = ProviderProfile(
            base_url="https://YOUR_PROVIDER_HOST/v1",
            api_key_env="TEST_KEY",
            model="deepseek-chat",
        )
        with patch.dict(os.environ, {"TEST_KEY": "abc"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "placeholder base_url"):
                OpenAICompatibleProvider("test", profile)

    def test_placeholder_model_is_rejected(self) -> None:
        profile = ProviderProfile(
            base_url="https://api.example.invalid/v1",
            api_key_env="TEST_KEY",
            model="YOUR_MODEL_ID",
        )
        with patch.dict(os.environ, {"TEST_KEY": "abc"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "YOUR_MODEL_ID"):
                OpenAICompatibleProvider("test", profile)

    def test_placeholder_api_key_is_rejected(self) -> None:
        profile = ProviderProfile(
            base_url="https://api.example.invalid/v1",
            api_key_env="TEST_KEY",
            model="deepseek-chat",
        )
        with patch.dict(os.environ, {"TEST_KEY": "replace_me"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "missing/not configured"):
                OpenAICompatibleProvider("test", profile)


if __name__ == "__main__":
    unittest.main()
