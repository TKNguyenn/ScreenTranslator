# CURRENT PLAN - AI SCREEN TRANSLATOR

**Project:** AI Screen Translator for Windows  
**Source status:** V0.4.1.11: Microsoft Translator with local usage accounting, simplified language toolbar and borderless pin icon. Built and verified on 2026-10-20; 215 tests and 9 packaged checks pass. Earlier planning sections below are historical.
**Primary platform:** Windows 10/11 x64  
**Recommended Python for source builds:** 3.11 / 3.12  
**Planning rule:** ưu tiên khả năng dịch nhanh từ bôi đen (Quick UX) trước Live Screen, nhưng giữ kiến trúc tái sử dụng cho Region -> Live Screen -> PDF. Không viết feature one-off.

---

## AI Trial — implemented in source (2026-10-17)

- Follow-up: Trial exposes Endpoint (`auto`, `responses`, `chat_completions`, `completions`); new profiles default to auto and existing saved modes are retained. Selection survives save/reload and factory validation; URL/paths/models remain pinned. On every app/store startup, the local usage file compares the current Vietnam date/time with the latest check, resets after a day change, saves the new check and keeps only two checks. The visible timer still checks within one minute. Endpoint routing/fallback, startup history/reset and visible day-change tests added: **188 tests pass**, compile and all seven native offline checks pass; updated 1280px/900px renders in artifacts/trial-ui/trial-endpoint-*.png.
- Fresh packaged defaults and source examples contain exactly Google Translate Free + Trial; Google Free remains active with no key required. Existing user catalogs are not overwritten. Existing users can add the built-in profile with **+ Trial** and save/apply.
- Trial connection/model definition is in `app/trial.py`, based on the user-supplied local `trial.json`: fixed gateway, three selectable models, empty shipped key. Local trial.json is ignored by Git and excluded from the publication checklist; it is not used as a packaged secret/config source.
- Trial editor shows API key, priced model selection and the original three streaming overrides (Ultra Fast / Fast / Quality, each inherit/on/off). This supersedes the initial one-switch interpretation. Labels show Luna from 1 VND/request, Flash from 3, Sol from 4; raw model IDs remain in saved settings and API payloads. Advanced connection fields/model editing stay hidden for Trial, while custom providers retain their editor. Factory/config/catalog normalization pins the built-in settings after import/save/reload/rename; it is not server authorization.
- User clarified that the slim white-on-dark quota bar should be a **local estimate** rather than wait for a gateway API. It starts at 100 VND/day, with no numeric quota labels, and deducts the selected model's fixed illustrative price once after a successful network translation or provider test. Cache hits and failed requests do not deduct. The note below explicitly says the estimate is not accurate and actual cost depends on text length.
- `TrialUsageStore` reuses atomic RuntimeSettingsStore writes in data/trial_usage.json, serializes concurrent workers, identifies keys by SHA256 without storing the key, survives restart and resets the local estimate after the startup/current-date check detects a new Vietnam calendar day (UTC+7). It stores only the current spent map and the two latest date/time checks. The bar refreshes on key/form changes and results, and once per minute while visible. Zero only empties the bar; it does not block requests or claim the gateway is exhausted. This file is local to each machine, not a shared balance.
- `TrialProvider` wraps the existing OpenAI-compatible transport to record one estimate after successful normal/streaming completion; cache bypasses the provider. Local write failure keeps the successful translation. Reuse worker/popup/cache/prompts; no new dependency or billing server. Empty-key Trial can remain inactive; using it without a key gives setup guidance.
- Verification: **188 unit/widget tests pass**, including 13 Trial tests covering fixed settings/import restrictions, raw model IDs with priced labels, endpoint selection/routing/auto fallback, independent streaming, clean bootstrap/catalog retention, save/reload, per-key/day persistence, two-check startup reset, visible daily refill, concurrency and success/cache/error/stream accounting. Final compileall and all seven native offline source self-checks pass; 1280px/900px UI renders inspected. Details recorded in the handoff.
- Evidence: `artifacts/trial-ui/` and `artifacts/trial-source-self-check.json`. Trial-specific design/plan: `docs/superpowers/specs/2026-10-17-ai-trial-design.md`, `docs/superpowers/plans/2026-10-17-ai-trial.md`.
- Pending: real gateway key/model/streaming acceptance and provider-side daily-budget validation. No live paid request, installer rebuild, sync, push or release for this change. The existing Setup executable predates Trial and must be rebuilt/verified against the accepted source before publication. App version remains 0.4.1.9 for now; select the release version before building/publishing.

## Hotkey settings follow-up (2026-10-17)

- Added a dedicated **Cài đặt** sidebar page with seven editable `QKeySequenceEdit` fields: translate selection, translate and replace, Live toggle, Region Translate and three target-language shortcuts.
- Hotkeys are normalized to the `keyboard` package format, validated as non-empty and unique, and saved atomically under `config.json.hotkeys` with release delay and suppress behavior. Save & apply reloads the runtime and re-registers global hotkeys without restarting the app; reset restores defaults.
- UI coverage includes the new page/icon, editable shortcut emission and duplicate validation. Full suite: **189 tests pass**; compile and native offline self-check pass.

---

## Daily startup update check (2026-10-17, V0.4.1.10)

- User accepted the provider-save fix and requested automatic update checks when reopening the app on a new day, sharing Trial data.
- TrialUsageStore atomically claims `last_update_check_date` in the same data/trial_usage.json, independently of the two-check quota history. First startup checks; subsequent startups on the same Vietnam calendar day skip; a later day checks again even after several days away. Trial writes/reset preserve the marker and quota data.
- Controller schedules this after showing the main window via a zero-delay Qt timer and reuses the manual asynchronous metadata-check path. It never starts a download automatically. Offline attempts count for the day; manual retry is unrestricted. Marker write errors log and skip automatic checking without blocking startup.
- Validation includes startup wiring, same-day restarts, skipped days, quota preservation/reset, concurrent Trial writes, manual retry and avoiding automatic download. Verified: 196 unit/widget tests and compileall pass; rebuilt 0.4.1.10 Setup succeeds. Packaged offline self-check passes all 8 checks, and archive inspection confirms the daily startup wiring and marker method are bundled. Evidence: artifacts/daily-update-tests.log, daily-update-build.log and daily-update-self-check.json. Full install/uninstall and live GitHub checks were not repeated; no sync/push/release performed.

## Provider save hotfix (2026-10-17)

- Reproduced the save failure when a regular provider uses the Trial gateway with a model outside the Trial allowlist. URL-based Trial detection incorrectly applied Trial restrictions and blocked the entire provider save before disk writes.
- Trial identity now requires `type=ai_trial` or the reserved catalog name `Trial`. Custom providers sharing the gateway keep their model list and OpenAI-compatible behavior. Renamed Trial profiles retain their type in config overrides; a renamed portable-only export needs Trial type reapplied to retain Trial behavior.
- Validation: 191 tests pass, including regression coverage for parsing/catalog save/reload/factory and UI-to-controller saves from every profile. Compileall passes. Local 0.4.1.10 Setup build and packaged offline self-check pass (8 app checks plus frozen Trial identity regression); evidence: artifacts/provider-save-hotfix-self-check.json. No hotfix publication requested/performed.
- No installed personal configuration/catalog was edited. Existing 0.4.1.9 EXEs need the new installer to receive this fix.

