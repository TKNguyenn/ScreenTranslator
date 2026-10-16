"""Standalone Google Translate adapters for AI Screen Translator.

================================================================================
CODEX INTEGRATION HANDOFF (read BEFORE modifying the user's project)
================================================================================

GOAL
    Integrate *both* Google Translate Web (unofficial, no API key) and Google
    Cloud Translation Basic v2 (official, API key) into the user's CURRENT
    ScreenTranslator repository. Their working copy diverged from V0.4.1.3.
    DO NOT replace main.py, config.py, worker, UI, providers.json or other
    already-modified files with an old version. Inspect and make targeted edits.

THIS FILE IS STANDALONE
    Runtime dependency: httpx (already used by the original ScreenTranslator).
    No imports from the user's ``app`` package, PySide6, or comtypes.
    ``profile`` may be an object (e.g. ProviderProfile dataclass) or dict.
    ``request`` may be an object (e.g. TranslationRequest) or dict.
    The two provider classes duck-type the V0.4.1.x TranslationProvider API:
        .provider_id, .model_id, .translate(request, instructions),
        .translate_stream(request, instructions, on_delta),
        .streaming_override_for(mode), .cache_scope(request, instructions),
        .close()
    If the current project requires subclassing its TranslationProvider ABC,
    add that superclass when integrating, without changing business behavior.

REQUIRED INTEGRATION POINTS
    1. Place this file at ``app/providers/google_translate_addon.py`` (or
       adapt the import path to the user's current repository).
    2. In the existing provider factory, import GoogleTranslateWebProvider,
       GoogleCloudTranslationProvider and infer_google_provider_type from here.
       Route ``google_translate_web`` to the first class and
       ``google_cloud_translate`` to the second; keep all original providers.
       Example inside existing factory AFTER current profile is resolved:
           if kind == 'google_translate_web':
               return GoogleTranslateWebProvider(name, profile)
           if kind == 'google_cloud_translate':
               return GoogleCloudTranslationProvider(name, profile)
       Avoid reusing OpenAI-compatible chat/responses payloads for Google.
    3. Keep portable ``providers.json`` with exactly base_url, api_key, models
       for each provider. Add two presets via GUI or catalog *without wiping
       any existing entries*:
           'Google Translate Free': {
               'base_url': 'https://translate.googleapis.com',
               'api_key': '', 'models': ['google-translate']},
           'Google Cloud Translate': {
               'base_url': 'https://translation.googleapis.com',
               'api_key': '', 'models': ['nmt']}
       Cloud entry is optional until user enters their key. DO NOT hardcode a
       live key. Do not make Cloud the active provider until properly set up.
    4. In catalog -> runtime profile resolution, call
       infer_google_provider_type(base_url) for canonical Google hostnames so
       portable catalog works WITHOUT app-specific config copying. Preserve
       explicitly supported config overrides and all non-Google providers.
       Keep model as first item unless the user's active model is valid.
    5. Add or adapt Provider Manager controls to add both presets and select
       provider type. Use GOOGLE_PROVIDER_PRESETS as a template. The user must
       still be able to rename/remove them via GUI and save providers.json.
       For Google, mark prompt / Engineer / Chat / Email / streaming / endpoint
       mode / alternative models as irrelevant. Existing global app settings
       should not be deleted or changed when switching away from Google.
    6. Route translations through the EXISTING translation worker / UI /
       selection / Quick UX / Region OCR / cache, not a duplicate pipeline.
       ``streaming_override_for()`` returns False; Google is non-streaming.
       ``cache_scope()`` returns a provider-neutral prompt scope so Google's
       results are reused across speed/style. Cache must STILL distinguish
       source/target language, provider ID, model ID and source text.
       If current worker lacks the hooks, extend it conditionally using
       getattr(provider, 'cache_scope', None) and
       getattr(provider, 'streaming_override_for', None) so existing third-
       party providers remain compatible. Do not modify AI prompt cache rules.
    7. Provider Test button should send a short REAL translation, e.g.
       Hello -> Xin chao (English to Vietnamese), NOT a prompt asking for 'OK'.
    8. Never silently fallback from free Web to paid Cloud. Cloud Translation
       requires enabled Cloud Translation API, project/billing, and API key.
       Cloud key is sent in X-goog-api-key header, never in query URL.
    9. Do not log URLs/text/headers/API keys. In particular Google Web uses a
       GET query with plaintext selected text (not suitable for confidential
       text without authorization). Preserve sanitization on request failures.
       GoogleTranslateWebProvider suppresses httpx/httpcore request logging
       process-wide so original GET URLs cannot be written by httpx INFO.
       Do not turn those loggers back to INFO/DEBUG without URL redaction.
    10. Add offline tests using httpx.MockTransport for response parsing,
        language aliases, missing Cloud key, 403/429, HTML, streaming OFF,
        cache scope, and provider type inference. Run existing test suite too.
        Then do a Windows UI smoke test; no live endpoint check is included.

CONFIG REFERENCE (NOT written automatically by this module)
    providers.json (portable, 3 fields only):
        {
          "Google Translate Free": {
            "base_url": "https://translate.googleapis.com",
            "api_key": "",
            "models": ["google-translate"]
          },
          "Google Cloud Translate": {
            "base_url": "https://translation.googleapis.com",
            "api_key": "",
            "models": ["nmt"]
          }
        }
    Optional app-only profile overrides in config.json:
        type: google_translate_web | google_cloud_translate
        timeout_s: 45
        api_key_env: GOOGLE_CLOUD_TRANSLATE_API_KEY (optional; read environment)
    Do not put these app-specific settings into portable providers.json.

LIMITATIONS
    Web endpoint /translate_a/single?client=gtx is unofficial and may stop,
    captcha, rate-limit, or return unexpected content. No guaranteed free quota.
    Official Cloud Translation Basic v2 is metered and may incur charges;
    free allowances are not a hard spending cap. Neither endpoint is an LLM,
    supports a user prompt, or streams tokens.
================================================================================
"""

