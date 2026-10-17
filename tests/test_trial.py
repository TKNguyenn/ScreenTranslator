from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import httpx
from PySide6.QtWidgets import QApplication
from app.config import (AppConfig, ProviderProfile, ProviderSection, provider_profile_from_dict,
                        provider_profile_to_dict, profile_override_entry)
from app.models import RequestMode, TranslationRequest
from app.providers.factory import create_translation_provider
from app.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.services.provider_catalog import ProviderCatalogStore
from app.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]
URL = "https://api.vilao.ai/v1"
MODELS = ("gemini-3.8-flash", "gpt-6-luna", "gpt-6-sol")


def trial(**changes):
    return provider_profile_from_dict({"type": "ai_trial", "base_url": URL,
                                       "models": list(MODELS), **changes})


class TrialTests(unittest.TestCase):
    def test_custom_gateway_profile_is_not_trial_and_survives_save_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = {"base_url": URL, "api_key": "synthetic-key",
                   "model": "gemini-3.7-flash", "models": ["gemini-3.7-flash", "custom-model"]}
            for values in (raw, dict(raw, type="openai_compatible")):
                profile = provider_profile_from_dict(values)
                self.assertEqual(profile.type, "openai_compatible")
                self.assertEqual(profile.model, raw["model"])
                self.assertEqual(list(profile.models), raw["models"])
            store = ProviderCatalogStore(root / "providers.json")
            store.replace_all({"VILAO": raw, "Trial": {"base_url": URL, "models": list(MODELS)}})
            (root / "config.json").write_text(json.dumps({"providers": {"active_profile": "VILAO"}}))
            with patch.dict(os.environ, {"APP_CONFIG_PATH": str(root / "config.json")}):
                config = AppConfig.load()
            custom = config.providers.profiles["VILAO"]
            self.assertEqual(custom.type, "openai_compatible")
            self.assertEqual(custom.model, raw["model"])
            self.assertEqual(list(custom.models), raw["models"])
            self.assertEqual(config.providers.profiles["Trial"].type, "ai_trial")
            provider = create_translation_provider(config)
            self.addCleanup(provider.close)
            self.assertIs(type(provider), OpenAICompatibleProvider)

    def test_frozen_defaults_seed_once_without_overwriting_existing_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("app.config.PROJECT_ROOT", root), patch("app.config.sys.frozen", True, create=True), \
                    patch.dict(os.environ, {"APP_CONFIG_PATH": ""}):
                config = AppConfig.load()
                self.assertEqual(list(config.providers.profiles), ["Google Translate Free", "Trial"])
                self.assertEqual(config.providers.active_profile, "Google Translate Free")
                self.assertEqual(config.providers.profiles["Trial"].api_key, "")
                provider = create_translation_provider(config)
                provider.close()
                custom = b'{"Mine":{"base_url":"https://custom.invalid/v1","api_key":"saved","models":["m"]}}'
                (root / "providers.json").write_bytes(custom)
                config = AppConfig.load()
                self.assertEqual(list(config.providers.profiles), ["Mine"])
                self.assertEqual((root / "providers.json").read_bytes(), custom)

    def test_reserved_trial_import_cannot_redirect_the_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProviderCatalogStore(Path(tmp) / "providers.json")
            store.replace_all({"Trial": {"base_url": "https://other.invalid", "api_key": "user-key",
                                         "models": ["not-allowed"]}})
            entry = store.read()["Trial"]
            self.assertEqual(entry["base_url"], URL)
            self.assertEqual(entry["models"], list(MODELS))
            self.assertEqual(entry["api_key"], "user-key")

    def test_fixed_connection_settings_and_model_allowlist(self):
        profile = trial(base_url="https://other.invalid", api_key="user-key",
                        endpoint_paths={"responses": "https://other.invalid"},
                        extra_headers={"Authorization": "unsafe"}, extra_body={"model": "other"},
                        verify_ssl=False, allow_no_api_key=True, api_key_env="OTHER_KEY")
        self.assertEqual(profile.base_url, URL)
        self.assertEqual(profile.type, "ai_trial")
        self.assertEqual(profile.available_models(), MODELS)
        self.assertTrue(profile.verify_ssl)
        self.assertFalse(profile.allow_no_api_key)
        self.assertEqual(profile.api_key_env, "")
        self.assertEqual(profile.extra_headers, {})
        self.assertEqual(profile.extra_body, {})
        self.assertEqual(profile.endpoint_paths["responses"], "/responses")
        self.assertEqual(profile.endpoint_mode, "auto")
        for mode in ("auto", "responses", "chat_completions", "completions"):
            self.assertEqual(trial(endpoint_mode=mode).endpoint_mode, mode)
        with self.assertRaises(ValueError):
            trial(endpoint_mode="https://other.invalid")
        with self.assertRaises(ValueError):
            trial(model="not-allowed")

    def test_factory_revalidates_direct_profiles_and_requires_a_key(self):
        config = replace(AppConfig(), providers=ProviderSection(active_profile="Renamed",
                         profiles={"Renamed": ProviderProfile(type="ai_trial", base_url="https://other.invalid",
                                   models=MODELS, model=MODELS[1], api_key="user-key", verify_ssl=False)}))
        provider = create_translation_provider(config)
        self.addCleanup(provider.close)
        self.assertEqual(provider._base_url, URL)
        self.assertTrue(provider._profile.verify_ssl)
        with self.assertRaises(RuntimeError):
            create_translation_provider(replace(config, providers=replace(config.providers,
                profiles={"Renamed": trial()})))

    def test_fresh_defaults_and_roundtrip_preserve_custom_profiles(self):
        for filename in ("app/defaults/providers.json", "providers.example.json"):
            data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
            self.assertEqual(list(data), ["Google Translate Free", "Trial"])
            self.assertEqual(data["Trial"]["api_key"], "")
            self.assertEqual(data["Trial"]["models"], list(MODELS))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProviderCatalogStore(root / "providers.json")
            custom = {"base_url": "https://custom.invalid/v1", "api_key": "custom-key", "models": ["m"]}
            profile = trial(api_key="trial-key", model=MODELS[2], endpoint_mode="responses",
                            streaming_override={"fast": True})
            store.replace_all({"Custom": custom, "Renamed Trial": provider_profile_to_dict(profile)})
            original = (root / "providers.json").read_bytes()
            (root / "config.json").write_text(json.dumps({"providers": {
                "active_profile": "Custom", "catalog_path": "providers.json", "profile_overrides": {
                    "Renamed Trial": profile_override_entry(profile)}}}), encoding="utf-8")
            with patch.dict(os.environ, {"APP_CONFIG_PATH": str(root / "config.json")}):
                config = AppConfig.load()
            restored = config.providers.profiles["Renamed Trial"]
            self.assertEqual(restored.type, "ai_trial")
            self.assertEqual(restored.api_key, "trial-key")
            self.assertEqual(restored.model, MODELS[2])
            self.assertEqual(restored.endpoint_mode, "responses")
            self.assertEqual(restored.streaming_override, {"fast": True})
            self.assertEqual(store.read()["Custom"], custom)
            self.assertEqual((root / "providers.json").read_bytes(), original)

    def test_translation_and_streaming_use_fixed_url_and_selected_model(self):
        seen = []
        def handle(req):
            body = json.loads(req.content)
            seen.append((str(req.url), body))
            if body.get("stream"):
                return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Xin chao"}}]}\n\ndata: [DONE]\n\n',
                                      headers={"content-type": "text/event-stream"})
            return httpx.Response(200, json={"choices": [{"message": {"content": "Xin chao"}}]})
        req = TranslationRequest("test", "Hello", "en", "vi", "chat", "fast", RequestMode.POPUP, None)
        for enabled in (False, True):
            profile = trial(api_key="test-key", model=MODELS[1], endpoint_mode="chat_completions",
                            streaming_override={"fast": enabled})
            provider = OpenAICompatibleProvider("Trial", profile, transport=httpx.MockTransport(handle))
            self.addCleanup(provider.close)
            self.assertIs(provider.streaming_override_for("fast"), enabled)
            self.assertIsNone(provider.streaming_override_for("quality"))
            deltas = []
            result = provider.translate_stream(req, "Translate", deltas.append) if enabled else provider.translate(req, "Translate")
            self.assertEqual(result, "Xin chao")
            self.assertEqual(deltas, ["Xin chao"] if enabled else [])
        self.assertEqual(len(seen), 2)
        for url, body in seen:
            self.assertEqual(url, URL + "/chat/completions")
            self.assertEqual(body["model"], MODELS[1])

    def test_selected_endpoints_and_auto_fallback_charge_once(self):
        from app.providers.trial_provider import TrialProvider
        from app.services.trial_usage import TrialUsageStore
        request = TranslationRequest("endpoint", "Hello", "en", "vi", "chat", "fast", RequestMode.POPUP, None)
        for mode in ("auto", "responses", "chat_completions", "completions"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                seen = []
                def handle(req):
                    seen.append(req.url.path)
                    self.assertEqual(json.loads(req.content)["model"], MODELS[1])
                    if req.url.path.endswith("/responses"):
                        return (httpx.Response(404, json={"error": "unsupported endpoint"}) if mode == "auto"
                                else httpx.Response(200, json={"output_text": "Xin chao"}))
                    if req.url.path.endswith("/chat/completions"):
                        return httpx.Response(200, json={"choices": [{"message": {"content": "Xin chao"}}]})
                    return httpx.Response(200, json={"choices": [{"text": "Xin chao"}]})
                usage = TrialUsageStore(Path(tmp) / "usage.json")
                provider = TrialProvider("Trial", trial(api_key="test-key", model=MODELS[1], endpoint_mode=mode),
                                         usage, transport=httpx.MockTransport(handle))
                try:
                    self.assertEqual(provider.translate(request, "Translate"), "Xin chao")
                    self.assertEqual(usage.remaining("test-key"), 99)
                    expected = {"responses": ["/v1/responses"], "completions": ["/v1/completions"],
                                "chat_completions": ["/v1/chat/completions"],
                                "auto": ["/v1/responses", "/v1/chat/completions"]}
                    self.assertEqual(seen, expected[mode])
                finally:
                    provider.close()


class TrialUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_save_from_each_provider_with_custom_trial_gateway(self):
        from app.controller import AppController
        from app.services.config_store import ConfigFileStore

        config = replace(AppConfig(), providers=ProviderSection(active_profile="Custom", profiles={
            "Custom": ProviderProfile(base_url=URL, api_key="synthetic-key",
                                      model="custom-model", models=("custom-model",)),
            "Google Translate Free": provider_profile_from_dict({
                "base_url": "https://translate.googleapis.com", "models": ["google-translate"]}),
            "Trial": trial(api_key="synthetic-key", model=MODELS[2]),
        }))
        window = MainWindow(self.app, config)
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.allow_close)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            controller = SimpleNamespace(
                _config=config, _profile=config.providers.profiles["Custom"],
                _provider_catalog_store=ProviderCatalogStore(root / "providers.json"),
                _config_store=ConfigFileStore(root / "config.json"),
                _runtime_settings=Mock(), _reload_config_internal=Mock(return_value=True),
                _tray=Mock(), _show_error_dialog=Mock(),
            )
            window.save_providers_requested.connect(
                lambda profiles, active: AppController._save_provider_configuration(controller, profiles, active))
            for row, name in enumerate(config.providers.profiles):
                with self.subTest(provider=name):
                    window._provider_list.setCurrentRow(row)
                    window._active_profile_combo.setCurrentText(name)
                    window._save_and_apply()
                    controller._show_error_dialog.assert_not_called()
                    controller._reload_config_internal.assert_called_with(preferred_profile=name)
                    with patch.dict(os.environ, {"APP_CONFIG_PATH": str(root / "config.json")}):
                        restored = AppConfig.load()
                    self.assertEqual(restored.providers.active_profile, name)
                    self.assertEqual(restored.providers.profiles["Custom"].type, "openai_compatible")
                    self.assertEqual(restored.providers.profiles["Custom"].model, "custom-model")
                    self.assertEqual(restored.providers.profiles["Trial"].model, MODELS[2])

    def test_compact_editor_switches_saves_and_reloads_without_quota_numbers(self):
        config = replace(AppConfig(), providers=ProviderSection(active_profile="Google Translate Free", profiles={
            "Google Translate Free": provider_profile_from_dict({"base_url": "https://translate.googleapis.com", "models": ["google-translate"]}),
            "Trial": trial(),
            "Custom": ProviderProfile(model="m", models=("m",)),
        }))
        window = MainWindow(self.app, config)
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.allow_close)
        window._nav.setCurrentRow(1)
        window.show()
        self.addCleanup(window.hide)
        window._provider_list.setCurrentRow(1)
        self.app.processEvents()
        self.assertTrue(window._api_key_edit.isVisible())
        self.assertTrue(window._endpoint_combo.isVisible())
        self.assertTrue(window._endpoint_combo.isEnabled())
        self.assertEqual(window._endpoint_combo.currentText(), "auto")
        self.assertFalse(window._base_url_edit.isVisible())
        self.assertFalse(window._models_list.isVisible())
        self.assertTrue(window._stream_group.isVisible())
        self.assertTrue(window._trial_quota.isVisible())
        self.assertFalse(window._trial_quota.isTextVisible())
        self.assertEqual(window._trial_quota.value(), 100)
        self.assertNotRegex(window._trial_quota_status.text(), r"\d")
        self.assertIn("ước lượng", window._trial_quota_status.text())
        window._api_key_edit.setText("user-key")
        window._endpoint_combo.setCurrentText("responses")
        window._active_model_combo.setCurrentIndex(2)
        self.assertIn("4đ/lượt", window._active_model_combo.currentText())
        window._set_stream_combo(window._stream_ultra, True)
        window._set_stream_combo(window._stream_fast, False)
        window._set_stream_combo(window._stream_quality, None)
        window._active_profile_combo.setCurrentText("Trial")
        saved = []
        window.save_providers_requested.connect(lambda profiles, active: saved.append((profiles, active)))
        window._save_and_apply()
        profiles, active = saved[0]
        self.assertEqual(active, "Trial")
        self.assertEqual(profiles["Trial"]["model"], MODELS[2])
        self.assertEqual(profiles["Trial"]["endpoint_mode"], "responses")
        self.assertEqual(profiles["Trial"]["streaming_override"], {"ultra_fast": True, "fast": False})
        window.load_config(replace(config, providers=replace(config.providers,
            profiles={name: provider_profile_from_dict(data) for name, data in profiles.items()})), active_profile="Trial")
        window._provider_list.setCurrentRow(1)
        self.assertEqual(window._endpoint_combo.currentText(), "responses")
        self.assertIs(window._stream_ultra.currentData(), True)
        self.assertIs(window._stream_fast.currentData(), False)
        self.assertIsNone(window._stream_quality.currentData())
        window._provider_list.setCurrentRow(2)
        self.assertTrue(window._base_url_edit.isVisible())
        self.assertTrue(window._models_list.isVisible())
        self.assertTrue(window._stream_group.isVisible())
        self.assertFalse(window._trial_group.isVisible())
        window._provider_list.setCurrentRow(0)
        self.assertFalse(window._models_group.isVisible())
        self.assertFalse(window._stream_group.isVisible())

    def test_visible_estimate_refills_on_daily_timer(self):
        from app.services.trial_usage import TrialUsageStore
        with tempfile.TemporaryDirectory() as tmp:
            config = replace(AppConfig(), app=replace(AppConfig().app, data_dir=tmp),
                             providers=ProviderSection(active_profile="Trial", profiles={"Trial": trial(api_key="key-a")}))
            usage = TrialUsageStore(config.data_dir / "trial_usage.json")
            with patch("app.services.trial_usage._today", return_value="2026-10-17"):
                usage.record("key-a", "gpt-6-sol")
                window = MainWindow(self.app, config)
                self.addCleanup(window.deleteLater)
                self.addCleanup(window.allow_close)
                self.addCleanup(window.hide)
                window._nav.setCurrentRow(1)
                window.show()
                self.app.processEvents()
                self.assertTrue(window._trial_group.isVisible())
                self.assertEqual(window._trial_quota.value(), 96)
            with patch("app.services.trial_usage._today", return_value="2026-10-18"):
                window._trial_quota_timer.timeout.emit()
                self.assertEqual(window._trial_quota.value(), 100)


