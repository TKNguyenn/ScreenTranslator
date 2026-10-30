# Explain Adaptive v1.1 — source integration

## Delivered build0.6.0 — 2026-10-30

Task ID: build-0.6.0-20261030. User selected0.6.0 after accepting Explain, compact toolbar, Markdown output and six-page guide with provider/model instructions. Original unsigned packaging pipeline completed in clean staging; defaults/examples only, Pygments omitted and child PATH filtered. Version/source/installer aligned. Build-gate correction: valid encoded Markdown image URLs revealed Qt fallback despite loadResource=None; test now uses encoded URL and document returns a transparent1x1 placeholder. RED→GREEN,22 Explain cases and2 native150% cases pass; full253 tests pass; frozen self-check10/10;59 modules+main/assets/defaults match source. EXE and Setup hashes unchanged after observation/self-check/copy; AV log metadata unchanged, no AV changes.

Portable dist/ScreenTranslator-0.6.0/ScreenTranslator.exe (retain _internal):7960603 bytes SHA25664f10380daa3dc4e3e3fa4981f5f903045d2c5461ad0b536048ea9c3e2b4e43c. Setup release/AI-Screen-Translator-0.6.0-Setup.exe:111994758 bytes SHA256e0045c4f22e781e83deb9dc8d914c1e3c290f5ae37ddea8dec908db0831dd0b1. Evidence artifacts/build-0.6.0-20261030/result.json. Previous0.5.1 files retained; no install/update/live API/security rescan/push/publish. Older source-only entries below are historical.

Follow-up2026-10-30 provider guide: UsageGuideDialog now has6 pages; added page5 for provider/model setup before final tray/help page6. Actual UI names/instructions verified in MainWindow. Includes provider connection fields, exact Model ID/add/select, Test cost note, active-provider selection and Save & Apply, presets/Trial/Explain differences, and a local model demo. Page counters/navigation and offline self-check updated; app/provider behavior unchanged. 13 guide and253 full suite tests pass exit0, compileall/native100%/150% renders and compact navigation pass. Evidence artifacts/provider-guide-*. No real provider call/config edit/new binaries/version/release.

Follow-up2026-10-30 Markdown: fixed literal **bold** markers in Explain. app/ui/quick_popup.py retains its existing output class but uses QTextEdit/Qt Markdown only for Explain; Translate remains literal/plain. Explain Copy strips formatting using rendered toPlainText. Streaming rerenders accumulated Markdown while preserving reader scroll; loading animation/stale guards/geometry retained. Markdown HTML disabled, _OutputDocument prevents local/remote resource loading. tests/test_explain.py covers bold/regular text, split stream delimiters, Copy, code, scroll, HTML/images and switching back to Translate. Final252/252 suite exit0 (22 Explain), compileall and native100%/150% screenshot checks pass; artifacts/explain-markdown-*. No provider/prompt/new dependencies/build/version/release.

Follow-up2026-10-30: user confirmed Explain working; toolbar now shows only 💡 with accessible name/tooltip. Existing five-page guide adds Explain to page1 with a local fixed-text demo, AI requirement/default Vietnamese and no-Replace explanation. Translation language demos still work and no API/settings/clipboard changes occur from the Explain demo. Full suite248/248 exit0, compileall and native100%/150% normal/compact render pass. See artifacts/explain-icon-guide-tests.log and artifacts/explain-icon-guide/. No new binaries/version/release.

Task ID: explain-adaptive-v1-20261030
Date: 2026-10-30
Status: implementation and offline verification complete; live-model acceptance not run.

Spec: ScreenTranslator_Explain_Adaptive_Minimal_Spec_v1.1.md. Plan: .ai/current_plan.md.

The current workspace is source 0.5.1 without Git metadata. Explain was integrated directly here; existing EXE/Setup files predate this feature.

Changes: independent RequestMode.EXPLAIN and button after VI/EN/繁; existing selection snapshot/controller/worker/streaming/popup reused. Exact section 3 prompt in app/prompts.py, version explain-v1, fixed vi/en/zh-Hant output language. Selected text is JSON user data, never part of the system prompt. No classifier or translation-cache access. Existing Quick UX settings now expose explain_output_language (default vi).

OpenAI-compatible providers and Trial support Explain through Chat Completions/Responses. Machine translation, missing configuration, Mock and explicit legacy Completions report AI configuration errors. Endpoint auto excludes legacy Completions for Explain; malformed successful Explain output does not retry another endpoint. Existing unsupported-endpoint/streaming rejection handling remains.

Popup Explain has only Copy/Pin/Close; Replace is hidden and disabled, and the controller never retains a replaceable source snapshot for Explain. Existing stale callback/close checks apply. Translate restores its normal buttons and retains its cache, prompts, Replace behavior and hotkeys. No selection, clipboard, OCR or PDF implementation changed.

Verification: baseline 229/229; new 18 Explain tests; final full suite 247/247 exit 0; compileall exit 0. Native Windows render assertions at 100%/150% pass and images inspected. Read-only independent review found no actionable defects. Logs and screenshots under artifacts/explain-*. Original modified files under artifacts/explain-original.

Test lifecycle fix: Qt offscreen crashes at shutdown for an empty QMimeData handed to clipboard; Copy test restores an empty clipboard with clear(). Separate reproducer confirmed root cause; no production clipboard edit.

Limits: mock HTTP validates request construction, inference count, streaming, provider errors, Trial usage, cache isolation and popup safety; it does not demonstrate actual AI answer quality/injection resistance. No live API, cross-application focus/paste acceptance, version bump, packaging/install or publish. Next: user checks a configured AI provider with 加急, normal prose, PLC/Python, KeyError, long text and embedded instructions; build only when requested.