from __future__ import annotations

import hashlib
import html
import logging
import os
from typing import Any, Callable
from urllib.parse import quote, urlsplit

import httpx


__all__ = [
    "GOOGLE_WEB_URL",
    "GOOGLE_CLOUD_URL",
    "GOOGLE_WEB_MODEL",
    "GOOGLE_CLOUD_MODEL",
    "GOOGLE_PROVIDER_PRESETS",
    "GoogleTranslateError",
    "GoogleTranslateWebProvider",
    "GoogleCloudTranslationProvider",
    "infer_google_provider_type",
    "create_google_provider",
]

logger = logging.getLogger(__name__)
GOOGLE_WEB_URL = "https://translate.googleapis.com"
GOOGLE_CLOUD_URL = "https://translation.googleapis.com"
GOOGLE_WEB_MODEL = "google-translate"
GOOGLE_CLOUD_MODEL = "nmt"

# Portable entries deliberately contain exactly 3 fields, as per V0.3.1+.
GOOGLE_PROVIDER_PRESETS: dict[str, dict[str, str | list[str]]] = {
    "Google Translate Free": {
        "base_url": GOOGLE_WEB_URL,
        "api_key": "",
        "models": [GOOGLE_WEB_MODEL],
    },
    "Google Cloud Translate": {
        "base_url": GOOGLE_CLOUD_URL,
        "api_key": "",
        "models": [GOOGLE_CLOUD_MODEL],
    },
}


class GoogleTranslateError(RuntimeError):
    """Sanitized user-facing error; MUST NOT contain source text or API key."""


def _field(obj: Any, name: str, fallback: Any = None) -> Any:
    """Accept the user's possibly modified dataclass OR mapping interfaces."""
    return obj.get(name, fallback) if isinstance(obj, dict) else getattr(obj, name, fallback)


def infer_google_provider_type(base_url: str) -> str | None:
    """Exact Google hostnames only. Return None for all other providers.

    IMPORTANT: ``infer_portable_provider_type`` in the original app returns
    'openai_compatible' for non-Google URLs. The caller must preserve that
    fallback (or any newer provider routing) in its own config module.
    """
    try:
        parsed = urlsplit(str(base_url).strip())
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 443):
            return None
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return None
        if parsed.hostname == "translate.googleapis.com":
            return "google_translate_web"
        if parsed.hostname == "translation.googleapis.com":
            return "google_cloud_translate"
    except ValueError:
        pass
    return None


