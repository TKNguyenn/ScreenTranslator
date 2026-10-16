from __future__ import annotations

import json
import logging
import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

import httpx

from app.config import AppConfig, ProviderProfile, ProviderSection, TranslationSection, provider_profile_from_dict
from app.models import RequestMode, TranslationRequest
from app.providers.factory import create_translation_provider
from app.services.cache import TranslationCache
from app.workers.translation_worker import TranslationWorker


def request(**changes):
    return replace(TranslationRequest(job_id="google-test", source_text="Hello",
                   source_language="auto", target_language="vi", context_preset="engineering",
                   performance_mode="ultra_fast", mode=RequestMode.POPUP, foreground_hwnd=None), **changes)


class GoogleIntegrationTests(unittest.TestCase):
    def test_portable_google_profiles_inferred_without_changing_other_types(self):
        for url, kind, model in (("https://translate.googleapis.com", "google_translate_web", "google-translate"),
                                 ("https://translation.googleapis.com", "google_cloud_translate", "nmt")):
            with self.subTest(kind=kind):
                profile = provider_profile_from_dict({"base_url": url, "models": [model]})
                self.assertEqual(profile.type, kind)
                self.assertEqual(profile.model, model)
        self.assertEqual(provider_profile_from_dict({"base_url": "https://api.example.test/v1"}).type,
                         "openai_compatible")
        self.assertEqual(provider_profile_from_dict({"type": "mock",
                         "base_url": "https://translate.googleapis.com"}).type, "mock")

    def test_catalog_reload_routes_google_and_preserves_active_model_and_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers.json").write_text(json.dumps({
                "Free": {"base_url": "https://translate.googleapis.com", "api_key": "", "models": ["google-translate"]},
                "Cloud": {"base_url": "https://translation.googleapis.com", "api_key": "", "models": ["nmt"]},
                "AI": {"base_url": "https://api.example.test/v1", "api_key": "test", "models": ["first", "second"]},
            }), encoding="utf-8")
            (root / "config.json").write_text(json.dumps({"providers": {"active_profile": "AI",
                "profile_overrides": {"AI": {"model": "second"}}}}), encoding="utf-8")
            with patch.dict(os.environ, {"APP_CONFIG_PATH": str(root / "config.json")}):
                config = AppConfig.load()
            self.assertEqual(config.providers.profiles["Free"].type, "google_translate_web")
            self.assertEqual(config.providers.profiles["Cloud"].type, "google_cloud_translate")
            self.assertEqual(config.providers.active_profile, "AI")
            self.assertEqual(config.providers.profiles["AI"].model, "second")
            provider = create_translation_provider(config, "Free")
            self.addCleanup(provider.close)
            self.assertFalse(provider.streaming_override_for("ultra_fast"))