class TrialEstimateTests(unittest.TestCase):
    def test_prices_persist_per_key_reset_daily_and_clamp_without_storing_keys(self):
        from app.services.trial_usage import TrialUsageStore
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            store = TrialUsageStore(path)
            with patch("app.services.trial_usage._today", return_value="2026-10-17"):
                self.assertEqual(store.remaining("key-a"), 100)
                for model in ("gpt-6-luna", "gemini-3.8-flash", "gpt-6-sol"):
                    store.record("key-a", model)
                self.assertEqual(TrialUsageStore(path).remaining("key-a"), 92)
                self.assertEqual(store.remaining("key-b"), 100)
                self.assertNotIn("key-a", path.read_text())
                for _ in range(30):
                    store.record("key-a", "gpt-6-sol")
                self.assertEqual(store.remaining("key-a"), 0)
            with patch("app.services.trial_usage._today", return_value="2026-10-18"):
                self.assertEqual(store.remaining("key-a"), 100)

    def test_startup_check_keeps_two_timestamps_and_resets_after_midnight(self):
        from app.services.trial_usage import TrialUsageStore
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            with patch("app.services.trial_usage._today", return_value="2026-10-17"):
                store = TrialUsageStore(path)
                store.record("key-a", "gpt-6-sol")
                TrialUsageStore(path)
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(len(data["checks"]), 2)
                self.assertEqual(data["checks"][-1]["date"], "2026-10-17")
                self.assertEqual(TrialUsageStore(path).remaining("key-a"), 96)
            with patch("app.services.trial_usage._today", return_value="2026-10-18"):
                TrialUsageStore(path)
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["date"], "2026-10-18")
                self.assertEqual(data["spent"], {})
                self.assertEqual(len(data["checks"]), 2)
                self.assertEqual([item["date"] for item in data["checks"]], ["2026-10-17", "2026-10-18"])
                self.assertEqual(TrialUsageStore(path).remaining("key-a"), 100)

    def test_concurrent_provider_instances_do_not_lose_estimated_usage(self):
        from concurrent.futures import ThreadPoolExecutor
        from app.services.trial_usage import TrialUsageStore
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _: TrialUsageStore(path).record("key-a", "gpt-6-luna"), range(20)))
            self.assertEqual(TrialUsageStore(path).remaining("key-a"), 80)

    def test_provider_counts_success_once_and_ignores_cache_and_failures(self):
        from app.services.trial_usage import TrialUsageStore
        from app.services.cache import TranslationCache
        from app.workers.translation_worker import TranslationWorker
        from app.config import TranslationSection
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = trial(api_key="key-a", model="gpt-6-luna", streaming_override={"fast": False})
            config = replace(AppConfig(), app=replace(AppConfig().app, data_dir=str(root)),
                             providers=ProviderSection(active_profile="Trial", profiles={"Trial": profile}))
            client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(
                200, json={"choices": [{"message": {"content": "Xin chao"}}]})))
            with patch("app.providers.openai_compatible_provider.httpx.Client", return_value=client):
                provider = create_translation_provider(config)
            self.addCleanup(provider.close)
            results = []
            worker = TranslationWorker(provider, TranslationCache(root / "cache.db"), TranslationSection(), results.append)
            request = TranslationRequest("one", "Hello", "en", "vi", "chat", "fast", RequestMode.POPUP, None)
            worker._translate(request)
            worker._translate(replace(request, job_id="cached"))
            self.assertTrue(results[-1].cached)
            store = TrialUsageStore(root / "trial_usage.json")
            self.assertEqual(store.remaining("key-a"), 99)
            client._transport = httpx.MockTransport(lambda req: httpx.Response(429, json={"error": "limited"}))
            with self.assertRaisesRegex(RuntimeError, "429"):
                provider.translate(replace(request, source_text="Another"), "Translate")
            self.assertEqual(store.remaining("key-a"), 99)
            client._transport = httpx.MockTransport(lambda req: httpx.Response(200,
                text='data: {"choices":[{"delta":{"content":"Xin "}}]}\n\ndata: {"choices":[{"delta":{"content":"chao"}}]}\n\ndata: [DONE]\n\n',
                headers={"content-type": "text/event-stream"}))
            self.assertEqual(provider.translate_stream(request, "Translate", lambda _: None), "Xin chao")
            self.assertEqual(store.remaining("key-a"), 98)
            with patch.object(provider._trial_usage, "record", side_effect=OSError("disk unavailable")), \
                    self.assertLogs("app.providers.trial_provider", level="WARNING"):
                self.assertEqual(provider.translate_stream(request, "Translate", lambda _: None), "Xin chao")


if __name__ == "__main__":
    unittest.main()
