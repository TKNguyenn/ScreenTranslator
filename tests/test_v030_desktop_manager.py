from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import httpx

from app.config import ProviderProfile, provider_profile_from_dict, provider_profile_to_dict
from app.models import RequestMode, TranslationRequest
from app.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.services.config_store import ConfigFileStore


class V030ProviderConfigTests(unittest.TestCase):
    def test_old_single_model_config_becomes_model_catalog(self) -> None:
        profile = provider_profile_from_dict({"model": "gpt-test"})
        self.assertEqual(profile.model, "gpt-test")
        self.assertEqual(profile.available_models(), ("gpt-test",))

    def test_models_round_trip_keeps_active_model(self) -> None:
        profile = provider_profile_from_dict(
            {"model": "m2", "models": ["m1", "m2", "m3"]}
        )
        dumped = provider_profile_to_dict(profile)
        self.assertEqual(dumped["model"], "m2")
        self.assertEqual(dumped["models"], ["m1", "m2", "m3"])

    def test_direct_api_key_works_without_env(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["authorization"] = request.headers.get("Authorization")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "xin chao"}}]},
            )

        profile = ProviderProfile(
            base_url="https://example.test/v1",
            api_key="direct-secret",
            api_key_env="",
            model="demo-model",
            models=("demo-model",),
            endpoint_mode="chat_completions",
        )
        provider = OpenAICompatibleProvider(
            "demo", profile, transport=httpx.MockTransport(handler)
        )
        request = TranslationRequest(
            job_id="1",
            source_text="hello",
            source_language="en",
            target_language="vi",
            context_preset="chat",
            performance_mode="fast",
            mode=RequestMode.POPUP,
            foreground_hwnd=None,
        )
        try:
            self.assertEqual(provider.translate(request, "translate"), "xin chao")
            self.assertEqual(captured["authorization"], "Bearer direct-secret")
        finally:
            provider.close()

    def test_replace_section_preserves_other_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"app": {"name": "x"}, "providers": {}}))
            store = ConfigFileStore(path)
            store.replace_section(
                "providers", {"active_profile": "a", "profiles": {"a": {"model": "m"}}}
            )
            data = json.loads(path.read_text())
            self.assertEqual(data["app"]["name"], "x")
            self.assertEqual(data["providers"]["active_profile"], "a")


class V030UiSourceTests(unittest.TestCase):
    def test_main_window_has_minimize_to_tray_and_close_to_exit(self) -> None:
        source = (Path(__file__).parents[1] / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("def changeEvent", source)
        self.assertIn("self.hide", source)
        self.assertIn("def closeEvent", source)
        self.assertIn("self.exit_requested.emit()", source)

    def test_tray_double_click_opens_main_window(self) -> None:
        source = (Path(__file__).parents[1] / "app" / "ui" / "tray.py").read_text(encoding="utf-8")
        self.assertIn("QSystemTrayIcon.DoubleClick", source)
        self.assertIn("Mở cửa sổ chính", source)

    def test_controller_shows_main_window_at_startup(self) -> None:
        source = (Path(__file__).parents[1] / "app" / "controller.py").read_text(encoding="utf-8")
        self.assertIn("self._main_window.show()", source)
        self.assertIn("save_providers_requested", source)


if __name__ == "__main__":
    unittest.main()
