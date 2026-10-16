from __future__ import annotations

import hashlib
import logging
import queue
import threading
from collections.abc import Callable
from typing import Any, Mapping
from dataclasses import dataclass

from app.config import TranslationSection
from app.models import TranslationProgress, TranslationRequest, TranslationResult
from app.prompts import build_translation_instructions
from app.providers.base import TranslationProvider
from app.services.cache import TranslationCache


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSwitchTask:
    provider: TranslationProvider


@dataclass(frozen=True)
class RuntimeReloadTask:
    provider: TranslationProvider
    config: TranslationSection
    prompt_overrides: dict[str, dict[str, str]]


@dataclass(frozen=True)
class PromptReloadTask:
    prompt_overrides: dict[str, dict[str, str]]


class TranslationWorker:
    def __init__(
        self,
        provider: TranslationProvider,
        cache: TranslationCache,
        config: TranslationSection,
        on_result: Callable[[TranslationResult], None],
        on_progress: Callable[[TranslationProgress], None] | None = None,
        prompt_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._config = config
        self._on_result = on_result
        self._on_progress = on_progress
        self._prompt_overrides = self._clone_prompt_overrides(prompt_overrides)
        self._queue: queue.Queue[TranslationRequest | ProviderSwitchTask | RuntimeReloadTask | PromptReloadTask | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="TranslationWorker", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._close_provider(self._provider)

    def submit(self, request: TranslationRequest) -> None:
        self._queue.put(request)

    def replace_provider(self, provider: TranslationProvider) -> None:
        """
        Queue a provider swap so the old provider is never closed while a request
        is using it. All later queued translations use the new provider.
        """
        self._queue.put(ProviderSwitchTask(provider=provider))

    def reload_runtime(
        self,
        provider: TranslationProvider,
        config: TranslationSection,
        prompt_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        """Atomically replace provider + translation config + prompts after earlier queued work."""
        self._queue.put(
            RuntimeReloadTask(
                provider=provider,
                config=config,
                prompt_overrides=self._clone_prompt_overrides(prompt_overrides),
            )
        )

    def reload_prompts(self, prompt_overrides: Mapping[str, Any] | None) -> None:
        """Queue prompt updates without rebuilding the active provider."""
        self._queue.put(PromptReloadTask(self._clone_prompt_overrides(prompt_overrides)))

    def _run(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                return
            if isinstance(task, ProviderSwitchTask):
                self._switch_provider(task.provider)
                continue
            if isinstance(task, RuntimeReloadTask):
                self._reload_runtime(task.provider, task.config, task.prompt_overrides)
                continue
            if isinstance(task, PromptReloadTask):
                self._prompt_overrides = task.prompt_overrides
                logger.info("Prompt catalog reloaded with %s custom modes", len(task.prompt_overrides))
                continue
            self._translate(task)

    def _switch_provider(self, provider: TranslationProvider) -> None:
        old_provider = self._provider
        self._provider = provider
        logger.info(
            "Translation provider switched to provider_id=%s model=%s",
            provider.provider_id,
            provider.model_id,
        )
        self._close_provider(old_provider)

    def _reload_runtime(
        self,
        provider: TranslationProvider,
        config: TranslationSection,
        prompt_overrides: dict[str, dict[str, str]] | None = None,
    ) -> None:
        old_provider = self._provider
        self._provider = provider
        self._config = config
        self._prompt_overrides = self._clone_prompt_overrides(prompt_overrides)
        logger.info(
            "Translation runtime reloaded provider_id=%s model=%s",
            provider.provider_id,
            provider.model_id,
        )
        self._close_provider(old_provider)

    @staticmethod
    def _close_provider(provider: TranslationProvider) -> None:
        close = getattr(provider, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                logger.exception("Failed to close translation provider")

    @staticmethod
    def _clone_prompt_overrides(raw: Mapping[str, Any] | None) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        if not isinstance(raw, Mapping):
            return result
        for mode, styles in raw.items():
            if not isinstance(styles, Mapping):
                continue
            clean_styles = {
                str(style): str(template)
                for style, template in styles.items()
                if isinstance(template, str) and template.strip()
            }
            if clean_styles:
                result[str(mode)] = clean_styles
        return result

    def _prompt_cache_version(self, request: TranslationRequest, instructions: str) -> str:
        # V0.3.2 fingerprints the fully-rendered effective prompt. Custom prompt
        # edits therefore can never reuse a translation produced by an older prompt.
        digest = hashlib.sha256(instructions.encode("utf-8")).hexdigest()[:16]
        return f"{self._config.prompt_version}:{request.performance_mode}:{digest}"

    def _emit_delta(self, request: TranslationRequest, delta: str) -> None:
        if not delta or self._on_progress is None:
            return
        self._on_progress(TranslationProgress(request=request, delta_text=delta))

    def _translate(self, request: TranslationRequest) -> None:
        try:
            provider = self._provider
            instructions = build_translation_instructions(
                source_language=request.source_language,
                target_language=request.target_language,
                context_preset=request.context_preset,
                performance_mode=request.performance_mode,
                prompt_overrides=self._prompt_overrides,
            )
            cache_version = self._prompt_cache_version(request, instructions)
            cache_context = request.context_preset
            scope = getattr(provider, "cache_scope", None)
            if callable(scope):
                cache_context, cache_version = scope(request, instructions)
            key = self._cache.make_key(
                source_text=request.source_text,
                source_language=request.source_language,
                target_language=request.target_language,
                context_preset=cache_context,
                provider_id=provider.provider_id,
                model_id=provider.model_id,
                prompt_version=cache_version,
            )

            cached = self._cache.get(key)
            if cached is not None:
                self._on_result(
                    TranslationResult(request=request, translated_text=cached, cached=True)
                )
                return

            global_streaming = self._config.streaming_enabled_for(request.performance_mode)
            override = getattr(provider, "streaming_override_for", None)
            profile_override = override(request.performance_mode) if callable(override) else None
            streaming = global_streaming if profile_override is None else profile_override
            source = "global" if profile_override is None else "profile_override"
            logger.info(
                "Translation execution mode=%s streaming=%s streaming_source=%s",
                request.performance_mode,
                streaming,
                source,
            )

            if streaming:
                translated = provider.translate_stream(
                    request,
                    instructions,
                    lambda delta: self._emit_delta(request, delta),
                )
            else:
                translated = provider.translate(request, instructions)

            self._cache.put(
                key=key,
                source_text=request.source_text,
                translated_text=translated,
                source_language=request.source_language,
                target_language=request.target_language,
                context_preset=cache_context,
                provider_id=provider.provider_id,
                model_id=provider.model_id,
                prompt_version=cache_version,
            )
            self._on_result(
                TranslationResult(request=request, translated_text=translated, cached=False)
            )
        except Exception as exc:
            logger.exception("Translation failed")
            self._on_result(
                TranslationResult(
                    request=request,
                    translated_text="",
                    cached=False,
                    error=str(exc),
                )
            )
