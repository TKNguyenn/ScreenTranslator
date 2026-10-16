from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import httpx

from app.config import ProviderProfile
from app.models import RequestMode, TranslationRequest
from app.providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
    ProviderHttpError,
)


def request(text: str = "hello") -> TranslationRequest:
    return TranslationRequest(
        job_id="job-1",
        source_text=text,
        source_language="en",
        target_language="vi",
        context_preset="engineering",
        performance_mode="fast",
        mode=RequestMode.POPUP,
        foreground_hwnd=None,
    )


class OpenAICompatibleProviderTests(unittest.TestCase):
    def test_parse_responses_direct_output_text(self) -> None:
        data = {"output_text": "xin chao"}
        self.assertEqual(
            OpenAICompatibleProvider._extract_text("responses", data),
            "xin chao",
        )

    def test_parse_responses_nested_output(self) -> None:
        data = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "xin chao"}
                    ],
                }
            ]
        }
        self.assertEqual(
            OpenAICompatibleProvider._extract_text("responses", data),
            "xin chao",
        )

    def test_parse_chat_completions(self) -> None:
        data = {"choices": [{"message": {"role": "assistant", "content": "xin chao"}}]}
        self.assertEqual(
            OpenAICompatibleProvider._extract_text("chat_completions", data),
            "xin chao",
        )

    def test_parse_completions(self) -> None:
        data = {"choices": [{"text": "xin chao"}]}
        self.assertEqual(
            OpenAICompatibleProvider._extract_text("completions", data),
            "xin chao",
        )

    def test_arbitrary_deepseek_model_id_is_sent_unchanged(self) -> None:
        seen = {}

        def handler(req: httpx.Request) -> httpx.Response:
            seen["path"] = req.url.path
            seen["json"] = json.loads(req.content.decode("utf-8"))
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="deepseek-v3-custom",
            endpoint_mode="chat_completions",
        )
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "deepseek", profile, transport=httpx.MockTransport(handler)
            )
            try:
                self.assertEqual(provider.translate(request(), "translate"), "ok")
            finally:
                provider.close()

        self.assertEqual(seen["path"], "/v1/chat/completions")
        self.assertEqual(seen["json"]["model"], "deepseek-v3-custom")

    def test_arbitrary_glm_model_id_is_sent_unchanged(self) -> None:
        seen = {}

        def handler(req: httpx.Request) -> httpx.Response:
            seen["json"] = json.loads(req.content.decode("utf-8"))
            return httpx.Response(200, json={"output_text": "ok"})

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="glm-future-model",
            endpoint_mode="responses",
        )
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "glm", profile, transport=httpx.MockTransport(handler)
            )
            try:
                self.assertEqual(provider.translate(request(), "translate"), "ok")
            finally:
                provider.close()

        self.assertEqual(seen["json"]["model"], "glm-future-model")

    def test_custom_singular_response_path(self) -> None:
        seen_paths: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            seen_paths.append(req.url.path)
            return httpx.Response(200, json={"output_text": "ok"})

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="any-model",
            endpoint_mode="responses",
            endpoint_paths={
                "responses": "/response",
                "chat_completions": "/chat/completions",
                "completions": "/completions",
            },
        )
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "singular", profile, transport=httpx.MockTransport(handler)
            )
            try:
                self.assertEqual(provider.translate(request(), "translate"), "ok")
            finally:
                provider.close()

        self.assertEqual(seen_paths, ["/v1/response"])

    def test_auto_fallback_responses_404_to_chat(self) -> None:
        seen_paths: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            seen_paths.append(req.url.path)
            if req.url.path.endswith("/responses"):
                return httpx.Response(404, json={"error": {"message": "route not found"}})
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="model-x",
            endpoint_mode="auto",
            auto_order=("responses", "chat_completions", "completions"),
        )
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "auto", profile, transport=httpx.MockTransport(handler)
            )
            try:
                self.assertEqual(provider.translate(request(), "translate"), "ok")
            finally:
                provider.close()

        self.assertEqual(seen_paths, ["/v1/responses", "/v1/chat/completions"])

    def test_auto_does_not_fallback_on_401(self) -> None:
        seen_paths: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            seen_paths.append(req.url.path)
            return httpx.Response(401, json={"error": {"message": "invalid key"}})

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="model-x",
            endpoint_mode="auto",
        )
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "auto", profile, transport=httpx.MockTransport(handler)
            )
            try:
                with self.assertRaises(ProviderHttpError):
                    provider.translate(request(), "translate")
            finally:
                provider.close()

        self.assertEqual(seen_paths, ["/v1/responses"])

    def test_no_auth_local_gateway(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            self.assertNotIn("authorization", req.headers)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        profile = ProviderProfile(
            base_url="http://local.test/v1",
            api_key_env="",
            allow_no_api_key=True,
            model="local-model",
            endpoint_mode="chat_completions",
        )
        provider = OpenAICompatibleProvider(
            "local", profile, transport=httpx.MockTransport(handler)
        )
        try:
            self.assertEqual(provider.translate(request(), "translate"), "ok")
        finally:
            provider.close()

    def test_protected_fields_cannot_be_overridden(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"output_text": "ok"})

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="model-x",
            endpoint_mode="responses",
            extra_body={"model": "evil-override"},
        )
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "bad-extra", profile, transport=httpx.MockTransport(handler)
            )
            try:
                with self.assertRaises(ValueError):
                    provider.translate(request(), "translate")
            finally:
                provider.close()

    def test_provider_fingerprint_changes_with_base_url(self) -> None:
        p1 = ProviderProfile(
            base_url="https://a.test/v1",
            api_key_env="",
            allow_no_api_key=True,
            model="same-model",
        )
        p2 = ProviderProfile(
            base_url="https://b.test/v1",
            api_key_env="",
            allow_no_api_key=True,
            model="same-model",
        )
        provider1 = OpenAICompatibleProvider("same", p1, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"output_text": "x"})))
        provider2 = OpenAICompatibleProvider("same", p2, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"output_text": "x"})))
        try:
            self.assertNotEqual(provider1.provider_id, provider2.provider_id)
        finally:
            provider1.close()
            provider2.close()


if __name__ == "__main__":
    unittest.main()


class AutoEndpointLearningTests(unittest.TestCase):
    def test_auto_mode_remembers_successful_fallback_endpoint(self) -> None:
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path.endswith("/responses"):
                return httpx.Response(404, json={"error": "not found"})
            return httpx.Response(200, json={"choices": [{"message": {"content": "xin chao"}}]})

        profile = ProviderProfile(
            base_url="https://example.test/v1",
            api_key_env="",
            allow_no_api_key=True,
            model="deepseek-chat",
            endpoint_mode="auto",
        )
        provider = OpenAICompatibleProvider(
            "test", profile, transport=httpx.MockTransport(handler)
        )
        try:
            first = provider.translate(request(), "translate")
            second = provider.translate(request(), "translate")
        finally:
            provider.close()

        self.assertEqual(first, "xin chao")
        self.assertEqual(second, "xin chao")
        self.assertEqual(calls.count("/v1/responses"), 1)
        self.assertEqual(calls.count("/v1/chat/completions"), 2)

