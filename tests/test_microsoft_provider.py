from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from app.config import (AppConfig, ProviderSection, portable_provider_entry,
                        provider_profile_from_dict)
from app.models import TranslationRequest, RequestMode
from app.providers.factory import create_translation_provider
from app.providers.microsoft_provider import MICROSOFT_PRESET, MicrosoftTranslationProvider
from microsoft_translator import UsageEvent
from microsoft_translator_usage import LocalUsageLedger


class Response(BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(json.dumps(body).encode())
        self.headers = headers or {}


class MicrosoftProviderTests(unittest.TestCase):
    def test_microsoft_removes_env_and_timeout_settings(self):
        from dataclasses import replace
        from app.config import provider_profile_to_dict, profile_override_entry
        from microsoft_translator import DEFAULT_TIMEOUT_SECONDS
        raw=dict(MICROSOFT_PRESET,api_key='synthetic-key',api_key_env='OLD_ENV',timeout_s=120)
        profile=provider_profile_from_dict(raw)
        self.assertEqual(profile.api_key_env,'')
        for values in (provider_profile_to_dict(profile),profile_override_entry(raw)):
            self.assertNotIn('api_key_env',values)
            self.assertNotIn('timeout_s',values)
        provider=MicrosoftTranslationProvider('MS', replace(profile,timeout_s=120))
        self.assertEqual(provider._translator.timeout,DEFAULT_TIMEOUT_SECONDS)
        with patch.dict('os.environ',{'OLD_ENV':'synthetic-env-key'}):
            with self.assertRaisesRegex(ValueError,'key'):
                MicrosoftTranslationProvider('MS',replace(profile,api_key='',api_key_env='OLD_ENV'))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'usage.sqlite3'
        self.usage = LocalUsageLedger(self.path)
        self.profile = provider_profile_from_dict(dict(MICROSOFT_PRESET, api_key='synthetic-key', region='eastasia'))
        self.provider = MicrosoftTranslationProvider('MS', self.profile, usage=self.usage)
        self.request = TranslationRequest('job', 'Hello', 'auto', 'zh-TW', 'chat', 'fast', RequestMode.POPUP, None)

    def test_request_headers_languages_and_header_usage(self):
        response = Response([{'translations': [{'to': 'zh-Hant', 'text': '你好'}]}], {'X-Metered-Usage': '5'})
        with patch('microsoft_translator.urlopen', return_value=response) as send:
            self.assertEqual(self.provider.translate(self.request, 'ignored prompt'), '你好')
        req = send.call_args.args[0]
        self.assertIn('to=zh-Hant', req.full_url)
        self.assertNotIn('from=', req.full_url)
        self.assertEqual(req.get_header('Ocp-apim-subscription-key'), 'synthetic-key')
        self.assertEqual(req.get_header('Ocp-apim-subscription-region'), 'eastasia')
        self.assertEqual(json.loads(req.data), [{'Text': 'Hello'}])
        self.assertNotIn('synthetic-key', req.full_url)
        month = self.usage.month_usage()
        self.assertEqual((month.calls, month.verified_characters, month.estimated_characters), (1, 5, 0))
        self.assertFalse(self.provider.streaming_override_for('quality'))

    def test_estimate_persists_and_bad_responses_never_record(self):
        response = Response([{'translations': [{'to': 'zh-Hant', 'text': '你好'}]}])
        with patch('microsoft_translator.urlopen', return_value=response):
            self.provider.translate(self.request, '')
        self.assertEqual(LocalUsageLedger(self.path).month_usage().estimated_characters, 5)
        for response in (Response({}), Response([{'translations': []}])):
            with patch('microsoft_translator.urlopen', return_value=response):
                with self.assertRaises(RuntimeError):
                    self.provider.translate(self.request, '')
        for status in (401, 403, 429, 500):
            error = HTTPError('https://official.test', status, 'secret body', {}, BytesIO(b'private text'))
            with patch('microsoft_translator.urlopen', side_effect=error):
                with self.assertRaisesRegex(RuntimeError, str(status)) as caught:
                    self.provider.translate(self.request, '')
                self.assertNotIn('private', str(caught.exception))
                self.assertNotIn('synthetic-key', str(caught.exception))
        self.assertEqual(self.usage.month_usage().calls, 1)

    def test_factory_and_portable_roundtrip_keep_region(self):
        portable = portable_provider_entry(self.profile)
        self.assertEqual(portable['region'], 'eastasia')
        restored = provider_profile_from_dict(portable)
        self.assertEqual(restored.type, 'microsoft_translator')
        self.assertEqual(restored.region, 'eastasia')
        config = AppConfig(providers=ProviderSection(active_profile='Renamed', profiles={'Renamed': restored}))
        from dataclasses import replace
        config = replace(config, app=replace(config.app, data_dir=self.tmp.name))
        provider = create_translation_provider(config)
        self.assertIsInstance(provider, MicrosoftTranslationProvider)
        self.assertFalse(provider.streaming_override_for('fast'))
        with self.assertRaisesRegex(ValueError, 'key'):
            create_translation_provider(replace(config, providers=ProviderSection(active_profile='MS', profiles={
                'MS': provider_profile_from_dict(MICROSOFT_PRESET)})))

    def test_ledger_deduplicates_and_uses_vietnam_month(self):
        from datetime import datetime, timezone
        event = UsageEvent('request-1', 'en', ('vi',), 5, 'header')
        with patch('microsoft_translator_usage.datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 31, 18, 0, tzinfo=timezone.utc)
            self.usage.record(event)
            self.usage.record(event)
        self.assertEqual(self.usage.month_usage('2026-11').verified_characters, 5)
        self.assertEqual(self.usage.month_usage('2026-10').calls, 0)
        self.assertEqual(self.usage.month_usage('2026-12').estimated_local_remaining, 2_000_000)

    def test_ledger_error_keeps_successful_translation(self):
        response = Response([{'translations': [{'to': 'zh-Hant', 'text': '你好'}]}])
        with patch.object(self.usage, 'record', side_effect=OSError('disk full')), \
             patch('microsoft_translator.urlopen', return_value=response), self.assertLogs('microsoft_translator', level='WARNING'):
            # Callback is bound during construction.
            provider = MicrosoftTranslationProvider('MS', self.profile, usage=self.usage)
            self.assertEqual(provider.translate(self.request, ''), '你好')

    def test_worker_cache_skips_network_usage_and_streaming(self):
        from dataclasses import replace
        from app.services.cache import TranslationCache
        from app.workers.translation_worker import TranslationWorker
        from app.config import TranslationSection
        results = []
        worker = TranslationWorker(self.provider, TranslationCache(Path(self.tmp.name) / 'cache.db'),
                                   TranslationSection(streaming={'fast': True}), results.append)
        response = Response([{'translations': [{'to': 'zh-Hant', 'text': '你好'}]}])
        with patch('microsoft_translator.urlopen', return_value=response) as send:
            worker._translate(self.request)
            worker._translate(replace(self.request, job_id='cached'))
        self.assertEqual(send.call_count, 1)
        self.assertIsNone(results[0].error)
        self.assertTrue(results[1].cached)
        self.assertEqual(self.usage.month_usage().calls, 1)

    def test_catalog_and_config_reload_region_and_invalid_endpoint(self):
        import os
        from app.services.provider_catalog import ProviderCatalogStore
        root = Path(self.tmp.name)
        ProviderCatalogStore(root / 'providers.json').replace_all({'Custom MS': portable_provider_entry(self.profile)})
        (root / 'config.json').write_text(json.dumps({'providers': {'active_profile': 'Custom MS'}}))
        with patch.dict(os.environ, {'APP_CONFIG_PATH': str(root / 'config.json'),
                                    'PROVIDER_CATALOG_PATH': str(root / 'providers.json'),
                                    'PROMPT_CATALOG_PATH': str(root / 'prompts.json')}):
            loaded = AppConfig.load().providers.profiles['Custom MS']
        self.assertEqual((loaded.type, loaded.region), ('microsoft_translator', 'eastasia'))
        from dataclasses import replace
        for url in ('http://api.cognitive.microsofttranslator.com', 'https://evil.test',
                    'https://api.cognitive.microsofttranslator.com.evil.test'):
            with self.assertRaises(ValueError):
                MicrosoftTranslationProvider('MS', replace(self.profile, base_url=url))
        with self.assertRaises(ValueError):
            provider_profile_from_dict(dict(MICROSOFT_PRESET, region='eastasia\r\nprivate-header'))

    def test_size_guard_empty_input_and_concurrent_ledger(self):
        from dataclasses import replace
        with patch('microsoft_translator.urlopen') as send:
            self.assertEqual(self.provider.translate(replace(self.request, source_text='  '), ''), '  ')
            with self.assertRaises(ValueError):
                self.provider.translate(replace(self.request, source_text='A' * 50_001), '')
            send.assert_not_called()
        from concurrent.futures import ThreadPoolExecutor
        def record(i):
            LocalUsageLedger(self.path).record(UsageEvent(str(i), 'en', ('vi',), 5, 'estimate'))
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(record, range(20)))
        self.assertEqual(self.usage.month_usage().estimated_characters, 100)

    def test_usage_initialization_failure_keeps_provider_available(self):
        from dataclasses import replace
        import sqlite3
        config = replace(AppConfig(), app=replace(AppConfig().app, data_dir=self.tmp.name),
                         providers=ProviderSection(active_profile='MS', profiles={'MS': self.profile}))
        with patch('microsoft_translator_usage.LocalUsageLedger', side_effect=sqlite3.OperationalError('locked')), \
                self.assertLogs('app.providers.factory', level='WARNING'):
            self.assertIsInstance(create_translation_provider(config), MicrosoftTranslationProvider)