# 1. Mục tiêu sản phẩm dài hạn

AI Screen Translator hướng tới một ứng dụng Windows có hai lớp sử dụng:

1. **System Tray / hotkey** cho thao tác nhanh hằng ngày.
2. **Main Window** cho cấu hình nâng cao và các workflow lớn như Screen Translate, PDF, History, Glossary, Benchmark.

Các workflow cuối cùng cần hỗ trợ:

- Bôi đen text ở bất kỳ app nào -> dịch -> popup.
- Bôi đen text -> dịch -> replace vào app nguồn nhưng không tự Enter/send.
- Kéo vùng màn hình -> OCR local -> dịch.
- Live Translate cửa sổ/vùng màn hình bằng OCR tracking + overlay.
- Dịch PDF text và PDF scan.
- Provider/model tùy ý qua API OpenAI-compatible.
- Prompt tùy chỉnh theo `speed x style`.
- Glossary kỹ thuật và Translation Memory.
- History riêng cho người dùng.
- Benchmark model/provider/streaming ngay trong app.
- Đóng gói `.exe`/installer để người dùng cuối không cần Python.

Nguyên tắc quan trọng:

- `main.py` chỉ bootstrap, không biến lại thành script monolithic.
- Network không chạy trên Qt UI thread.
- OCR không chạy trên Qt UI thread.
- Ảnh Region/PDF scan mặc định phải OCR local; provider dịch chỉ nhận text trừ khi tương lai người dùng chủ động chọn multimodal cloud OCR.
- Provider, prompt và dữ liệu người dùng phải portable/migrate được giữa các version.
- Feature mới phải dùng lại infrastructure hiện có thay vì tạo pipeline dịch riêng.

---


## V0.4.1.9 - GitHub in-app updates (2026-10-16)

Replace sidebar's Aurora/tray footer with Check for updates, version/status and download progress. Manual checks only against https://api.github.com/repos/TKNguyenn/ScreenTranslator/releases/latest. Numeric stable versions; never downgrade. Validate exact repository/tag/installer filename, positive bounded size and GitHub SHA256. Native Qt networking keeps the UI responsive, handles HTTPS redirects/timeouts and streams a partial file under app/data/updates. Bad/truncated/oversized downloads, network errors and shutdown cancel without executing anything.

An available release changes the button to Update to v... . Installed Windows builds download/verify, copy a native C# helper to the download directory, hand off and quit. Helper waits for app exit, rechecks/locks SHA256, runs existing Inno Setup silently with the exact current /DIR and /UPDATE=1, restarts only on success, deletes the large installer. /UPDATE=1 does not recreate a previously omitted desktop shortcut. Source runs can check but install through Git/Setup. Catalog/config/data retention uses the existing installer. Public API currently serves v0.4.1.8 with verified asset digest; 0.4.1.9 requires one manual Setup install to bootstrap updater and a new GitHub release published by the user. Current workspace has no .git; no push/publish performed.

Verified: 175 tests pass, source compile passes, compact sidebar preview inspected. Real Qt HTTPS downloads the public v0.4.1.8 installer and verifies size/SHA256 without executing it; native fixture confirms waiting/quoted target/silent args/relaunch/large-file cleanup (artifacts/update-smoke.json). Real 0.4.1.9 frozen Qt/TLS/UIA/OCR plus install/reinstall/both uninstall modes pass (17 checks, artifacts/release-install-uninstall.json). Targeted real Setup /UPDATE=1 install/reinstall confirms helper inclusion, no unsolicited desktop shortcut and byte-identical config/catalog retention (artifacts/update-installer-smoke.json). release/AI-Screen-Translator-0.4.1.9-Setup.exe built and SHA256 verified. Future-version end-to-end acceptance, clean second-PC and signing remain pending.

## V0.4.1.8 - Combined installation and data location (2026-10-16)

Frozen application_root is sys.executable.parent, independent of cwd. Config/catalogs/.env sit beside exe; data/ holds cache/runtime settings/logs. Python source root is unchanged. Setup imports legacy config/catalog/.env/data only if no local config/catalog exists, copies missing files, retains original legacy files for recovery until uninstall. Reinstall preserves local files and never revives legacy settings when catalogs were retained.

Uninstall removes known runtime files/data plus tracked payload, never recursively deletes the selected app root. Keep mode restores precisely two catalogs to the install folder, using recovery outside both app and legacy roots. Full mode removes app-owned content and empty folders; unrelated user files at install root survive. Existing append-only unconditional legacy deletion logs remain covered by catalog recovery.

Verified: 165 tests and source compile pass. Native 0.4.1.8 sandbox passes 16 checks including real Qt/UIA/OCR, legacy migration without changing originals during setup, config/catalog preservation, old unconditional uninstall-log upgrade, locked-catalog abort, both removal modes, clean full removal, custom folder, mutex and unrelated-file/junction-target survival. Setup and standalone launcher built; release/SHA256.txt verified. Interactive acceptance, signing and clean second-PC remain unchecked.

## V0.4.1.7 - Uninstall retention choices (2026-10-16)

User requested Uninstall.exe with exclusive keep-provider/prompt and full-delete options. Native Inno uninstaller now offers a default keep mode and explicit remove-all mode. In keep mode, it backs up only providers.json/prompts.json outside the logged deletion tree before removing app files, then restores both byte-for-byte. Backup failure aborts before removal; restore failure preserves a recovery folder and reports its path. Old unconditional data deletion records from prior installs are handled by this backup/restore. A tiny C# Windows launcher resolves HKCU x64 registration/custom install location, requires DisplayVersion >= 0.4.1.7 and exits immediately after launching to allow its own deletion. Installer replaces Uninstall.bat with Uninstall.exe; Start Menu/Settings/direct native exe use the same choice dialog. Silent defaults to keep; /DATA=all is explicit full deletion.

Verified: 165 tests pass; source compile passes. Real 0.4.1.7 frozen self-check/OCR, custom-location install/reinstall, keep-only-two-files byte-for-byte, recovery-folder cleanup, locked-catalog abort, invalid-mode abort and full removal through the installed Uninstall.exe pass in the isolated Windows smoke. Running-app guard and unrelated/junction target survival pass. Artifacts: release/AI-Screen-Translator-0.4.1.7-Setup.exe, release/Uninstall.exe, release/SHA256.txt. Native interactive radio dialog has compiled; mouse/keyboard acceptance and clean second-PC/signing remain unverified.

## V0.4.1.6 - Windows release packaging (2026-10-16)

User requested a standalone Windows app and uninstall file. PyInstaller onedir bundles Python, Qt/assets, RapidOCR models and ONNX/native UIA/input backends. Inno Setup generates a single per-user x64 Setup exe; installed app has a standard uninstaller and Uninstall.bat, also supplied alongside Setup. No admin/Python dependency on target machine. No upload/publication was requested or performed.

Installer follow-up: always show the destination page (default plus Browse); final page offers a checked-by-default desktop shortcut checkbox. Start Menu links remain installed. Standalone Uninstall.bat reads the per-user x64 uninstall registration so custom locations work. Qt failed to initialize platform plugins at a deeply nested sandbox destination; installer now rejects paths over 180 characters before writing installed files.

