"""Microsoft Text Translation adapter; credentials stay in the user's catalog."""
from urllib.parse import urlsplit

from app.providers.base import TranslationProvider
from microsoft_translator import DEFAULT_ENDPOINT, DEFAULT_REGION, MicrosoftTranslator, MicrosoftTranslatorError

MICROSOFT_TYPE = 'microsoft_translator'
MICROSOFT_PRESET = {
    'type': MICROSOFT_TYPE, 'base_url': DEFAULT_ENDPOINT, 'api_key': '',
    'model': 'microsoft-translator', 'models': ['microsoft-translator'],
    'region': DEFAULT_REGION,
}


def is_microsoft_url(url: str) -> bool:
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.netloc.lower() == 'api.cognitive.microsofttranslator.com'
            and parsed.path in ('', '/') and not parsed.query and not parsed.fragment)


class MicrosoftTranslationProvider(TranslationProvider):
    def __init__(self, profile_name, profile, *, usage=None):
        if not is_microsoft_url(profile.base_url):
            raise ValueError('Microsoft Translator cần endpoint HTTPS Text Translation chính thức.')
        key = profile.api_key.strip()
        self._profile_name = profile_name
        self._region = profile.region
        self._translator = MicrosoftTranslator(
            api_key=key, region=profile.region, max_chars=50_000,
            on_usage=usage.record if usage else None)

    @property
    def provider_id(self):
        return f'{MICROSOFT_TYPE}:{self._profile_name}:{self._region}'

    @property
    def model_id(self):
        return 'microsoft-translator'

    def translate(self, request, instructions):
        try:
            return self._translator.translate(request.source_text, request.source_language, request.target_language)
        except MicrosoftTranslatorError as exc:
            raise MicrosoftTranslatorError(str(exc), status_code=exc.status_code,
                                           service_error_code=exc.service_error_code,
                                           retry_after=exc.retry_after) from None

    def streaming_override_for(self, performance_mode):
        return False

    def close(self):
        pass  # urllib opens/closes each request; no persistent client.
