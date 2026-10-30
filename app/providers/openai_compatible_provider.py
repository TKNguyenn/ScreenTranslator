from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.config import ProviderProfile
from app.models import RequestMode, TranslationRequest
from app.providers.base import TranslationProvider


logger = logging.getLogger(__name__)

SUPPORTED_ENDPOINT_MODES = ("responses", "chat_completions", "completions")
MODE_ALIASES = {
    "response": "responses",
    "responses": "responses",
    "chat": "chat_completions",
    "chat_completion": "chat_completions",
    "chat_completions": "chat_completions",
    "chat/completions": "chat_completions",
    "completion": "completions",
    "completions": "completions",
    "auto": "auto",
}


class ProviderHttpError(RuntimeError):
    def __init__(self, status_code: int, url: str, body: str) -> None:
        self.status_code = status_code
        self.url = url
        self.body = body
        super().__init__(f"HTTP {status_code} from {url}: {body[:800]}")


class ProviderResponseError(RuntimeError):
    pass


class OpenAICompatibleProvider(TranslationProvider):
    """
    Vendor-neutral OpenAI-compatible adapter.

    Raw HTTP is used intentionally so arbitrary model IDs, endpoint paths and
    third-party OpenAI-compatible gateways remain supported. V0.2.6 keeps native
    SSE streaming for Responses, Chat Completions and legacy Completions.
    """

    supports_explain = True

    def __init__(
        self,
        profile_name: str,
        profile: ProviderProfile,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._profile_name = profile_name
        self._profile = profile
        self._base_url = profile.base_url.rstrip("/")
        if not self._base_url:
            raise ValueError("OpenAI-compatible provider base_url cannot be empty.")
        if "YOUR_PROVIDER_HOST" in self._base_url.upper():
            raise RuntimeError(
                f"Provider profile '{profile_name}' is still using the placeholder base_url: {self._base_url}. "
                "Edit config.json and enter the real third-party API base URL."
            )

        self._model = profile.model.strip()
        if not self._model:
            raise ValueError("OpenAI-compatible provider model cannot be empty.")
        if self._model.upper() == "YOUR_MODEL_ID":
            raise RuntimeError(
                f"Provider profile '{profile_name}' is still using model=YOUR_MODEL_ID. "
                "Edit config.json and enter the exact model ID exposed by your gateway."
            )

        self._endpoint_mode = self._normalize_mode(profile.endpoint_mode)
        self._resolved_auto_mode: str | None = None
        direct_key = str(profile.api_key or "").strip()
        env_key = os.getenv(profile.api_key_env, "").strip() if profile.api_key_env else ""
        self._api_key = direct_key or env_key
        placeholder_key = self._api_key.lower().startswith("replace_me")
        if (not self._api_key or placeholder_key) and not profile.allow_no_api_key:
            env_name = profile.api_key_env or "<empty api_key_env>"
            raise RuntimeError(
                f"API key is missing/not configured for provider profile '{profile_name}'. "
                f"Enter api_key in config/app, set {env_name} in .env, or set "
                "allow_no_api_key=true only for a local gateway."
            )

        timeout = httpx.Timeout(profile.timeout_s, connect=profile.connect_timeout_s)
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=60.0,
        )
        self._client = httpx.Client(
            timeout=timeout,
            verify=profile.verify_ssl,
            follow_redirects=True,
            limits=limits,
            transport=transport,
        )

        fingerprint_material = json.dumps(
            {
                "profile": profile_name,
                "base_url": self._base_url,
                "endpoint_mode": self._endpoint_mode,
                "endpoint_paths": profile.endpoint_paths,
                "auto_order": profile.auto_order,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        fingerprint = hashlib.sha256(fingerprint_material.encode("utf-8")).hexdigest()[:12]
        self._provider_id = f"openai_compatible:{profile_name}:{fingerprint}"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def model_id(self) -> str:
        return self._model

    def streaming_override_for(self, performance_mode: str) -> bool | None:
        return self._profile.streaming_override_for(performance_mode)

    def translate(self, request: TranslationRequest, instructions: str) -> str:
        return self._translate_across_modes(
            request=request,
            instructions=instructions,
            streaming=False,
            on_delta=None,
        )

    def translate_stream(
        self,
        request: TranslationRequest,
        instructions: str,
        on_delta: Callable[[str], None],
    ) -> str:
        return self._translate_across_modes(
            request=request,
            instructions=instructions,
            streaming=True,
            on_delta=on_delta,
        )

    def _translate_across_modes(
        self,
        request: TranslationRequest,
        instructions: str,
        streaming: bool,
        on_delta: Callable[[str], None] | None,
    ) -> str:
        modes = self._candidate_modes()
        if request.mode == RequestMode.EXPLAIN:
            modes = tuple(mode for mode in modes if mode != "completions")
            if not modes:
                raise ValueError("Explain cần Chat Completions hoặc Responses. Hãy cấu hình trong Provider & Model.")
        failures: list[str] = []

        for index, mode in enumerate(modes):
            try:
                if streaming:
                    assert on_delta is not None
                    translated = self._call_endpoint_stream(
                        mode,
                        request,
                        instructions,
                        on_delta,
                    )
                else:
                    translated = self._call_endpoint(mode, request, instructions)
                if self._endpoint_mode == "auto":
                    self._resolved_auto_mode = mode
                return translated
            except ProviderHttpError as exc:
                failures.append(str(exc))
                if index < len(modes) - 1 and self._endpoint_unsupported(exc):
                    logger.info(
                        "Provider profile %s does not support endpoint mode %s; trying fallback",
                        self._profile_name,
                        mode,
                    )
                    continue
                if streaming and self._streaming_unsupported(exc):
                    logger.info(
                        "Provider profile %s rejected streaming for %s; retrying the same endpoint without streaming",
                        self._profile_name,
                        mode,
                    )
                    translated = self._call_endpoint(mode, request, instructions)
                    if on_delta is not None and translated:
                        on_delta(translated)
                    if self._endpoint_mode == "auto":
                        self._resolved_auto_mode = mode
                    return translated
                raise
            except ProviderResponseError as exc:
                failures.append(f"{mode}: {exc}")
                if request.mode != RequestMode.EXPLAIN and self._endpoint_mode == "auto" and index < len(modes) - 1:
                    logger.info(
                        "Provider profile %s returned an incompatible %s response; trying fallback",
                        self._profile_name,
                        mode,
                    )
                    continue
                raise

        raise RuntimeError("All configured endpoint modes failed: " + " | ".join(failures))

    def close(self) -> None:
        self._client.close()

    def _candidate_modes(self) -> tuple[str, ...]:
        if self._endpoint_mode != "auto":
            return (self._endpoint_mode,)

        normalized: list[str] = []
        if self._resolved_auto_mode:
            normalized.append(self._resolved_auto_mode)
        for mode in self._profile.auto_order:
            value = self._normalize_mode(mode)
            if value != "auto" and value not in normalized:
                normalized.append(value)
        return tuple(normalized) or SUPPORTED_ENDPOINT_MODES

    def _call_endpoint(
        self,
        mode: str,
        request: TranslationRequest,
        instructions: str,
    ) -> str:
        url = self._build_url(mode)
        payload = self._build_payload(mode, request, instructions, streaming=False)
        headers = self._build_headers(streaming=False)
        started = time.perf_counter()

        logger.info(
            "Translation request provider=%s mode=%s model=%s stream=off chars=%d",
            self._profile_name,
            mode,
            self._model,
            len(request.source_text),
        )

        try:
            response = self._client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Network error calling provider profile '{self._profile_name}' at {url}: {exc}"
            ) from exc

        if response.status_code < 200 or response.status_code >= 300:
            body = self._safe_error_body(response)
            raise ProviderHttpError(response.status_code, url, body)

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                f"Provider returned non-JSON data from {url}: {response.text[:500]}"
            ) from exc

        text = self._extract_text(mode, data).strip()
        if not text:
            raise ProviderResponseError(
                f"Provider returned no translated text for mode '{mode}'."
            )

        logger.info(
            "Translation completed provider=%s mode=%s stream=off total=%.3fs",
            self._profile_name,
            mode,
            time.perf_counter() - started,
        )
        return text

    def _call_endpoint_stream(
        self,
        mode: str,
        request: TranslationRequest,
        instructions: str,
        on_delta: Callable[[str], None],
    ) -> str:
        url = self._build_url(mode)
        payload = self._build_payload(mode, request, instructions, streaming=True)
        headers = self._build_headers(streaming=True)
        started = time.perf_counter()
        first_delta_at: float | None = None

        logger.info(
            "Translation request provider=%s mode=%s model=%s stream=on chars=%d",
            self._profile_name,
            mode,
            self._model,
            len(request.source_text),
        )

        try:
            with self._client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    response.read()
                    body = self._safe_error_body(response)
                    raise ProviderHttpError(response.status_code, url, body)

                content_type = response.headers.get("content-type", "").lower()
                if "text/event-stream" not in content_type:
                    # Some compatible gateways ignore stream=true and return one
                    # normal JSON response. Accept that rather than failing.
                    response.read()
                    try:
                        data = response.json()
                    except ValueError as exc:
                        raise ProviderResponseError(
                            f"Streaming request returned non-SSE/non-JSON data from {url}: {response.text[:500]}"
                        ) from exc
                    text = self._extract_text(mode, data).strip()
                    if not text:
                        raise ProviderResponseError(
                            f"Provider returned no translated text for mode '{mode}'."
                        )
                    on_delta(text)
                    logger.info(
                        "Translation completed provider=%s mode=%s stream=requested-but-buffered total=%.3fs",
                        self._profile_name,
                        mode,
                        time.perf_counter() - started,
                    )
                    return text

                pieces: list[str] = []
                last_json: dict[str, Any] | None = None

                for line in response.iter_lines():
                    if not line:
                        continue
                    stripped = line.strip()
                    if not stripped or stripped.startswith(":") or stripped.startswith("event:"):
                        continue
                    if not stripped.startswith("data:"):
                        continue

                    raw_data = stripped[5:].strip()
                    if not raw_data or raw_data == "[DONE]":
                        if raw_data == "[DONE]":
                            break
                        continue

                    try:
                        event_data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        logger.debug("Ignoring non-JSON SSE data from %s: %s", url, raw_data[:300])
                        continue
                    if not isinstance(event_data, dict):
                        continue
                    last_json = event_data

                    delta = self._extract_stream_delta(mode, event_data)
                    if not delta:
                        continue
                    if first_delta_at is None:
                        first_delta_at = time.perf_counter()
                        logger.info(
                            "Translation first token provider=%s mode=%s ttft=%.3fs",
                            self._profile_name,
                            mode,
                            first_delta_at - started,
                        )
                    pieces.append(delta)
                    on_delta(delta)

                text = "".join(pieces).strip()
                if not text and last_json is not None:
                    # Compatibility fallback for gateways that wrap a complete
                    # response JSON in one SSE event instead of deltas.
                    try:
                        text = self._extract_text(mode, last_json).strip()
                    except ProviderResponseError:
                        text = ""
                    if text:
                        on_delta(text)

                if not text:
                    raise ProviderResponseError(
                        f"Provider streaming response contained no translated text for mode '{mode}'."
                    )

                logger.info(
                    "Translation completed provider=%s mode=%s stream=on total=%.3fs",
                    self._profile_name,
                    mode,
                    time.perf_counter() - started,
                )
                return text
        except ProviderHttpError:
            raise
        except ProviderResponseError:
            raise
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Network error calling provider profile '{self._profile_name}' at {url}: {exc}"
            ) from exc

    def _build_url(self, mode: str) -> str:
        path = self._profile.endpoint_paths.get(mode)
        if not path:
            raise ValueError(f"No endpoint path configured for mode '{mode}'.")
        return f"{self._base_url}/{path.lstrip('/')}"

    def _build_headers(self, streaming: bool = False) -> dict[str, str]:
        headers = {
            "Accept": "text/event-stream, application/json" if streaming else "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        headers.update(self._profile.extra_headers)
        return headers

    def _build_payload(
        self,
        mode: str,
        request: TranslationRequest,
        instructions: str,
        streaming: bool = False,
    ) -> dict[str, Any]:
        user_text = (json.dumps({"selected_text": request.source_text}, ensure_ascii=False)
                     if request.mode == RequestMode.EXPLAIN else request.source_text)
        if mode == "responses":
            payload: dict[str, Any] = {
                "model": self._model,
                "instructions": instructions,
                "input": user_text,
            }
            if self._profile.max_output_tokens is not None:
                payload["max_output_tokens"] = self._profile.max_output_tokens
        elif mode == "chat_completions":
            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_text},
                ],
            }
            if self._profile.max_output_tokens is not None:
                # max_tokens remains the broadest third-party-compatible field.
                # Gateways that require max_completion_tokens can override it via
                # endpoint_extra_body and leave max_output_tokens unset.
                payload["max_tokens"] = self._profile.max_output_tokens
        elif mode == "completions":
            payload = {
                "model": self._model,
                "prompt": (
                    f"{instructions}\n\n"
                    "Text to translate:\n"
                    f"{request.source_text}\n\n"
                    "Translation:"
                ),
            }
            if self._profile.max_output_tokens is not None:
                payload["max_tokens"] = self._profile.max_output_tokens
        else:
            raise ValueError(f"Unsupported endpoint mode: {mode}")

        if self._profile.temperature is not None:
            payload["temperature"] = self._profile.temperature
        if streaming:
            payload["stream"] = True

        self._merge_extra_payload(payload, self._profile.extra_body, mode)
        endpoint_extra = self._profile.endpoint_extra_body.get(mode, {})
        self._merge_extra_payload(payload, endpoint_extra, mode)
        return payload

    @staticmethod
    def _merge_extra_payload(
        payload: dict[str, Any],
        extra: dict[str, Any],
        mode: str,
    ) -> None:
        if not extra:
            return
        protected_by_mode = {
            "responses": {"model", "instructions", "input"},
            "chat_completions": {"model", "messages"},
            "completions": {"model", "prompt"},
        }
        protected = set(protected_by_mode[mode])
        if "stream" in payload:
            protected.add("stream")
        collisions = sorted(protected.intersection(extra))
        if collisions:
            raise ValueError(
                "extra_body/endpoint_extra_body cannot override core OpenAI-compatible fields: "
                + ", ".join(collisions)
            )
        payload.update(extra)

    @classmethod
    def _extract_text(cls, mode: str, data: Any) -> str:
        if not isinstance(data, dict):
            raise ProviderResponseError("Provider response JSON is not an object.")
        if mode == "responses":
            return cls._extract_responses_text(data)
        if mode == "chat_completions":
            return cls._extract_chat_text(data)
        if mode == "completions":
            return cls._extract_completions_text(data)
        raise ProviderResponseError(f"Cannot parse unsupported endpoint mode '{mode}'.")

    @classmethod
    def _extract_stream_delta(cls, mode: str, data: dict[str, Any]) -> str:
        """Extract one text delta from common OpenAI-compatible SSE shapes."""
        if mode == "responses":
            event_type = str(data.get("type", ""))
            if event_type in {"response.output_text.delta", "response.refusal.delta"}:
                delta = data.get("delta")
                return delta if isinstance(delta, str) else ""
            # Some gateways send a top-level delta without a type field.
            delta = data.get("delta")
            if isinstance(delta, str):
                return delta
            # Others proxy Chat Completions chunks from /responses.
            if isinstance(data.get("choices"), list):
                return cls._extract_chat_stream_delta(data)
            return ""

        if mode == "chat_completions":
            return cls._extract_chat_stream_delta(data)

        if mode == "completions":
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                return ""
            first = choices[0]
            if not isinstance(first, dict):
                return ""
            text = first.get("text")
            return text if isinstance(text, str) else ""

        return ""

    @classmethod
    def _extract_chat_stream_delta(cls, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""

        delta = first.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            pieces = cls._text_pieces(content)
            if pieces:
                return "".join(pieces)

        # Compatibility with old completions-like chunks.
        text = first.get("text")
        return text if isinstance(text, str) else ""

    @classmethod
    def _extract_responses_text(cls, data: dict[str, Any]) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct

        pieces: list[str] = []
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                pieces.extend(cls._text_pieces(content))

        if pieces:
            return "\n".join(piece for piece in pieces if piece.strip())

        # Some compatible gateways return a Chat Completions-like object even
        # when the URL is /responses. Accept it as a compatibility fallback.
        try:
            return cls._extract_chat_text(data)
        except ProviderResponseError:
            pass

        raise ProviderResponseError("No output text found in Responses-style JSON.")

    @classmethod
    def _extract_chat_text(cls, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderResponseError("No choices found in Chat Completions JSON.")
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderResponseError("Invalid first choice in Chat Completions JSON.")

        message = first.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            pieces = cls._text_pieces(content)
            if pieces:
                return "\n".join(pieces)

        text = first.get("text")
        if isinstance(text, str):
            return text
        raise ProviderResponseError("No message.content found in Chat Completions JSON.")

    @staticmethod
    def _extract_completions_text(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderResponseError("No choices found in Completions JSON.")
        first = choices[0]
        if not isinstance(first, dict) or not isinstance(first.get("text"), str):
            raise ProviderResponseError("No choices[0].text found in Completions JSON.")
        return first["text"]

    @staticmethod
    def _text_pieces(content: Any) -> list[str]:
        pieces: list[str] = []
        if isinstance(content, str):
            return [content]
        if not isinstance(content, list):
            return pieces

        for part in content:
            if isinstance(part, str):
                pieces.append(part)
                continue
            if not isinstance(part, dict):
                continue

            text = part.get("text")
            if isinstance(text, str):
                pieces.append(text)
            elif isinstance(text, dict):
                value = text.get("value")
                if isinstance(value, str):
                    pieces.append(value)

            value = part.get("content")
            if isinstance(value, str):
                pieces.append(value)
        return pieces

    @staticmethod
    def _safe_error_body(response: httpx.Response) -> str:
        try:
            data = response.json()
            return json.dumps(data, ensure_ascii=False)[:1200]
        except ValueError:
            return response.text[:1200]

    @staticmethod
    def _endpoint_unsupported(error: ProviderHttpError) -> bool:
        if error.status_code in {404, 405, 501}:
            return True
        if error.status_code not in {400, 422}:
            return False
        body = error.body.lower()
        endpoint_markers = (
            "unknown endpoint",
            "unsupported endpoint",
            "endpoint not found",
            "unknown route",
            "route not found",
            "method not allowed",
            "invalid endpoint",
        )
        return any(marker in body for marker in endpoint_markers)

    @staticmethod
    def _streaming_unsupported(error: ProviderHttpError) -> bool:
        if error.status_code not in {400, 404, 405, 422, 501}:
            return False
        body = error.body.lower()
        if "stream" not in body:
            return False
        markers = (
            "unsupported",
            "not supported",
            "not available",
            "unknown field",
            "unrecognized field",
            "invalid parameter",
            "invalid field",
        )
        return any(marker in body for marker in markers)

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        normalized = MODE_ALIASES.get(str(mode).strip().lower())
        if normalized is None:
            supported = ", ".join(("auto",) + SUPPORTED_ENDPOINT_MODES)
            raise ValueError(f"Unsupported endpoint_mode '{mode}'. Supported: {supported}")
        return normalized