Frozen config/data lives in `%LOCALAPPDATA%/AIScreenTranslator`; source runs keep the existing project paths. First-run defaults are bundled clean (Google Free, empty key); no live config/catalog/prompts/cache/log is packaged. Missing default files are created only, existing settings survive reinstall/update. Dotenv loads from the config directory, avoiding unrelated cwd files. Installed application holds an Inno AppMutex so installation/uninstall requires app exit.

Uninstall owns installed files/shortcuts/uninstall registry and the fixed per-user data directory, including stored API keys/prompts/cache/logs. It does not follow arbitrary externally configured data paths or erase source/exported files. Self-check verifies UI/resources, keyless provider construction, native COM/input backend imports and real RapidOCR on synthetic text without API/clipboard/hooks.

Validation: 164 tests and compile pass; sandbox installer/exe/reinstall/uninstall workflow passes, including the running-app uninstall guard and preservation of unrelated files and junction targets. Artifacts: `release/AI-Screen-Translator-0.4.1.6-Setup.exe`, `release/Uninstall.bat`, `release/SHA256.txt`; reports in `artifacts/release-*.json`. Build: `packaging/build.ps1`; user guide: `docs/Windows_Release.md`. No signing certificate, no clean second-PC or real-provider acceptance check.

## V0.4.1.5 - Google translation providers (2026-10-15)

User approved integrating the supplied `google_translate_addon_for_codex.py` into the current app. Runtime adapters are in `app/providers/google_translate_addon.py` and subclass the existing provider ABC; factory/config infer canonical Google URLs while retaining other provider routes. Google Web Free uses the unofficial keyless GET endpoint; Cloud Basic v2 uses POST and an API-key header. Neither streams or accepts AI prompt/style/speed settings. No automatic Free-to-Cloud fallback.

Provider Manager has two opt-in preset buttons and provider types; additions preserve existing entries and active selection, remain editable/renamable/removable and save using the existing portable 3-field catalog. Cloud can be stored with an empty key while inactive; applying/testing it validates key presence. Irrelevant controls are disabled and service/privacy/cost limitations are shown. AI global settings are preserved. Google cache scope ignores style/speed/prompt while preserving text/source/target/provider/model distinctions; LLM prompt fingerprint rules remain unchanged. Provider Test now translates Hello from English to Vietnamese.

Verified: 160 tests PASS, compileall PASS, native Google UI smoke PASS (preset forms, compact layout, preserved active provider, restored AI controls), native Quick UX UI smoke PASS. Response tests use MockTransport; no live Google endpoint, paid key or billing/account validation was performed. New guide: `docs/Google_Providers_V0_4_1_5.md`; synthetic native previews: `artifacts/google-v0415/`.

## V0.4.1.4 - Dark Ocean Aurora Bento (2026-10-14)

User selected logo concept 1 (Glyph Slash) and UI concept 1 (Aurora Bento) from `demo_UI_ver2`. Applied the deep ocean #080E1A / cyan #38BDF8 / emerald #10B981 identity across six manager pages, tray/menu/dialog controls, Quick Toolbar, Quick Popup, legacy translation popup and region selector. Reference assets are bundled under `app/assets`, with a shared Fusion palette/QSS theme and native-painted Aurora hero. No external demo path is required at runtime.

Overview cards use real runtime state; capture CTA uses the existing region signal and feature flag. Form pages scroll vertically; provider footer and prompt actions adapt to the minimum 900×620 window. Quick Popup retains dragging, resizing, pin/source panes and stable result/error geometry. Glass appearance uses painted layers and opaque floating-card content for readability. Translation, OCR, workers, portable provider/prompt files and clipboard contracts remain intact. PDF remains a future feature.

Verified: 142 tests PASS, compile PASS, native Windows Qt smoke PASS with the global theme enabled. Actual widget previews for all six pages at 1180×800 and 900×620 plus both popup variants are in `artifacts/ocean-v0414/`. Full real-provider/external-application/DPI acceptance remains pending. Design and reproducible checks: `docs/Ocean_UI_Design_V0_4_1_4.md`.

## V0.4.1.3 - Quick UX UI / popup interaction (2026-10-12)

User confirmed toolbar now appears after the UIA hotfix, then reported missing toolbar/popup background and requested redesigned UI plus moving/resizing the translation popup.

Completed: shared `FloatingSurface` explicitly paints an opaque rounded card (custom QWidget stylesheet did not reliably paint the transparent toolbar); navy/teal high-contrast controls; drag handles in popup header/metadata; border resizing and bottom-right QSizeGrip; expandable output/original panes. Removed fixed width and final/error repositioning. Size is retained for the process session; each new request starts near its selection. Pin/Copy/Replace/close, no-activate/topmost, worker streaming and one-shot language behavior remain supported. Menu stays open without the toolbar timeout dismissing it.

Verified: 135 unit/widget/source tests PASS, compile PASS; native Windows Qt smoke PASS for opaque backgrounds, WS_EX_TOPMOST, WS_EX_NOACTIVATE, header drag and retained geometry. Preview rendered from actual widgets in `artifacts/quickux-v0413-preview.png`. Full app-source selection -> real-provider translation interaction and wider DPI/application matrix still need user acceptance.

## V0.4.1.2 - Quick UX UIA compatibility hotfix (2026-10-12)

Latest Windows logs confirm a running mouse hook and recognized gestures, followed by empty UIA results. Added generic pattern access for Custom/Pane controls, deeper ancestor traversal and bounded source-window descendant traversal. Diagnostics now includes content-free probe details rather than treating every exception as unsupported selection. Win32 HWND signatures are pointer-sized. SQLite connections are explicitly closed and old source tests read UTF-8 on Windows.

Verified: 124 unit/source tests PASS, compile PASS, offscreen native Windows RichEdit UIA selection smoke PASS. User-facing Notepad/browser mouse -> toolbar -> translation acceptance remains pending. The exact cause of the user's cross-app failure requires restart and the new probe diagnostics if symptoms persist. No automatic Ctrl+C/API calls during selection detection.

## V0.4.1.1 - Quick UX auto-toolbar hotfix (2026-10-12)

User-reported: selecting text did not show the floating toolbar. Root cause found in source: old `pynput` mouse `on_click` callback only accepted four positional arguments, but current package may pass five including `injected`, terminating the listener callback thread.

Completed: accept 4/5-argument callbacks; don't react to injected clicks; avoid uncaught mouse-hook callback exceptions; log hook startup, gesture, and UIA absence; surface `mouse hook running` and `last probe` in Diagnostics; new regression tests and Windows troubleshooting guide. The popup continues to appear only after a toolbar language is clicked, not on selection alone.

Acceptance still pending real Windows: confirm tray version 0.4.1.1 after fully exiting old process; Notepad drag-select -> toolbar -> VI -> popup; test Chrome/Edge; inspect Diagnostics when UIA doesn't support text selection; test 100/125/150%% DPI; confirm legacy Alt+T. No silent clipboard polling fallback.

If Notepad still fails after mouse hook confirmed alive: gather `data/logs/app.log` and Diagnostics; address specific UIA/Qt compatibility issue in another hotfix before Live/PDF.

# 2. Trạng thái hiện tại - V0.4.1

## 2.1. Core translation đã ổn định

Đã có:

- Global hotkey thread.
- Selected-text capture bằng clipboard.
- Translate popup.
- Translate + Replace.
- Provider switching runtime.
- Target language switching runtime.
- Style switching runtime:
  - Engineer
  - Chat
  - Email