class GoogleAdapterTests(unittest.TestCase):
    def setUp(self):
        from app.providers import google_translate_addon as google
        self.google = google

    def provider(self, handler, cloud=False, **changes):
        profile = {"base_url": "https://translation.googleapis.com" if cloud else "https://translate.googleapis.com",
                   "model": "nmt" if cloud else "google-translate", "api_key": "synthetic-key", **changes}
        cls = self.google.GoogleCloudTranslationProvider if cloud else self.google.GoogleTranslateWebProvider
        provider = cls("test", profile, transport=httpx.MockTransport(handler))
        self.addCleanup(provider.close)
        return provider

    def test_web_joins_segments_and_maps_traditional_chinese(self):
        def handle(req):
            self.assertEqual(req.method, "GET")
            self.assertEqual(req.url.path, "/translate_a/single")
            self.assertEqual(req.url.params["tl"], "zh-TW")
            self.assertEqual(req.url.params["sl"], "auto")
            self.assertEqual(req.url.params["q"], "Hello")
            self.assertNotIn("x-goog-api-key", req.headers)
            return httpx.Response(200, json=[[["你好", "Hello"], ["！", None]]])
        provider = self.provider(handle)
        self.assertEqual(provider.translate(request(target_language="zh-Hant"), "ignored prompt"), "你好！")

    def test_cloud_key_header_auto_source_and_html_decoding(self):
        def handle(req):
            self.assertEqual(req.method, "POST")
            self.assertEqual(req.url.path, "/language/translate/v2")
            self.assertEqual(req.headers["x-goog-api-key"], "synthetic-key")
            self.assertNotIn("synthetic-key", str(req.url))
            self.assertEqual(json.loads(req.content), {"q": "Hello", "target": "vi", "format": "text", "model": "nmt"})
            return httpx.Response(200, json={"data": {"translations": [{"translatedText": "Xin chào &amp; bạn"}]}})
        self.assertEqual(self.provider(handle, cloud=True).translate(request(), "ignore"), "Xin chào & bạn")

    def test_cloud_reads_env_key_and_requires_key(self):
        with self.assertRaises(ValueError):
            self.provider(lambda r: httpx.Response(200), cloud=True, api_key="")
        with patch.dict(os.environ, {"GOOGLE_TEST_KEY": "from-env"}):
            def handle(req):
                self.assertEqual(req.headers["x-goog-api-key"], "from-env")
                self.assertEqual(json.loads(req.content)["source"], "zh-CN")
                return httpx.Response(200, json={"data": {"translations": [{"translatedText": "test"}]}})
            provider = self.provider(handle, cloud=True, api_key="", api_key_env="GOOGLE_TEST_KEY")
            self.assertEqual(provider.translate(request(source_language="zh-Hans")), "test")

    def test_rejects_spoofed_hosts_paths_and_wrong_models(self):
        for url in ("http://translate.googleapis.com", "https://translate.googleapis.com.evil.test",
                    "https://user@translate.googleapis.com", "https://translate.googleapis.com:444",
                    "https://translate.googleapis.com/path", "https://translate.googleapis.com?q=1"):
            with self.subTest(url=url):
                self.assertIsNone(self.google.infer_google_provider_type(url))
                with self.assertRaises(ValueError):
                    self.provider(lambda r: httpx.Response(200), base_url=url)
        with self.assertRaises(ValueError):
            self.provider(lambda r: httpx.Response(200), model="random")

    def test_errors_do_not_leak_text_key_or_url_and_never_fallback(self):
        for cloud in (False, True):
            for status in (403, 429, 500, 302):
                with self.subTest(cloud=cloud, status=status):
                    urls = []
                    def handle(req):
                        urls.append(req.url.host)
                        return httpx.Response(status, text="secret-source synthetic-key", headers={"Location": "https://evil.test"})
                    provider = self.provider(handle, cloud=cloud)
                    with self.assertRaises(self.google.GoogleTranslateError) as caught:
                        provider.translate(request(source_text="secret-source"))
                    self.assertNotIn("secret-source", str(caught.exception))
                    self.assertNotIn("synthetic-key", str(caught.exception))
                    self.assertEqual(len(urls), 1)
            def timeout(req):
                raise httpx.ReadTimeout(str(req.url), request=req)
            with self.assertRaises(self.google.GoogleTranslateError) as caught:
                self.provider(timeout, cloud=cloud).translate(request(source_text="secret-source"))
            self.assertNotIn("secret-source", str(caught.exception))

    def test_html_malformed_and_empty_translation_responses_fail(self):
        for cloud, payload in ((False, {}), (False, []), (False, [[[]]]),
                               (False, [[[""]]]), (True, {}), (True, {"data": {"translations": []}}),
                               (True, {"data": {"translations": [{"translatedText": ""}]}})):
            with self.subTest(cloud=cloud, payload=payload):
                with self.assertRaises(self.google.GoogleTranslateError):
                    self.provider(lambda r: httpx.Response(200, json=payload), cloud=cloud).translate(request())
        with self.assertRaises(self.google.GoogleTranslateError):
            self.provider(lambda r: httpx.Response(200, text="<html>captcha</html>")).translate(request())

    def test_long_unicode_text_stays_bounded_and_preserves_delimiters(self):
        text = ("測試內容。 Paragraph.\n\n" * 240) + "end"
        calls = []
        def handle(req):
            chunk = req.url.params["q"]
            calls.append(chunk)
            self.assertLessEqual(len(quote(chunk, safe="")), 6400)
            return httpx.Response(200, json=[[[chunk]]])
        provider = self.provider(handle)
        self.assertEqual(provider.translate(request(source_text=text)), text)
        self.assertGreater(len(calls), 1)
        with self.assertRaises(self.google.GoogleTranslateError):
            provider.translate(request(source_text="漢" * 30000))

    def test_web_request_logging_does_not_expose_source_query(self):
        old_levels = {name: logging.getLogger(name).level for name in ("httpx", "httpcore")}
        self.addCleanup(lambda: [logging.getLogger(name).setLevel(level) for name, level in old_levels.items()])
        logging.getLogger("httpx").setLevel(logging.INFO)
        provider = self.provider(lambda r: httpx.Response(200, json=[[["result"]]]))
        with self.assertLogs(level=logging.INFO) as captured:
            provider.translate(request(source_text="private-query"))
        self.assertNotIn("private-query", "\n".join(captured.output))

    def test_worker_reuses_google_cache_across_styles_prompts_but_separates_languages(self):
        calls = []
        def handle(req):
            calls.append(req.url.params["tl"])
            return httpx.Response(200, json=[[["result"]]])
        provider = self.provider(handle)
        with tempfile.TemporaryDirectory() as tmp:
            results, progress = [], []
            worker = TranslationWorker(provider, TranslationCache(Path(tmp) / "cache.db"),
                                       TranslationSection(), results.append, progress.append)
            worker._translate(request())
            worker._prompt_overrides = {"quality": {"chat": "CUSTOM {target_language}"}}
            worker._translate(request(context_preset="chat", performance_mode="quality"))
            self.assertEqual(len(calls), 1)
            self.assertTrue(results[-1].cached)
            self.assertEqual(progress, [])
            worker._translate(request(target_language="en"))
            worker._translate(request(source_language="en"))
            worker._translate(request(source_text="Another sentence"))
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(r.error is None for r in results))

    def test_worker_cache_separates_web_profiles_and_cloud_model(self):
        calls = []
        def handle(req):
            calls.append(req.url.host)
            if req.url.host == "translation.googleapis.com":
                return httpx.Response(200, json={"data": {"translations": [{"translatedText": "cloud"}]}})
            return httpx.Response(200, json=[[["web"]]])
        web = self.provider(handle)
        cloud = self.provider(handle, cloud=True)
        another = self.google.GoogleTranslateWebProvider("another-profile",
            {"base_url": "https://translate.googleapis.com"}, transport=httpx.MockTransport(handle))
        self.addCleanup(another.close)
        with tempfile.TemporaryDirectory() as tmp:
            results = []
            worker = TranslationWorker(web, TranslationCache(Path(tmp) / "cache.db"), TranslationSection(), results.append)
            for provider in (web, cloud, another):
                worker._provider = provider
                worker._translate(request())
            self.assertEqual(calls, ["translate.googleapis.com", "translation.googleapis.com", "translate.googleapis.com"])
            self.assertEqual([r.translated_text for r in results], ["web", "cloud", "web"])
            self.assertFalse(any(r.cached for r in results))


if __name__ == "__main__":
    unittest.main()
