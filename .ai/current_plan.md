# Explain Adaptive v1.1 Implementation Plan

## Build 0.6.0 completed — 2026-10-30

Task ID: build-0.6.0-20261030. User accepted the feature/guide changes and explicitly chose version0.6.0. Updated app/version.py, installer default and Windows release filenames. Used the established unsigned build.ps1 pipeline in a clean disposable staging copy with example/default configs, existing PyInstaller6.22.3/Inno compiler, Pygments excluded and unrelated child DLL PATH entries filtered.

Build verification exposed a real Markdown image fallback: returning None from loadResource allows Qt's image handler to read valid local image URLs. The earlier test's unencoded spaces prevented Markdown image parsing. Corrected the test to use encoded URL (RED), return a transparent non-null1x1 placeholder (GREEN); 22 Explain tests pass, including2 native Windows150% cases. Clean staging full suite253/253 exit0; frozen self-check10/10 exit0. Verified59 product modules plus main/assets/defaults against current source. EXE survived150s before execution,30s after and60s after delivery; SHA256 stable, AV report metadata unchanged. No AV settings changed.

Delivered portable: dist/ScreenTranslator-0.6.0/ScreenTranslator.exe (keep _internal),7960603 bytes, SHA25664f10380daa3dc4e3e3fa4981f5f903045d2c5461ad0b536048ea9c3e2b4e43c. Setup: release/AI-Screen-Translator-0.6.0-Setup.exe,111994758 bytes, SHA256e0045c4f22e781e83deb9dc8d914c1e3c290f5ae37ddea8dec908db0831dd0b1. Evidence artifacts/build-0.6.0-20261030/result.json; latest-build-evidence updated. Prior0.5.1 binaries retained. No install/update/live API/new security scan/repo sync/push/publish.

## Completed follow-up: provider/model usage guide (2026-10-30)

User requested the missing provider/model instructions. Added a dedicated page5 before tray/help (now page6): + Thêm provider, Type/Base URL/API key/Endpoint, + Thêm model with exact Model ID, Model đang dùng, Test, Provider đang áp dụng, Lưu & áp dụng. Notes cover preset buttons, fixed Trial model list and machine translation limitations. One local model demo changes only its label. Navigation/counters use actual page count; updated six-page offline self-check, guide tests and README. RED before implementation; 13 guide tests and all253 suite tests pass exit0, compileall/native100%/150% six-page navigation/render including600x500 scrolling pass. Evidence artifacts/provider-guide-*. No provider logic, live API, real config changes, build/version/release.

## Completed follow-up: Explain Markdown display (2026-10-30)

Fixed raw **bold** markers caused by QPlainTextEdit rendering the spec's Markdown as literal text. Existing WaveTranslationOutput now uses QTextEdit with Qt Markdown for Explain streams/final output; Translate still uses plain text. Explain Copy uses rendered plain text. Loading animation, geometry, reader scroll, stale callbacks and Replace guards preserved. HTML parsing disabled and custom QTextDocument rejects image/file resources. No provider/prompt/dependency changes. New regression tests RED before implementation; final252/252 full suite exit0 (22 Explain), compileall and native100%/150% renders pass. Evidence artifacts/explain-markdown-*. No live calls/build/version/release.

## Completed follow-up: compact icon and guide (2026-10-30)

User confirmed Explain works and requested an icon-only toolbar button plus usage-guide coverage. The real and demo Explain buttons now show only 💡, with Explain tooltip/accessibility names. Existing guide page 1 demonstrates a fixed offline explanation and explains AI configuration/default Vietnamese/no Replace; all five pages and language demos remain. Only toolbar/guide UI, relevant tests and README changed. Tests were RED before edits; final248/248 full suite exit0; compileall and native100%/150% render (including600x500 guide) pass. Evidence artifacts/explain-icon-guide-tests.log and artifacts/explain-icon-guide/. No model calls or build/version/release.

Task ID: explain-adaptive-v1-20261030

Goal: implement ScreenTranslator_Explain_Adaptive_Minimal_Spec_v1.1.md against the existing 0.5.1 source, without rebuilding its Quick UX pipeline.

Architecture: RequestMode.EXPLAIN travels through the existing controller, worker and popup. The worker renders the fixed explain-v1 system prompt and bypasses translation cache. The OpenAI-compatible adapter (including Trial) sends selected text as JSON data in the user role; legacy completion and machine translation providers report an AI configuration error. Existing translation behavior stays intact.

Tech stack: existing Python/PySide6/httpx/unittest; no new dependencies. This workspace has no Git metadata; no branch/commit/build/release is part of this task.

## Scope and interfaces

- app/models.py: add RequestMode.EXPLAIN, no hotkey changes.
- app/prompts.py: fixed EXPLAIN_PROMPT_VERSION='explain-v1', build_explain_instructions(output_language) with the exact section 3 prompt; only vi/en/zh-Hant.
- app/providers/base.py and openai_compatible_provider.py: supports_explain default false, adapter true; JSON user data, system role separation, no legacy completions, no retry after a successful but malformed Explain response.
- app/workers/translation_worker.py: choose Explain prompt, reject unsupported providers, skip translation cache get/put, reuse streaming and result callbacks.
- app/config.py and app/ui/main_window.py: explain_output_language='vi' in existing Quick UX settings and validation/save/reset flow.
- app/ui/quick_toolbar.py and app/controller.py: independent Explain signal/action, shared snapshot checks and submission, no replacement snapshot for Explain.
- app/ui/quick_popup.py: optional mode argument to start; Explain labels and Copy/Pin/Close only; disable Replace and retain late-result checks.
- tests/test_explain.py and existing toolbar expectation: behavioral coverage at these boundaries.

## Execution

- [x] Capture baseline: 229 tests pass; original changed source preserved under artifacts/explain-original.
- [x] Write failing tests for system/user separation, exact prompt, capabilities, settings, single inference, cache bypass, toolbar/controller/popup safety.
- [x] Run new tests and confirm missing-feature failures (artifacts/explain-red-tests.log).
- [x] Implement the minimum changes above.
- [x] Verify: 18 Explain tests and all 247 suite tests pass with exit 0; compileall passes; native Qt smoke/render at 100% and 150% passes.
- [x] Independent read-only review found no actionable defects; README and handoff updated.
- [x] Updated ScreenTranslator Current-State in Shared Brain and verified by reading it back.

## Review focus

- Selection data containing prompt injection remains JSON user data; simple text, PLC/code, logs and long text all use one adaptive prompt.
- Machine translation, missing AI config and legacy completions never simulate Explain.
- Closing/replacing a popup rejects stale tokens/results; forged Replace callbacks cannot paste Explain output.
- Explain cannot read/write translation cache even when a matching translation exists.
- Translation languages/settings/hotkeys and existing clipboard/UIA timing remain unchanged.

Offline tests verify integration and prompts; actual model response quality requires live-provider acceptance and is reported separately.

## Verification notes

artifacts/explain-targeted-tests.log: 18/18 pass. artifacts/explain-regression-tests.log: 247/247 pass (includes existing intentional synthetic mouse-callback error). Native screenshots: artifacts/explain-native/{1,1.5}/. No live-provider calls, version bump, EXE/Setup build, install, repo sync or publishing.

Test-only shutdown issue reproduced independently: Qt offscreen exits with access violation after setMimeData(QMimeData()) on an empty clipboard. Preserve empty clipboard with clear() in the Copy test instead; targeted run exits 0. Production clipboard implementation unchanged.