- Speed switching runtime:
  - Ultra Fast
  - Fast
  - Quality
- Streaming theo từng speed.
- Streaming override theo từng provider profile.
- RAM LRU + SQLite translation cache.
- Cache fingerprint theo effective prompt.
- OpenAI-compatible endpoints:
  - `/responses`
  - `/chat/completions`
  - `/completions`
- Arbitrary model ID.
- Runtime config reload.
- Single-instance guard.

## 2.2. Desktop Manager

Main Window hiện có:

- Tổng quan.
- Provider & Model.
- Prompt Editor.
- Dịch vùng màn hình.
- Quick UX Settings (tự hiện toolbar mặc định ON).
- PDF placeholder.

Window behavior:

- Startup -> Main Window xuất hiện.
- Minimize -> ẩn xuống System Tray.
- X -> thoát hoàn toàn.
- Double-click tray -> restore Main Window.
- Right-click tray -> quick controls.

## 2.3. Portable configuration

### `providers.json`

Source of truth cho:

- provider name
- base URL
- API key
- model list

Schema portable cố ý giữ tối giản.

### `prompts.json`

Chỉ chứa custom prompt override của user.

Prompt mặc định vẫn nằm trong source để bản mới có thể cải tiến default mà không làm user bị kẹt ở default cũ.

### `config.json`

Chứa behavior riêng của app:

- active provider/model
- endpoint mode
- timeout
- streaming
- cache
- hotkey
- OCR settings
- feature flags
- UI timing

### `data/runtime_settings.json`

Chứa lựa chọn runtime/tray gần nhất:

- provider hiện dùng
- target language
- style
- speed

---

# 3. V0.4.0 Region Translate - phạm vi đã code

## 3.1. User flow

```text
Alt+S / Tray / Main Window
        |
        v
Hide manager nếu cần
        |
        v
Chọn monitor tại vị trí con trỏ
        |
        v
Overlay tối + kéo chuột chọn vùng
        |
        v
Capture PNG local
        |
        v
OcrWorker
        |
        v
RapidOCR local
        |
        v
OCR text
        |
        v
TranslationWorker hiện tại
        |
        v
Provider/model hiện tại
        |
        v
Translation Popup
```

## 3.2. Region selector

V0.4.0 có:

- Hotkey mặc định: `Alt+S`.
- Tray action: `Dịch vùng màn hình`.
- Main Window page: `Dịch vùng màn hình`.
- Crosshair cursor.
- Dark overlay.
- Left-drag để chọn.
- `Esc` để cancel.
- Right-click để cancel.
- Reject vùng quá nhỏ.
- Hiển thị width x height của selection.
- Capture ảnh trước khi overlay xuất hiện để overlay không lọt vào OCR image.

## 3.3. Multi-monitor strategy của V0.4.0

V0.4.0 hỗ trợ nhiều monitor theo cách an toàn:

- Monitor được chọn là monitor chứa cursor lúc Region Translate bắt đầu.
- Có thể dịch vùng trên bất kỳ monitor nào bằng cách đưa cursor sang monitor đó rồi kích hoạt Region Translate.
- Một selection không kéo xuyên qua hai monitor.

Lý do chưa cho cross-monitor selection:

- mỗi monitor có thể dùng DPI scaling khác nhau;
- Qt logical coordinate và screenshot pixel coordinate có thể khác nhau;
- việc ép cross-monitor ngay trong V0.4.0 tạo rủi ro crop lệch vùng.

Code hiện tại đã map:

```text
logical selection rectangle
          |
          v
screen logical geometry
          |
          v
screenshot actual pixel size
          |
          v
scale_x / scale_y
          |
          v
pixel crop
```

Đây là nền tảng để test 100%, 125%, 150%, 175% DPI trước khi nâng cấp cross-monitor.

## 3.4. OCR architecture

OCR không nằm trong Controller/UI.

```text
app/ocr/
  base.py
  factory.py
  rapidocr_engine.py
  mock_engine.py

app/workers/
  ocr_worker.py
```

Default engine:

```text
rapidocr_onnxruntime
```

Đặc điểm:

- Local inference.
- Lazy model initialization.
- First OCR request có thể chậm hơn.
- OCR chạy trong `OcrWorker` thread.
- Filter block theo `ocr.min_confidence`.
- Translation provider không nhận screenshot; chỉ nhận OCR text.

Config:

```json
"ocr": {
  "engine": "rapidocr",
  "min_confidence": 0.45
}
```

## 3.5. Threading model sau V0.4.0

```text
Qt Main Thread
  |- MainWindow
  |- TrayIcon
  |- TranslationPopup
  |- RegionSelectorOverlay
  |- AppController signals/slots

HotkeyThread
  |- keyboard global hook

InputWorker
  |- Ctrl+C capture
  |- Ctrl+V replace

OcrWorker
  |- local OCR inference

TranslationWorker
  |- cache
  |- provider API
  |- streaming parser
```

Không được chuyển OCR/network sang UI thread trong các version sau.

## 3.6. Region translation behavior

Region request dùng:

```text
RequestMode.REGION
```

Khác selected-text popup:

- Region result không có source HWND hợp lệ.
- Vì vậy `Replace in source app` bị disable cho Region Translate.
- OCR text được dùng làm `source_text` cho TranslationWorker.
- Translation cache vẫn áp dụng bình thường theo OCR text + prompt/model/context.

## 3.7. V0.4.0 acceptance criteria

Được coi là hoàn tất khi trên Windows thực tế:

- [ ] `Alt+S` mở selector ổn định.
- [ ] Main Window button mở selector.
- [ ] Tray action mở selector.
- [ ] Esc cancel không để lại overlay.
- [ ] Right-click cancel không để lại overlay.
- [ ] Chọn Chinese Traditional text -> OCR ra đúng text đủ dùng.
- [ ] Chọn English text -> OCR ra đúng text đủ dùng.
- [ ] OCR không freeze app.
- [ ] API call không freeze app.
- [ ] Popup hiện OCR text + translation.
- [ ] Region popup không cho Replace.
- [ ] Monitor 1 hoạt động.
- [ ] Monitor 2 hoạt động.
- [ ] 100% DPI hoạt động.
- [ ] 125% DPI hoạt động.
- [ ] 150% DPI hoạt động.
- [ ] Reload config thay OCR min confidence mà không restart.
- [ ] Không upload screenshot tới translation provider.

Automated build-time suite hiện kiểm tra kiến trúc/config/parser/worker/source integration; Windows GUI smoke test vẫn phải chạy trên Windows thật.

---

# 4. V0.4.1.x - Region/Quick UX Stabilization (Windows smoke tests)

Không nhảy thẳng vào Live Translate nếu Region Translate chưa ổn trên máy thật.

## 4.1. Test matrix bắt buộc

### Display

- Single 1080p / 100%.
- Single 1440p / 125%.
- Single 4K / 150% hoặc 175% nếu có.
- Dual monitor cùng DPI.
- Dual monitor khác DPI.
- Secondary monitor nằm bên trái primary nếu có thể.

### Source content

- Chinese Traditional UI.
- Chinese Simplified UI.
- English software UI.
- Industrial HMI screenshot.
- Browser text.
- Small font.
- White-on-dark text.
- Dark-on-white text.
- Anti-aliased Windows UI text.

