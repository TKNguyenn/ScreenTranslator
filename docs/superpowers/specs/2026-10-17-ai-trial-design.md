# ScreenTranslator AI Trial — Design

Status: implemented in source, including the user's revised streaming and estimated-budget requirements on 2026-10-17. Installer rebuild and publication remain pending.

## Defaults and fixed provider

- Fresh source/packaged defaults contain Google Translate Free and Trial, with Google Free active. Preserve existing personal catalogs; existing users can add Trial through **+ Trial**.
- Trial uses `https://api.vilao.ai/v1` and gateway model IDs `gemini-3.8-flash`, `gpt-6-luna`, `gpt-6-sol`. Validate the fixed connection/model allowlist on load, save and provider creation, including imported or renamed profiles.
- Shipped keys are empty. The local `trial.json` and its personal key must stay out of Git/build artifacts. A missing Trial key is a setup state; attempting translation explains how to enter one.
- Reuse the existing OpenAI-compatible transport (Responses, Chat Completions or Completions), workers, prompts, cache, popup and save/apply behavior. Keep custom-provider support.

## Trial editor

Preserve the existing Dark Ocean layout. Show the API key, Endpoint selector (auto/responses/chat_completions/completions), model and three independent streaming override dropdowns: Ultra Fast, Fast and Quality, each with inherit/on/off. New profiles default to auto; existing saved endpoint modes are retained through normalization/factory/save/reload. Endpoint URL/paths remain fixed. This replaces the earlier single-switch design.

Display friendly model labels while retaining raw IDs as combo item data for transport:

| Model | Illustrative starting cost per request |
| --- | --- |
| GPT-6 Luna | 1đ/lượt |
| Gemini 3.8 Flash | 3đ/lượt |
| GPT-6 Sol | 4đ/lượt |

These are user-selected estimates for this gateway, not authoritative upstream prices. Hide base URL, environment-key, timeout/SSL and model-management controls for Trial.

## Local estimated budget

The gateway has no quota API. Per the user's revised direction, display a local estimate instead of the earlier unavailable state. Start at 100đ per key per Vietnam calendar day (UTC+7). Subtract the chosen model's fixed estimate once after each successful network translation or provider test, including one deduction after a complete stream. Cache hits and failed requests do not deduct. Clamp the display to zero; zero does not block requests.

Use a slim dark track with a white remaining segment. Do not show money amounts, percentages or numeric quota tooltips. Below the bar display: **Hạn mức ước lượng, không chính xác. Chi phí thực tế tùy độ dài văn bản.**

Persist the current day, spent estimates keyed by a SHA-256 hash of the stripped API key, and only the two latest date/time checks in `data/trial_usage.json`. Use the existing atomic settings store and serialize concurrent writes. On each app/store startup, compare the current Vietnam date/time with the latest check; if the date crossed midnight, clear spent, write the new check and retain two checks. Refresh for key/form changes, translation/test completion and once per minute while the Trial editor is visible.

This estimate is local to one installation and depends on its clock. It does not measure token usage, gateway charges, other devices or requests made elsewhere; incomplete/failed streams may still have real gateway charges. Actual quota enforcement remains with the gateway. No quota endpoints are guessed. A future authoritative balance needs a documented gateway API and is outside this change.

## Implementation and validation

- `app/trial.py`: fixed profile configuration, model names and illustrative costs.
- `app/services/trial_usage.py`: per-key daily estimate persistence and concurrency protection.
- `app/providers/trial_provider.py`: successful-request accounting over the existing transport; local persistence failure does not discard translation output.
- `app/ui/main_window.py` and controller callbacks: priced model selection, independent streaming overrides and estimate refresh.
- Tests cover clean defaults/personal catalog preservation, pinned settings, raw model IDs, endpoint routing/auto fallback, stream roundtrips, daily reset/key isolation, visible timer refill, concurrency, successful requests, caching, failures and streaming accounting. Full suite: 187 passing tests.
- UI render checks cover 1280px and 900px widths. Compile/native offline self-check evidence is recorded in `IMPLEMENTATION_HANDOFF.md`.

No personal key or paid live gateway request is used for validation. This change does not add registration, device binding, billing infrastructure, automatic fallback or Argos. No installer rebuild, repository push or release publication is included.
