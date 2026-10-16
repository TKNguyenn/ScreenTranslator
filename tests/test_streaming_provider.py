from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import httpx

from app.config import ProviderProfile
from app.models import RequestMode, TranslationRequest
from app.providers.openai_compatible_provider import OpenAICompatibleProvider


def make_request(mode: str = "ultra_fast") -> TranslationRequest:
    return TranslationRequest(
        job_id="stream-job",
        source_text="hello",
        source_language="en",
        target_language="vi",
        context_preset="engineering",
        performance_mode=mode,
        mode=RequestMode.POPUP,
        foreground_hwnd=None,
    )


class StreamingProviderTests(unittest.TestCase):
    def test_chat_completions_sse_stream(self) -> None:
        seen_payload: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            seen_payload.update(json.loads(req.content.decode("utf-8")))
            body = (
                'data: {"choices":[{"delta":{"content":"xin "}}]}\n\n'
                'data: {"choices":[{"delta":{"content":"chao"}}]}\n\n'
                'data: [DONE]\n\n'
            )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=body.encode("utf-8"),
            )

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="deepseek-test",
            endpoint_mode="chat_completions",
        )
        deltas: list[str] = []
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "chat-stream", profile, transport=httpx.MockTransport(handler)
            )
            try:
                text = provider.translate_stream(make_request(), "translate", deltas.append)
            finally:
                provider.close()

        self.assertTrue(seen_payload["stream"])
        self.assertEqual(text, "xin chao")
        self.assertEqual(deltas, ["xin ", "chao"])

    def test_responses_sse_stream(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            payload = json.loads(req.content.decode("utf-8"))
            self.assertTrue(payload["stream"])
            body = (
                'event: response.output_text.delta\n'
                'data: {"type":"response.output_text.delta","delta":"xin "}\n\n'
                'event: response.output_text.delta\n'
                'data: {"type":"response.output_text.delta","delta":"chao"}\n\n'
                'event: response.completed\n'
                'data: {"type":"response.completed"}\n\n'
            )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream; charset=utf-8"},
                content=body.encode("utf-8"),
            )

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="gpt-test",
            endpoint_mode="responses",
        )
        deltas: list[str] = []
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "responses-stream", profile, transport=httpx.MockTransport(handler)
            )
            try:
                text = provider.translate_stream(make_request(), "translate", deltas.append)
            finally:
                provider.close()

        self.assertEqual(text, "xin chao")
        self.assertEqual(deltas, ["xin ", "chao"])

    def test_stream_request_accepts_buffered_json_gateway(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            payload = json.loads(req.content.decode("utf-8"))
            self.assertTrue(payload["stream"])
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"choices": [{"message": {"content": "xin chao"}}]},
            )

        profile = ProviderProfile(
            base_url="https://gateway.test/v1",
            api_key_env="TEST_KEY",
            model="qwen-test",
            endpoint_mode="chat_completions",
        )
        deltas: list[str] = []
        with patch.dict(os.environ, {"TEST_KEY": "secret"}):
            provider = OpenAICompatibleProvider(
                "buffered", profile, transport=httpx.MockTransport(handler)
            )
            try:
                text = provider.translate_stream(make_request(), "translate", deltas.append)
            finally:
                provider.close()

        self.assertEqual(text, "xin chao")
        self.assertEqual(deltas, ["xin chao"])


if __name__ == "__main__":
    unittest.main()
