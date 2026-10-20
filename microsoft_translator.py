"""Microsoft Translator (Text REST API v3.0) for ScreenTranslator.

- Vietnamese, English, Traditional/Simplified Chinese and all supported pairs.
- Automatic detection, source/target switching, multiple targets in one call.
- Azure's per-request X-Metered-Usage header (when returned).
- Optional usage-event callback for SQLite persistence.
- Supported language list without an API key.

Standard library only. Never bundle private API keys with the Windows app.
All I/O is synchronous; call from a PySide6 worker (not the UI thread).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from getpass import getpass
from typing import Callable, Dict, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
DEFAULT_REGION = "southeastasia"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_BILLABLE_CHARS_PER_REQUEST = 5000  # App guardrail, not the official API maximum.

_LANGUAGE_ALIASES = {
    "zh-tw": "zh-Hant", "zh-hk": "zh-Hant", "zh-hant": "zh-Hant",
    "zh-cn": "zh-Hans", "zh-sg": "zh-Hans", "zh-hans": "zh-Hans",
    "zh": "zh-Hans",  # Don't use generic 'zh' if you know the script.
    "vi-vn": "vi", "en-us": "en", "en-gb": "en",
    "ja-jp": "ja", "ko-kr": "ko", "fr-fr": "fr", "de-de": "de",
}
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationResult:
    text: str
    detected_source_language: Optional[str] = None
    metered_characters: Optional[int] = None
    usage_source: str = "none"  # header | estimate | none


@dataclass(frozen=True)
class MultiTranslationResult:
    translations: Dict[str, str]
    detected_source_language: Optional[str] = None
    metered_characters: Optional[int] = None
    usage_source: str = "none"  # header | estimate | none


@dataclass(frozen=True)
class UsageEvent:
    """Metadata only: never stores text, translation or API keys."""
    request_id: str
    source_language: str
    target_languages: Tuple[str, ...]
    metered_characters: int
    usage_source: str  # header or estimate


class MicrosoftTranslatorError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None,
                 service_error_code: Optional[str] = None,
                 retry_after: Optional[str] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.service_error_code = service_error_code
        self.retry_after = retry_after


def normalize_language(language: Optional[str], *, source: bool = False) -> Optional[str]:
    """Map common app-style language IDs to Translator v3 language codes."""
    if language is None or not str(language).strip():
        if source:
            return None
        raise ValueError("Cần chọn ngôn ngữ đích.")
    code = str(language).strip()
    if code.lower() in ("auto", "automatic", "detect"):
        if source:
            return None
        raise ValueError("Ngôn ngữ đích không thể là 'auto'.")
    result = _LANGUAGE_ALIASES.get(code.lower(), code)
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})*", result):
        raise ValueError("Mã ngôn ngữ không hợp lệ: {!r}".format(code))
    return result


def approximate_billed_characters(text: str, target_count: int = 1) -> int:
    """Estimate based on Azure codepoint/surrogate counting rules.

    This is not an official quota reading. Prefer X-Metered-Usage if available.
    """
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text) * target_count


def _response_header(response: object, name: str) -> Optional[str]:
    headers = getattr(response, "headers", None)
    if headers is not None and hasattr(headers, "get"):
        value = headers.get(name)
        if value is not None:
            return str(value)
    getheader = getattr(response, "getheader", None)
    if callable(getheader):
        value = getheader(name)
        if value is not None:
            return str(value)
    return None


def get_supported_languages(*, display_language: str = "vi", timeout: float = 15.0) -> Dict[str, dict]:
    """Fetch translation languages. Public endpoint: API key NOT required.

    Cache this in the GUI (e.g. one day). Each value has name/nativeName/dir.
    """
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})*", display_language):
        raise ValueError("Mã ngôn ngữ giao diện không hợp lệ.")
    if timeout <= 0:
        raise ValueError("timeout phải lớn hơn 0.")
    request = Request(
        DEFAULT_ENDPOINT + "/languages?api-version=3.0&scope=translation",
        headers={"Accept-Language": display_language, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8-sig"))
        languages = data["translation"]
        if not isinstance(languages, dict):
            raise TypeError("translation should be an object")
        return languages
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise MicrosoftTranslatorError("Không tải được danh sách ngôn ngữ Microsoft Translator.") from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise MicrosoftTranslatorError("Danh sách ngôn ngữ trả về không đúng định dạng.") from exc


class MicrosoftTranslator:
    """Simple standalone translator adapter for a Windows Qt worker.

    Backwards-compatible methods:
        translate(text, source='auto', target='vi') -> str
        translate_with_info(...) -> TranslationResult
        await translate_async(...) -> str

    New methods:
        translate_many(text, source='auto', targets=('vi', 'en')) -> dict
        translate_many_with_info(...) -> MultiTranslationResult

    on_usage: optional callback(UsageEvent), invoked once after a successful
    network translation. A failing callback won't discard the translation.
    """

    def __init__(self, api_key: str, region: str = DEFAULT_REGION, *,
                 timeout: float = DEFAULT_TIMEOUT_SECONDS,
                 max_chars: int = DEFAULT_MAX_BILLABLE_CHARS_PER_REQUEST,
                 on_usage: Optional[Callable[[UsageEvent], None]] = None) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Chưa nhập Microsoft Translator API key.")
        if not isinstance(region, str):
            raise ValueError("region phải là chuỗi ký tự.")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout phải lớn hơn 0.")
        if not isinstance(max_chars, int) or max_chars <= 0:
            raise ValueError("max_chars phải là số nguyên dương.")
        if on_usage is not None and not callable(on_usage):
            raise ValueError("on_usage phải là callback hoặc None.")
        self._api_key = api_key.strip()
        self.region = region.strip()
        self.timeout = float(timeout)
        self.max_chars = max_chars
        self.on_usage = on_usage

    def translate(self, text: str, source: Optional[str] = "auto", target: str = "vi") -> str:
        return self.translate_with_info(text, source=source, target=target).text

    def translate_with_info(self, text: str, source: Optional[str] = "auto",
                            target: str = "vi") -> TranslationResult:
        target_code = normalize_language(target)
        result = self.translate_many_with_info(text, source=source, targets=[target_code])
        return TranslationResult(
            text=result.translations[target_code],
            detected_source_language=result.detected_source_language,
            metered_characters=result.metered_characters,
            usage_source=result.usage_source,
        )

    def translate_many(self, text: str, source: Optional[str] = "auto",
                       targets: Sequence[str] = ("vi", "en")) -> Dict[str, str]:
        return self.translate_many_with_info(text, source=source, targets=targets).translations

    def translate_many_with_info(self, text: str, source: Optional[str] = "auto",
                                 targets: Sequence[str] = ("vi", "en")) -> MultiTranslationResult:
        if not isinstance(text, str):
            raise TypeError("text phải là chuỗi ký tự.")
        if isinstance(targets, str) or not isinstance(targets, (tuple, list)) or not targets:
            raise ValueError("targets phải là danh sách ngôn ngữ đích không rỗng.")
        target_codes = [normalize_language(t) for t in targets]
        lower_codes = [c.lower() for c in target_codes]
        if len(set(lower_codes)) != len(lower_codes):
            raise ValueError("Không được lặp ngôn ngữ đích trong cùng request.")
        source_code = normalize_language(source, source=True)
        if not text.strip():
            return MultiTranslationResult(translations={code: text for code in target_codes})

        estimated_chars = approximate_billed_characters(text, len(target_codes))
        if estimated_chars > self.max_chars:
            raise ValueError(
                "Ước tính {} ký tự tính phí vượt giới hạn nội bộ {} ký tự/request. "
                "Hãy chia văn bản hoặc giảm số ngôn ngữ đích.".format(
                    estimated_chars, self.max_chars
                )
            )

        params = [("api-version", "3.0")]
        if source_code is not None:
            params.append(("from", source_code))
        params.extend(("to", t) for t in target_codes)
        url = DEFAULT_ENDPOINT + "/translate?" + urlencode(params)
        request_id = str(uuid.uuid4())
        payload = json.dumps([{"Text": text}], ensure_ascii=False).encode("utf-8")
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "X-ClientTraceId": request_id,
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        request = Request(url, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_data = response.read()
                usage_header = _response_header(response, "X-Metered-Usage")
        except HTTPError as exc:
            raise self._convert_http_error(exc) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise MicrosoftTranslatorError(
                "Không kết nối được Microsoft Translator. Kiểm tra Internet và thử lại sau."
            ) from exc

        try:
            payload_json = json.loads(raw_data.decode("utf-8-sig"))
            item = payload_json[0]
            all_translations = item["translations"]
            found = {}
            for entry in all_translations:
                language_code = entry["to"]
                translated_text = entry["text"]
                if not isinstance(translated_text, str):
                    raise TypeError("translation text isn't a string")
                found[language_code.lower()] = translated_text
            translations = {t: found[t.lower()] for t in target_codes}
            detected = item.get("detectedLanguage") or {}
            detected_source = detected.get("language") if isinstance(detected, dict) else None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            raise MicrosoftTranslatorError(
                "Microsoft Translator trả về dữ liệu không đúng định dạng."
            ) from exc

        metered: Optional[int] = None
        if usage_header is not None:
            try:
                parsed_meter = int(usage_header.strip())
                if parsed_meter >= 0:
                    metered = parsed_meter
            except (ValueError, AttributeError):
                pass
        usage_source = "header" if metered is not None else "estimate"
        if metered is None:
            metered = estimated_chars

        if self.on_usage is not None:
            event = UsageEvent(
                request_id=request_id,
                source_language=source_code or (detected_source or "auto"),
                target_languages=tuple(target_codes),
                metered_characters=metered,
                usage_source=usage_source,
            )
            try:
                self.on_usage(event)
            except Exception:  # Logging failure must not turn a good translation into an error.
                _LOG.warning("Không lưu được thống kê sử dụng Microsoft Translator.", exc_info=True)

        return MultiTranslationResult(
            translations=translations,
            detected_source_language=detected_source,
            metered_characters=metered,
            usage_source=usage_source,
        )

    async def translate_async(self, text: str, source: Optional[str] = "auto",
                              target: str = "vi") -> str:
        return await asyncio.to_thread(self.translate, text, source, target)

    @staticmethod
    def _convert_http_error(error: HTTPError) -> MicrosoftTranslatorError:
        service_code = None
        try:
            body = json.loads(error.read(4096).decode("utf-8", errors="replace"))
            inner = body.get("error", {})
            if isinstance(inner, dict) and inner.get("code") is not None:
                service_code = str(inner["code"])
        except (TypeError, ValueError, OSError, AttributeError):
            pass
        status = error.code
        if status in (401, 403):
            message = "Azure từ chối truy cập (HTTP {}). Kiểm tra key, region và quota F0.".format(status)
        elif status == 429:
            message = "Microsoft Translator đang giới hạn tốc độ/quota (HTTP 429)."
        elif status == 400:
            message = "Request không hợp lệ (HTTP 400): kiểm tra ngôn ngữ và kích thước văn bản."
        elif status >= 500:
            message = "Máy chủ Microsoft Translator đang lỗi (HTTP {}).".format(status)
        else:
            message = "Microsoft Translator trả về HTTP {}.".format(status)
        retry_after = error.headers.get("Retry-After") if error.headers else None
        return MicrosoftTranslatorError(message, status_code=status,
                                        service_error_code=service_code,
                                        retry_after=retry_after)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Microsoft Translator nhiều ngôn ngữ + usage.")
    parser.add_argument("--list-languages", action="store_true", help="In ngôn ngữ được hỗ trợ (không cần key).")
    parser.add_argument("--text", default="設備啟動前，請先確認安全門已關閉。")
    parser.add_argument("--source", default="auto", help="auto, en, vi, zh-TW, zh-CN, ...")
    parser.add_argument("--target", default="vi", help="vi, en, zh-TW, ...")
    parser.add_argument("--targets", help="Tùy chọn: vi,en,zh-TW (dịch 1 lần sang nhiều ngôn ngữ).")
    parser.add_argument("--region", default=os.environ.get("AZURE_TRANSLATOR_REGION", DEFAULT_REGION))
    options = parser.parse_args()
    if options.list_languages:
        try:
            for code, info in sorted(get_supported_languages().items()):
                print("{}: {}".format(code, info.get("name", "")))
            return 0
        except MicrosoftTranslatorError as exc:
            print("Lỗi:", exc)
            return 1
    key = os.environ.get("AZURE_TRANSLATOR_KEY") or getpass("Nhập Translator Key 1 hoặc Key 2: ")
    try:
        client = MicrosoftTranslator(api_key=key, region=options.region)
        if options.targets:
            result = client.translate_many_with_info(
                options.text, source=options.source,
                targets=[t.strip() for t in options.targets.split(",")],
            )
            for language, translated in result.translations.items():
                print("{}: {}".format(language, translated))
        else:
            result = client.translate_with_info(
                options.text, source=options.source, target=options.target
            )
            print("Bản dịch:", result.text)
        if result.detected_source_language:
            print("Ngôn ngữ phát hiện:", result.detected_source_language)
        if result.metered_characters is not None:
            print("Ký tự cho request này: {} ({})".format(
                result.metered_characters,
                "Azure X-Metered-Usage" if result.usage_source == "header" else "ước tính nội bộ",
            ))
        return 0
    except (MicrosoftTranslatorError, TypeError, ValueError) as exc:
        print("Lỗi:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