### OCR confidence

Benchmark các mức:

```text
0.30
0.40
0.45 default
0.55
0.65
```

Không chọn threshold chỉ dựa trên một ảnh.

## 4.2. V0.4.1.x fixes dự kiến

Nếu smoke test tìm ra vấn đề, ưu tiên:

1. DPI crop lệch.
2. Overlay không phủ đúng monitor.
3. Keyboard focus khiến Esc không cancel.
4. OCR block order sai.
5. OCR model init quá lâu.
6. Region hotkey xung đột app khác.
7. Popup che mất vùng cần nhìn.

## 4.3. Có thể thêm OCR Settings UI

Nếu OCR cần tuning thường xuyên, thêm vào Screen Translate page:

```text
OCR Engine: RapidOCR
Minimum confidence: 0.45
[ Test OCR from image ]
```

Không ưu tiên trước khi có dữ liệu thật cho thấy user cần chỉnh thường xuyên.

---

# 4A. V0.4.1 - Quick UX / Floating Toolbar (đã code)

> **Ưu tiên được thay đổi ngày 2026-10-12 theo quyết định của user:** đưa Quick UX (trước dự kiến V0.7) lên sau V0.4.0. **Auto-show mặc định ON**, không còn OFF như mockup đầu tiên. P0 ship trước; Explain/Summarize/Quick Compose ở P1.

## 4A.1. Quyết định UX đã khóa

- Bôi đen bằng **chuột kéo hoặc double-click** tại ứng dụng ngoài -> đợi 250 ms -> floating bar hiện gần con trỏ: `VI | EN | 繁 | ⋯`.
- Chỉ có signal mouse-up -> **Windows UI Automation TextPattern.GetSelection**, hoàn toàn không dùng Ctrl+C để dò tự động.
- Mouse selection mà user chưa bấm nút => **không gọi API, không sửa clipboard, không ghi source text vào log**.
- `VI / EN / 繁` gọi đúng provider/model, style, speed, streaming, prompt catalog và cache đang dùng. Chọn target trên toolbar là **one-shot override**, không làm thay đổi target cấu hình toàn app.
- `⋯` -> Dịch và thay thế / Cài đặt Quick UX / Ẩn toolbar. Explain/Summarize chuyển sang bản tiếp theo để không làm nhầm chức năng giả vào UI thực.
- QuickPopup ~414px không chiếm focus, có status, streaming partial, Copy, Replace, Xem gốc, Pin, Close.
- User click ngoài -> ẩn floating bar; popup ẩn nếu unpinned và setting `dismiss_popup_on_blur=true`. Pin cho phép xem bản dịch lâu hơn.
- Escape từ global keyboard hook chỉ đóng Quick UI, **không bị suppress** trong ứng dụng nguồn.
- Vị trí dùng Qt logical coordinates và screen.availableGeometry; giới hạn vùng nhìn được, hỗ trợ monitor có tọa độ âm.
- Existing Alt+T / Alt+Shift+T / Alt+S / tray Region / Main Window/Prompt Studio hoạt động như trước.

## 4A.2. Runtime pipeline và threading

```text
Global mouse listener (pynput, daemon)
       | left-drag / double-click candidate
       v
WorkerBridge.quick_mouse -> Qt GUI thread
       | debounce 250ms, generation counter
       v
QuickSelectionWorker (separate COM-initialized thread)
       | GetFocusedControl / ControlFromPoint
       | UIA TextPattern.GetSelection; reject password/empty/too long
       v
WorkerBridge.quick_probe -> Qt GUI
       | current generation only
       v
QuickToolbar (WindowDoesNotAcceptFocus)
       | user clicks VI / EN / 繁 (NO auto API)
       v
TranslationWorker (unchanged cache/stream/model/prompt)
       | progress delta -> throttled QuickTranslationPopup (55ms)
       | final -> Copy / UIA-verified Replace / Pin
       v
InputWorker (if explicit Replace)
       | verify selected text once more via Ctrl+C (explicit action only)
       v
Paste with existing clipboard service
```

### `AppController`

- Lưu `SelectionSnapshot` + source HWND + UIA control identity.
- `serial` generation bảo vệ kết quả UIA cũ khỏi làm toolbar hiện khi user đã chọn vùng khác.
- `job_id` bảo vệ stream/final cũ khỏi ghi đè QuickPopup của tác vụ mới.
- `quick:bool` trên PendingJob giúp route QuickPopup riêng, không ảnh hưởng popup selection/Region cũ.
- Nếu UIA verification hoặc final clipboard selection check không khớp -> **không dán**; hiển thị lý do trong QuickPopup.
- Nếu app không hỗ trợ UIA -> im lặng không hiện toolbar (không đọc clipboard thay thế), hotkey Alt+T dùng được.

### `app/quickux/*`

- `selection.py`: immutable selection snapshot, pure mouse gesture logic (drag and double-click).
- `mouse_monitor.py`: `pynput` hook; own-process/shell filtering. Không dùng Qt ở hook thread.
- `uia_reader.py`: UI Automation TextPattern; skip password, bounded text, read-only check; UIA COM only in worker.
- `selection_worker.py`: COM context per thread, asynchronous probe + verify. Không UIA/network trên Qt.

### `app/ui/*`

- `quick_toolbar.py`: noactivate compact pill, controls, timeout; screen clamping.
- `quick_popup.py`: noactivate result card, pinned state, Copy/Replace, 55ms stream coalescing.
- `main_window.py`: Quick UX Settings page với Save/Reset.
- `tray.py`: checkbox bật/tắt auto show, link trang Quick UX Settings.

## 4A.3. Settings mặc định, lưu và reload

`config.json` chứa:

```json
"quick_ux": {
  "auto_show_toolbar": true,
  "selection_delay_ms": 250,
  "languages": ["vi", "en", "zh-Hant"],
  "dismiss_popup_on_blur": true,
  "toolbar_timeout_ms": 8000,
  "max_selection_chars": 6000
}
```

- Auto-show ON là quyết định đã chốt, người dùng vẫn có thể tắt từ tray hoặc Settings.
- `Settings -> Quick UX -> Lưu & áp dụng`: atomic-write `config.json`, áp dụng động (không restart).
- `Reset`: trả về ON/250ms/3 nút/8 giây/limit 6000 và ghi file.
- `Reload config`: đọc Quick UX cùng provider/prompts/other config.
- `providers.json` và `prompts.json` không bị ghi Quick UX settings.

## 4A.4. Privacy + safety invariants

1. Không API ở bước probe hay chỉ hiện toolbar; **bấm ngôn ngữ hoặc Replace mới tạo TranslationRequest**.
2. Bỏ qua UIA password fields / password-like AutomationId, không dùng document text hay ValuePattern để giả làm selection.
3. Không Ctrl+C thăm dò sau mỗi lần chọn; clipboard chỉ được đụng tới bởi hotkey cũ hoặc thao tác Copy/Replace rõ ràng.
4. Không gửi ảnh màn hình tới AI trong Quick UX.
5. Không gọi UIA hoặc API từ Qt GUI thread, không gọi Qt từ global mouse hook.
6. UIA UI không phải tất cả Windows applications đều hỗ trợ; code phải fail closed và hotkey fallback.
7. Để tránh paste nhầm, trước Replace xác thực UIA text+identity+HWND; InputWorker tiếp tục so sánh clipboard-selected text ngay trước paste.
8. UIA và Ctrl+C vẫn có TOCTOU race nhỏ trong ứng dụng bên thứ ba, vì Windows không cung cấp transaction thay thế đa app. Không được quảng bá Replace an toàn tuyệt đối.