def _validate_google_base_url(base_url: str, expected_host: str) -> str:
    url = str(base_url).strip().rstrip("/")
    kind = infer_google_provider_type(url)
    expected = (
        "google_translate_web" if expected_host == "translate.googleapis.com"
        else "google_cloud_translate"
    )
    if kind != expected:
        raise ValueError(
            f"Google provider chỉ chấp nhận https://{expected_host} "
            "(không dùng proxy/domain lạ để bảo vệ dữ liệu và API key)."
        )
    return url


def _google_language(code: str, *, source: bool = False) -> str:
    normalized = str(code or "").strip().replace("_", "-")
    if source and (not normalized or normalized.lower() in {"auto", "auto-detect"}):
        return "auto"
    if not normalized or normalized.lower() in {"auto", "auto-detect"}:
        raise GoogleTranslateError("Ngôn ngữ đích không hợp lệ: auto.")
    aliases = {
        "zh-hant": "zh-TW",
        "zh-hans": "zh-CN",
        "zh-tw": "zh-TW",
        "zh-cn": "zh-CN",
    }
    return aliases.get(normalized.lower(), normalized.lower())


def _extract_google_web_translation(payload: Any) -> str:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        raise GoogleTranslateError("Google Translate Web trả về dữ liệu không đúng định dạng.")
    segments = [
        unit[0] for unit in payload[0]
        if isinstance(unit, (tuple, list)) and unit and isinstance(unit[0], str)
    ]
    if not segments:
        raise GoogleTranslateError("Google Translate Web không trả về bản dịch.")
    return "".join(segments)