## 4A.5. Windows acceptance matrix (cần user chạy thực tế)

| Case | Kỳ vọng | Trạng thái |
| --- | --- | --- |
| Edge/Chrome chọn text bằng mouse drag | hiện toolbar sau ~250ms nếu expose UIA TextPattern | chờ test Windows |
| Edge/Chrome double-click một từ | hiện toolbar nếu UIA report selection | chờ test Windows |
| Windows Notepad 11 | detect selection hoặc fallback Alt+T | chờ test Windows |
| MS Word/VS Code | detect nếu UIA hỗ trợ; hotkey vẫn chạy | chờ test Windows |
| Password box | không toolbar / không đọc secret | unit pass; smoke test chờ |
| Chọn text nhưng không bấm bar | 0 network request, clipboard giữ nguyên | unit/source pass; smoke test chờ |
| VI/EN/繁 | gọi đúng target nhưng không đổi global target | source pass; smoke test chờ |
| Popup streaming | từng delta hiển thị, final còn đủ chữ | source pass; smoke test chờ |
| Replace rồi thay selection trong khi AI đang dịch | không paste khi verify fail | unit/source pass; smoke test chờ |
| ESC / click ngoài / pin | không cướp focus; ẩn theo policy | source pass; smoke test chờ |
| 100/125/150%, monitor trái/trên có tọa độ âm | popup clamp trong availableGeometry | source pass; smoke test chờ |
| Quick UX OFF -> hotkeys | alt+t/alt+shift+t/alt+s vẫn dùng như cũ | regression pass |
| Settings Save/Reset/Tray toggle/Reload | cập nhật ngay và persist | unit/source pass; smoke test chờ |

## 4A.6. Known limitations P0

- **Auto-detect ưu tiên drag/double-click bằng chuột**; selection bằng Shift+arrows/keyboard hiện dùng hotkey.
- UIA selection có thể không hoạt động trong trò chơi, trình đọc PDF riêng, control canvas, protected apps, session elevated, một số Office/Chromium phiên bản. Không fallback sang Ctrl+C tự động để tránh spam clipboard.
- Toolbar không tự dịch; phải click để chủ động gửi data ra provider.
- Explain, Summarize và Quick Compose chỉ có trong mockup, chưa được triển khai ở V0.4.1 P0.
- Clipboard service legacy chỉ restore plain text cho thao tác Replace/Alt+T; nên test kĩ nếu clipboard chứa rich content/ảnh.
- `WindowDoesNotAcceptFocus` và QMenu behavior phụ thuộc Windows/Qt cần smoke test; click popup/menu có thể khiến UIA selection thay đổi, code sẽ fail closed nếu không xác minh được.
- Chưa có hook UIA event-driven cho selection bằng keyboard, chưa có per-app blacklist UI, chưa có installer.

## 4A.7. Test plan và ngưỡng hoàn thành

- Unit: QuickUxSection validation/roundtrip, mouse gesture recognizer, UIA stubs (password/readonly/oversize/parent/no-selection/identity verification), worker queue, controller source wiring.
- Regression: toàn bộ tests V0.2.5 - V0.4.0 giữ nguyên; `python -m compileall` pass.
- Windows manual: 3 app thực tế x 2 loại selection x 3 DPI; screenshot/status log nếu không hiện bar.
- **Definition of done phát hành cho người khác**: Windows smoke test + bảo mật clipboard/Password đã xác nhận. Build ở Linux chỉ được gọi là source/test build.

---

# 5. V0.4.5 - Live Screen Translate

Đây là milestone lớn dự kiến sau khi Region Translate và Quick UX được smoke-test trên Windows; có thể ưu tiên Quick Compose (V0.4.2) trước.

## 5.1. Scope đầu tiên

Chỉ làm:

- Selected Region Live Translate.
- Current Window Live Translate.

Chưa làm Whole Desktop ngay.

Lý do:

- giảm OCR workload;
- ít noise;
- overlay management đơn giản hơn;
- phù hợp nhu cầu dịch phần mềm/HMI/manual viewer.

## 5.2. Pipeline dự kiến

```text
Capture loop 2-5 FPS
        |
        v
Frame differ / hash gate
        |
        v
OCR only when image changed enough
        |
        v
OCR blocks
        |
        v
Block tracker
        |
        +---- same text/location ----> reuse translation
        |
        +---- new/changed text ------> TranslationWorker
                                      |
                                      v
                                  overlay
```

## 5.3. Text block state

Mỗi block nên có tối thiểu:

```text
block_id
bbox
source_text
normalized_text
ocr_confidence
translation
first_seen
last_seen
stable_frames
source_hash
translation_state
```

## 5.4. Không gửi API mỗi frame

Điều kiện bắt buộc:

- Text đứng yên -> không dịch lại.
- Text chỉ rung bbox vài pixel -> vẫn cùng block.
- OCR confidence dao động nhỏ -> không coi là text mới.
- Source text hash giống -> reuse cache/memory.
- Block biến mất -> giữ overlay grace period ngắn rồi remove.

Mục tiêu:

```text
Static UI 30 giây
=> 1 translation request/block, không phải 60-150 requests.
```

## 5.5. Capture frequency

Khởi đầu:

```text
2 FPS default
5 FPS optional max
```

Không cần 30/60 FPS vì OCR + translation không phải video renderer.

## 5.6. Overlay strategy

Overlay text phải:

- click-through mặc định;
- không lấy focus từ app nguồn;
- follow window move/resize;
- có background opacity configurable;
- tránh che source hoàn toàn nếu user chọn bilingual mode.

Modes dự kiến:

```text
Replace visual
Bilingual under source
Side panel
```

V0.4.5 chỉ cần `Bilingual under source` hoặc một mode đơn giản ổn định trước.

## 5.7. Live Translate performance targets

Target đầu tiên:

- UI không freeze.
- Capture overhead thấp.
- OCR cycle <= 500-800 ms cho vùng vừa phải trên laptop hiện đại.
- Translation requests chỉ xảy ra khi text thay đổi.
- Overlay update <= 100 ms sau khi translation result có sẵn.

Không đặt target tổng latency AI thấp hơn khả năng provider thực tế.

---

# 6. V0.5.0 - PDF Translator

PDF chỉ nên bắt đầu sau khi OCR infrastructure đã qua Region/Live test.

## 6.1. Hai loại PDF

### Text PDF

```text
PDF
 -> extract text blocks
 -> preserve page/block order
 -> translate
```

Không OCR nếu PDF đã có text layer tốt.

### Scanned PDF

```text
PDF page
 -> render page image
 -> OCR engine dùng lại từ V0.4
 -> translate
```

## 6.2. V0.5.0 MVP

Main Window page:

- Open PDF.
- Page list/navigation.
- Original pane.
- Translation pane.
- Translate current page.
- Translate whole document background queue.
- Progress indicator.
- Cancel whole-document job.
- Cache translation per block/page.

Chưa cần export PDF hoàn chỉnh ở MVP.

## 6.3. V0.5.1 / V0.5.2

Sau khi reader ổn:

- Export bilingual text/DOCX.
- Export translated PDF.
- Better layout preservation.
- OCR page rotation.
- Skip diagrams/images unless requested.

---

# 7. V0.6.0 - Glossary + History + Translation Memory

## 7.1. Glossary

Use case chính là technical translation.

Ví dụ:

```text
治具 -> đồ gá
互鎖 -> liên động / interlock
原點復歸 -> homing / về vị trí gốc
伺服驅動器 -> servo drive
急停迴路 -> mạch E-stop
```

Không gửi toàn glossary mỗi request.

Pipeline:

```text
source text
 -> normalize
 -> find glossary matches
 -> only matched terms
 -> render {glossary}
 -> effective prompt
```

Prompt Editor V0.3.2 đã reserve:

```text
{glossary}
```

nên không cần migration prompt schema.

## 7.2. History

History khác Cache.

Cache:

- optimization layer;
- có thể clear/expire;
- key machine-oriented.

History:

- user-facing;
- searchable;
- timestamp/provider/model/style/source mode;
- user có thể disable.

## 7.3. Translation Memory

Sau History/Glossary có thể thêm memory exact/fuzzy:

- exact source match -> reuse approved translation;
- fuzzy match -> chỉ suggest, không silent overwrite nếu similarity chưa đủ cao.

---

# 8. V0.7.0 - Quick UX advanced (P0 chuyển lên V0.4.1)

## 8.1. Floating selection toolbar (P0 hoàn thành ở V0.4.1)

Optional:

```text
[VI] [EN] [繁中] [Explain]
```

Xuất hiện sau text selection nếu user bật.

Phải có option OFF vì toolbar tự nổi có thể gây phiền.

## 8.2. Quick actions

Possible actions:

- Translate.
- Translate + Replace.
- Explain technical sentence.
- Summarize selection.
- Copy translation.

Không auto Enter/send message.

---

# 9. V0.8.0 - Benchmark Center + Diagnostics

Mục tiêu là biến các benchmark model hiện đang làm thủ công thành workflow trong app.

## 9.1. Benchmark inputs

- One or multiple fixed texts.
- Runs per model: 3-10.
- Cache forced OFF during benchmark.
- Provider/model selection.
- Streaming ON/OFF variants.

## 9.2. Metrics

- TTFT.
- Total latency.
- Success rate.
- Timeout rate.
- HTTP errors.
- Output character count.
- Optional chars/sec.
- Optional estimated API cost nếu provider trả usage.

## 9.3. Auto recommendation

App có thể chỉ recommend dựa trên measured data, ví dụ:

```text
Terra / responses:
stream OFF recommended

Gemini Flash / gateway X:
stream ON recommended
```

Không suy luận recommendation từ tên `Flash`, `Pro`, `Max`.

## 9.4. Quality benchmark

Không nên auto-score quality bằng heuristic đơn giản.

Có thể hỗ trợ:

- user reference translation;
- side-by-side blind comparison;
- manual rating;
- optional judge model sau này.

---

# 10. V0.9.0 - Distribution + Security

## 10.1. Packaging

Target:

```text
ScreenTranslatorSetup.exe
```

User cuối không cần:

- Python
- pip
- venv
- run.bat

## 10.2. Startup

Settings:

- Start with Windows.
- Start minimized to tray.
- Start showing Main Window.

## 10.3. API key security

Current portable mode:

```text
providers.json -> plaintext API key
```

Ổn cho personal portable use nhưng không phải final consumer security.

V0.9 target:

- Windows Credential Manager / DPAPI.
- `providers.json` chỉ giữ metadata + credential reference.
- Optional Portable Plaintext mode nếu user chủ động chọn.

## 10.4. Migration

Installer/update không được phá:

- providers.json
- prompts.json
- glossary
- history
- runtime settings

Cần schema version + migration functions.

---

# 11. V1.0 - Stable Release

V1.0 không phải thêm càng nhiều feature càng tốt.

V1.0 criteria:

- Text selection translation stable.
- Replace stable.
- Region Translate stable trên DPI/multi-monitor phổ biến.
- Live Translate usable và không spam API.
- PDF reader translation stable.
- Provider management không cần sửa code.
- Prompt management không cần sửa code.
- Upgrade không mất config.
- Installer ổn định.
- Logging/diagnostics đủ để debug user issue.
- API secret storage phù hợp consumer release.

---

# 12. Architecture target dài hạn

```text
                    +----------------------+
                    |      MainWindow      |
                    +----------+-----------+
                               |
           +-------------------+-------------------+
           |                   |                   |
         Tray              Region UI            PDF UI
           |                   |                   |
           +-------------------+-------------------+
                               |
                        AppController
                               |
       +-----------------------+-------------------------+
       |                       |                         |
   InputWorker             OcrWorker             TranslationWorker
       |                       |                         |
 Clipboard/Win32      OCR Engine Abstraction        Provider API
                               |                         |
                         RapidOCR etc.            Cache / Streaming
```

Live Translate tương lai phải reuse:

- screen capture utilities;
- OCR engine;
- OcrWorker hoặc worker pool;
- TranslationWorker;
- Cache;
- Provider config;
- Prompt config.

PDF scan cũng phải reuse OCR engine thay vì tạo `PdfOcrEngine` duplicate nếu không thật sự cần.

---

# 13. File/module ownership rules

## `main.py`

Chỉ:

- QApplication bootstrap.
- config load.
- single-instance setup.
- controller creation.

Không thêm business logic.

## `app/controller.py`

Orchestration only:

- connect UI -> workers;
- maintain runtime state;
- job lifecycle;
- config reload.

Không implement OCR algorithm/provider HTTP parsing trong controller.

## `app/ocr/*`

OCR backend only.

Không gọi translation provider.

## `app/workers/ocr_worker.py`

Background OCR scheduling.

## `app/workers/translation_worker.py`

Translation queue/cache/prompt/provider only.

Không capture screen.

## `app/ui/region_selector.py`

Selection/capture interaction only.

Không OCR và không gọi API.

---

# 14. Testing strategy

## Unit tests

Phải cover:

- config parsing;
- provider parsing;
- prompt catalog;
- cache key;
- OCR record parsing;
- OCR confidence filtering;
- worker queue ordering;
- runtime reload ordering;
- streaming parsers.

## Source-architecture tests

Dùng khi build environment không có PySide runtime:

- action tồn tại;
- signal wiring tồn tại;
- main controller flow không bị xóa vô tình.

Không xem source tests là thay thế cho GUI tests.

## Windows smoke tests

Mỗi release có UI/capture feature phải test thực tế.

Checklist tối thiểu cho V0.4:

- selector placement;
- DPI crop;
- multi-monitor;
- hotkey focus;
- overlay cancel;
- first OCR initialization;
- popup behavior.

---

# 15. Performance/telemetry nội bộ cần log

Không log full sensitive text ở INFO.

Nên log metadata:

```text
job id
request mode
capture pixel size
PNG bytes
OCR engine
OCR elapsed
OCR block count
OCR char count
provider
model
streaming on/off
TTFT
translation total
cache hit/miss
error class
```

V0.4.0 hiện đã log capture dimensions/block count cơ bản; milestone kế tiếp nên thêm OCR elapsed rõ ràng.

---

# 16. Privacy rules

Default behavior mục tiêu:

- Selection translation: selected text gửi provider AI.
- Region Translate: screenshot local only; OCR text mới gửi provider.
- Live Translate: frame local only; recognized text mới gửi provider.
- PDF text: extracted text gửi provider.
- PDF scan: rendered page image local OCR; recognized text gửi provider.

Nếu tương lai có cloud multimodal OCR, phải là explicit opt-in và UI phải nói rõ ảnh sẽ được upload.

---

# 17. Known limitations hiện tại

V0.4.1 kế thừa các giới hạn Region Translate của V0.4.0 và có thêm các giới hạn Quick UX ở mục **4A.6**. Những giới hạn Region hiện còn:

1. Region selection chỉ trong một monitor/lần.
2. RapidOCR runtime chưa được smoke-test trong build container vì container không phải Windows GUI runtime.
3. First OCR call có thể chậm vì lazy initialization.
4. Chưa có OCR settings editor đầy đủ trên GUI.
5. Chưa có screenshot preview/history.
6. Chưa có Live Screen tracking.
7. Chưa có OCR timing metric riêng trong Diagnostics UI.
8. Chưa bundle OCR model thành installer vì chưa tới distribution milestone.

Không workaround bằng cách đẩy ảnh lên AI vision mặc định; giữ local OCR direction.

---

# 18. Thứ tự phát triển được khuyến nghị từ đây

Roadmap đã đổi theo quyết định ngày 2026-10-12: **ưu tiên Quick UX trước Live Translate**.

```text
V0.4.0
Region Translate MVP
    |
    v
V0.4.1 (PREVIOUS SOURCE BUILD)
Quick UX P0: automatic selection toolbar (default ON), quick popup,
Copy / UIA-checked Replace / Pin / live settings / tray
    |
    v
V0.4.1.1 (CURRENT SOURCE BUILD)
Fixed pynput mouse callback signature; added hook/UIA diagnostics.
Windows smoke tests still pending; follow-up V0.4.1.x if needed
    |
    v
V0.4.2 (OPTIONAL, USER PRIORITY)
Quick Compose + Explain / Summarize + more app-specific selection detectors
    |
    v
V0.4.5
Live Screen OCR tracker + overlay
    |
    v
V0.5.0
PDF Translator MVP
    |
    v
V0.6.0
Glossary + History + Translation Memory
    |
    v
V0.7.0
UX upgrades / workflow polish (Quick Toolbar P0 already shipped)
    |
    v
V0.8.0
Benchmark Center
    |
    v
V0.9.0
EXE + Installer + Credential Security
    |
    v
V1.0
Stable release
```

---

# 19. Next concrete development task

**Ngay sau V0.4.1.1 source build:** người dùng smoke-test trên Windows 10/11 trước khi code milestone tiếp theo.

## 19.1. Quick Toolbar / Popup smoke tests (bắt buộc)

1. Chạy `run.bat` trên Python 3.11/3.12 x64, để mặc định Quick UX ON.
2. Mở Notepad: chọn text bằng chuột drag; sau ~250ms mong đợi thanh `VI | EN | 繁 | ⋯` nếu UIA control hỗ trợ.
3. Kiểm tra Edge/Chrome, Word/VS Code; ghi rõ ứng dụng/phiên bản nào không expose UIA selection (khi đó Alt+T phải vẫn dùng được).
4. Không click toolbar => không được gọi dịch hoặc sửa clipboard.
5. Bấm VI, EN, 繁 => popup nhỏ dịch đúng ngôn ngữ, không đổi target mặc định của tray.
6. Test copy và pin; click ra ngoài khi unpinned thì popup ẩn; Esc ẩn mà không nuốt Esc của app nguồn.
7. Chọn text trong trường Password => không hiển thị toolbar.
8. Chọn text readonly browser => popup vẫn dịch; Replace không được enabled nếu không có bằng chứng field editable.
9. Chọn trong editor rồi Translate; thay đổi selection hoặc focus trước Replace => app phải hủy dán.
10. Thử Close/Esc/external click trong lúc Quick Replace đang queue => không dán kết quả cũ.
11. Test streaming ON/OFF, cache HIT, provider switching, custom prompt Engineer/Chat/Email.
12. Toggle Auto OFF trong tray, reload từ `config.json`, mở Quick UX Settings và Reset Default; phải áp dụng live.
13. Test 100/125/150% DPI + monitor phụ bên trái (tọa độ âm): toolbar/popup không ra khỏi màn hình.

## 19.2. Nếu Windows xuất hiện lỗi

Làm bản vá tiếp theo trong nhánh **V0.4.1.x** theo severity: clipboard/focus/Replace safety -> crash -> UIA not detected -> popup placement/DPI -> polish. Test trong Chrome/Edge/Notepad thật chứ không tự coi 109 unit tests là đủ.

## 19.3. Nếu Quick UX P0 ổn

Chọn bước tiếp dựa trên nhu cầu người dùng:

- **V0.4.2**: Quick Compose (dịch văn bản đang gõ, không tự Enter/send) + Explain/Summarize.
- **V0.4.5**: Live Translate trên Selected Region với image-hash gate, OCR text-block tracking, request throttling.

Dù chọn nhánh nào, giữ nguyên module `quickux/`, `ocr/`, `TranslationWorker`, `providers.json`, `prompts.json`; không gom logic về `main.py`.

---

# 20. Definition of Done cho mỗi version từ đây

Một version chỉ được gọi là hoàn tất khi:

- source compile pass;
- automated tests pass;
- README cập nhật;
- IMPLEMENTATION_HANDOFF cập nhật;
- `current_plan.md` cập nhật status/next milestone;
- config/example config đồng bộ;
- không làm mất backward compatibility không có migration;
- feature mới có error state rõ ràng;
- không claim Windows GUI verified nếu chưa test trên Windows thật.

`current_plan.md` là roadmap sống. Sau mỗi milestone lớn phải sửa trạng thái, known issues, quyết định kiến trúc và next concrete task; không chỉ append changelog.

---

# 21. Current milestone handoff — V0.4.1 (2026-10-12)

**Decision:** ưu tiên auto toolbar cho người dùng cá nhân, mặc định ON khi select text bằng chuột. Không làm Live Screen trước. V0.4.1 triển khai code theo `QuickUX_Design_Spec_V0_4_1.md` đã phê duyệt, với P0 bám sát nhu cầu hàng ngày. Không gọi bất kỳ provider nào chỉ vì mouse selection.

**Điểm quyết định next:** chạy Windows smoke test Chrome/Notepad/VS Code/Word và xác nhận UIA bắt selection được; nếu không thì chỉnh UIA traversal cho app đó ở V0.4.1.1. Sau đó cân nhắc Quick Compose và Explain/Summarize (P1) trước Live Screen. PDF cũng giữ milestone tương lai.

**Chạy kiểm tra source:** `python -m compileall -q app` và `python -m unittest discover -s tests -v`. Lần build này 109/109 automated tests pass (không phải Windows GUI test).

**Sửa an toàn sau review:** tombstone các Quick Translation job đã hủy để callback muộn không chạy lại legacy Replace; callback popup Close / click ngoài / Esc hủy in-flight Quick Replace; InputWorker đối chiếu foreground window và selected text trước paste, không tự activate cửa sổ nguồn cho Quick UX; nếu UIA không cung cấp `ValuePattern`, cấm Replace mặc định.