def _split_google_web_text(
    text: str, limit: int = 1800, max_chunks: int = 12
) -> list[tuple[str, str]]:
    """Bound GET query to <= 6400 percent-encoded bytes per chunk.

    Preserve split delimiters (esp. whitespace/newlines) as joiners, without
    translating the same delimiter twice. Very long text fails explicitly;
    no automatic migration to a billable provider.
    """
    def allowed_prefix(source: str) -> int:
        upper = min(len(source), limit)
        low, high = 1, upper
        while low < high:
            mid = (low + high + 1) // 2
            if len(quote(source[:mid], safe="")) <= 6400:
                low = mid
            else:
                high = mid - 1
        return low

    chunks: list[tuple[str, str]] = []
    remaining = text
    while len(remaining) > limit or len(quote(remaining, safe="")) > 6400:
        ceiling = allowed_prefix(remaining)
        candidates: list[tuple[int, str]] = []
        for sep in ("\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "; ", " "):
            idx = remaining.rfind(sep, int(ceiling * 0.55), ceiling)
            if idx >= 0:
                candidates.append((idx, sep))
        if candidates:
            pos, sep = max(candidates, key=lambda item: item[0])
            cut = pos + len(sep)
            suffix_len = len(sep) - len(sep.rstrip())
            part = remaining[:cut - suffix_len] if suffix_len else remaining[:cut]
            joiner = sep[-suffix_len:] if suffix_len else ""
            if not part:
                part, joiner, cut = remaining[:ceiling], "", ceiling
        else:
            part, joiner, cut = remaining[:ceiling], "", ceiling
        chunks.append((part, joiner))
        if len(chunks) >= max_chunks:
            raise GoogleTranslateError(
                "Đoạn quá dài cho Google Translate Web. "
                "Dùng Google Cloud hoặc chia đoạn nhỏ hơn."
            )
        remaining = remaining[cut:]
    chunks.append((remaining, ""))
    return chunks


class _GoogleTranslateBase:
    """Standalone, structurally compatible with V0.4.1.x provider protocol."""

    _kind = "google"
    _expected_host = ""

    def __init__(
        self,
        profile_name: str,
        profile: Any,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = str(_field(profile, "model", "") or "").strip()
        if not self._model:
            models = _field(profile, "models", ()) or ()
            if isinstance(models, str):
                models = [models]
            self._model = str(models[0]) if models else ""
        self._base_url = _validate_google_base_url(
            str(_field(profile, "base_url", "")), self._expected_host
        )
        self._provider_id = (
            f"{self._kind}:{profile_name}:"
            f"{hashlib.sha256(self._base_url.encode()).hexdigest()[:12]}"
        )
        timeout_s = float(_field(profile, "timeout_s", 45.0))
        connect_timeout_s = float(_field(profile, "connect_timeout_s", 10.0))
        if timeout_s <= 0 or connect_timeout_s <= 0:
            raise ValueError("Google provider timeout phải lớn hơn 0.")
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_s, connect=connect_timeout_s),
            verify=bool(_field(profile, "verify_ssl", True)),
            follow_redirects=False,
            transport=transport,
            limits=httpx.Limits(max_keepalive_connections=6, max_connections=10),
        )

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def model_id(self) -> str:
        return self._model

    def streaming_override_for(self, performance_mode: str) -> bool:
        del performance_mode
        return False

    def translate_stream(
        self,
        request: Any,
        instructions: str,
        on_delta: Callable[[str], None],
    ) -> str:
        """Compatibility only: one complete delta, NEVER SSE/streaming."""
        text = self.translate(request, instructions)
        if text:
            on_delta(text)
        return text

    def cache_scope(self, request: Any, instructions: str) -> tuple[str, str]:
        """Style/speed/prompt don't affect plain Google machine translation."""
        del request, instructions
        return "google-plain-translation", "google-translate-v1"

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, url, **kwargs)
        except httpx.TimeoutException:
            # Web GET request failures may contain the source text as a URL.
            raise GoogleTranslateError(f"{self._kind}: hết thời gian chờ kết nối/phản hồi.") from None
        except httpx.RequestError:
            raise GoogleTranslateError(f"{self._kind}: không kết nối được đến Google.") from None
        if response.status_code == 429:
            raise GoogleTranslateError(f"{self._kind}: HTTP 429, bị giới hạn tốc độ. Thử lại sau.")
        if response.status_code in (401, 403):
            raise GoogleTranslateError(
                f"{self._kind}: HTTP {response.status_code}. "
                "Kiểm tra API key/quyền truy cập hoặc giới hạn dịch vụ."
            )
        if response.is_error:
            # Do NOT include request URL or raw response body.
            raise GoogleTranslateError(f"{self._kind}: Google trả lỗi HTTP {response.status_code}.")
        return response


class GoogleTranslateWebProvider(_GoogleTranslateBase):
    """Unofficial keyless Google Translate Web (best-effort only)."""

    _kind = "Google Translate Web (không chính thức)"
    _expected_host = "translate.googleapis.com"

    def __init__(self, profile_name: str, profile: Any, *, transport=None) -> None:
        model = str(_field(profile, "model", "") or "").strip()
        if model and model != GOOGLE_WEB_MODEL:
            raise ValueError(f"Google Translate Web chỉ có model '{GOOGLE_WEB_MODEL}'.")
        # httpx may log full GET URLs, including selected text in query q.
        # Suppress httpx/httpcore logging to avoid leaking source via root INFO.
        # This intentionally reduces httpx diagnostics process-wide too.
        for name in ("httpx", "httpcore"):
            transport_logger = logging.getLogger(name)
            if transport_logger.getEffectiveLevel() < logging.WARNING:
                transport_logger.setLevel(logging.WARNING)
        super().__init__(profile_name, profile, transport=transport)
        self._model = GOOGLE_WEB_MODEL

    def translate(self, request: Any, instructions: str = "") -> str:
        del instructions  # Not an LLM; no prompt/style support.
        text = str(_field(request, "source_text", "") or "")
        if not text.strip():
            return ""
        source = _google_language(_field(request, "source_language", "auto"), source=True)
        target = _google_language(_field(request, "target_language", "vi"))
        output: list[str] = []
        chunks = _split_google_web_text(text)
        for source_chunk, joiner in chunks:
            if source_chunk.strip():
                response = self._request(
                    "GET",
                    self._base_url + "/translate_a/single",
                    params={
                        "client": "gtx",
                        "sl": source,
                        "tl": target,
                        "dt": "t",
                        "q": source_chunk,
                    },
                )
                try:
                    payload = response.json()
                except ValueError:
                    raise GoogleTranslateError(
                        "Google Translate Web trả HTML/không phải JSON; "
                        "có thể bị chặn hoặc endpoint đã thay đổi."
                    ) from None
                output.append(_extract_google_web_translation(payload))
            else:
                output.append(source_chunk)
            output.append(joiner)
        logger.info("Google Translate Web completed chunks=%d characters=%d", len(chunks), len(text))
        return "".join(output)


class GoogleCloudTranslationProvider(_GoogleTranslateBase):
    """Official Cloud Translation Basic v2, API key required, metered usage."""

    _kind = "Google Cloud Translation Basic"
    _expected_host = "translation.googleapis.com"

    def __init__(self, profile_name: str, profile: Any, *, transport=None) -> None:
        model = str(_field(profile, "model", "") or "").strip()
        if model and model.lower() != GOOGLE_CLOUD_MODEL:
            raise ValueError(f"Google Cloud Basic hiện hỗ trợ model '{GOOGLE_CLOUD_MODEL}'.")
        key = str(_field(profile, "api_key", "") or "").strip()
        if not key:
            env_name = str(_field(profile, "api_key_env", "") or "").strip()
            key = os.getenv(env_name, "").strip() if env_name else ""
        if not key or key.lower().startswith("replace_me"):
            raise ValueError(
                "Google Cloud Translation cần API key. "
                "Bật Cloud Translation API + billing rồi nhập key hoặc api_key_env."
            )
        self._api_key = key
        super().__init__(profile_name, profile, transport=transport)
        self._model = GOOGLE_CLOUD_MODEL

    def translate(self, request: Any, instructions: str = "") -> str:
        del instructions
        source_text = str(_field(request, "source_text", "") or "")
        if not source_text.strip():
            return ""
        source = _google_language(_field(request, "source_language", "auto"), source=True)
        target = _google_language(_field(request, "target_language", "vi"))
        payload: dict[str, Any] = {
            "q": source_text,
            "target": target,
            "format": "text",
            "model": GOOGLE_CLOUD_MODEL,
        }
        if source != "auto":
            payload["source"] = source
        response = self._request(
            "POST",
            self._base_url + "/language/translate/v2",
            json=payload,
            headers={"X-goog-api-key": self._api_key},
        )
        try:
            data = response.json()
            translations = data["data"]["translations"]
            translated = translations[0]["translatedText"]
            if not isinstance(translated, str):
                raise ValueError("translatedText is not a string")
        except (ValueError, TypeError, KeyError, IndexError):
            raise GoogleTranslateError(
                "Google Cloud Translation trả về dữ liệu không đúng định dạng."
            ) from None
        logger.info("Google Cloud Translation completed characters=%d", len(source_text))
        return html.unescape(translated)


def create_google_provider(
    profile_name: str,
    profile: Any,
    *,
    provider_type: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> GoogleTranslateWebProvider | GoogleCloudTranslationProvider:
    """Optional convenience entrypoint for existing provider factories."""
    detected = infer_google_provider_type(str(_field(profile, "base_url", "") or ""))
    configured = str(provider_type or _field(profile, "type", "") or "").strip().lower()
    # The original ProviderProfile.type defaults to openai_compatible, even
    # when catalog URLs identify Google. Infer unless explicitly overridden.
    if provider_type is None and detected and configured in (
        "", "auto", "openai_compatible", "openai-compatible", "compatible"
    ):
        kind = detected
    else:
        kind = configured or detected or ""
    if kind == "google_translate_web":
        return GoogleTranslateWebProvider(profile_name, profile, transport=transport)
    if kind == "google_cloud_translate":
        return GoogleCloudTranslationProvider(profile_name, profile, transport=transport)
    raise ValueError(
        "Not a Google translation provider. "
        "Preserve existing provider factory routing for OpenAI-compatible providers."
    )
