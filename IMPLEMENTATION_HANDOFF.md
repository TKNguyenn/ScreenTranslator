# Built 0.4.1.12 — 2026-10-21 (local only)

User requested packaging the accepted loading wave. Updated app/version.py, installer default and Windows release instructions to 0.4.1.12; retained user's animation and existing unsigned build pipeline. 218 source tests, compile, native Windows Quick UX smoke and 17 native popup tests pass. Final frozen EXE passes 9 offline checks; all 58 product modules match source, including WaveTranslationOutput. Setup metadata 0.4.1.12; release/AI-Screen-Translator-0.4.1.12-Setup.exe 111958270 bytes SHA256 95f6b8a7537936ac335c0eae55f2e606f6910fa9b2880d91aaf6a28f13732ae9. EXE 7917584 bytes SHA256 bd109e3c9b5110183965170269c11ceff833c9a967653e8891ed7d2565eaa6b6; keep _internal beside it. Evidence artifacts/build-0.4.1.12-20261021-114924/result.json and logs. No install/uninstall, live provider call, repo sync/push or release. Public baseline remains v0.4.1.11; source-only/no-build statements below are historical.

# Loading wave — 2026-10-21 (source only)

User approved the animated preview and requested integration into the Quick Translation popup. `app/ui/quick_popup.py` now paints the loading text as a left-to-right wave (5 logical pixels, 1650 ms cycle, 85 ms character stagger, cyan at the crest). A Qt timer repaints only while loading and visible; streaming, final/cache results, errors and hide/close stop it. The text remains in the document for accessibility. Existing controller/provider interfaces are unchanged; no dependency added.

Validation: 218 unittest tests pass (including three new animation/lifecycle tests), app compileall passes, native Windows UI smoke passes. Inspected actual Qt render at `artifacts/loading-wave-popup.png`; test log: `artifacts/loading-wave-tests.log`. The synthetic mouse callback exception in that log is an intentional existing test. No live provider request or installer/EXE rebuild performed; packaged 0.4.1.11 still predates this change.

---

# Release 0.4.1.11 ? 2026-10-20

Microsoft Translator now supports API key/Region configuration and local monthly usage accounting in SQLite. Cached translations do not add usage. This release uses local usage only; no cloud usage sign-in is included. The selection toolbar now shows only language actions, and the popup uses a borderless ?? with 50% opacity unpinned and 100% pinned.

Validation: 215 source tests pass, final frozen EXE passes 9 offline checks, and 58 product modules match the accepted source. Setup SHA256: e8955af08a532aacf6f1a4b088d13257378ce2f11b068f6c653d9154d98f7e28 (111973776 bytes). Version 0.4.1.11. Installer execution and live provider calls were not repeated for this release. Earlier handoff entries below are historical.

---

# Daily startup update check (2026-10-17, V0.4.1.10)

User accepted the provider-save fix; 0.4.1.10 additionally checks GitHub once per Vietnam calendar day when the app starts, including first use. TrialUsageStore.claim_update_check atomically records last_update_check_date in data/trial_usage.json under its shared worker lock. This marker is independent of checks/date/spent, so opening Trial, quota resets and translations preserve the update schedule. Controller.start schedules _check_updates_on_startup after showing the window; _check_for_updates is shared with manual clicks and only requests release metadata, never downloads. An offline attempt counts for the day; manual retry remains available. Local disk errors log and skip the automatic request without preventing startup. No timer checks for updates while the app remains open overnight; the requested trigger is app startup. Version stays 0.4.1.10. Validation: 196 unit/widget tests and compileall pass. Rebuilt Setup passes all 8 packaged offline checks; archive inspection confirms startup callback and claim_update_check are bundled, with personal root configs excluded. Evidence: artifacts/daily-update-tests.log, daily-update-build.log and daily-update-self-check.json. Setup is 111926728 bytes; SHA256 7ad8c1bc04448cec192d2fe0f2e02bfd95e1858be811f14242e71137a207104f (supersedes the earlier local 0.4.1.10 artifact). Full install/uninstall and live GitHub checks were not repeated; installed app was left running. No source sync/push/release requested for this follow-up.

---

# Provider save hotfix (2026-10-17)

Source is now 0.4.1.10. Published 0.4.1.9 is commit 581c933b5e16c72dfbaa4781039be15d1ca6c936; older build/publish-pending statements below are historical. A regular custom provider using https://api.vilao.ai/v1 was inferred as Trial solely by URL. Saving an unsupported custom model then failed while parsing all profiles, before either config/catalog write, so saving from any selected profile could fail. is_trial_profile now checks explicit ai_trial type only; _build_provider_section assigns that type to the reserved Trial catalog name. Catalog import/store and factory already reserve the name. Custom gateway model lists remain intact; renamed Trials retain ai_trial in config overrides. A portable export without the Trial name or type is an ordinary provider on reimport.

Validation: 191 unit/widget tests pass plus compileall. New regression tests cover custom models on the shared gateway, catalog save/reload and factory identity, and real UI-to-controller Save & Apply from Custom/Google/Trial with temporary files. No personal config/catalog changed or live gateway request sent. Local release/AI-Screen-Translator-0.4.1.10-Setup.exe built successfully. Packaged offline self-check passes all 8 app checks plus frozen Trial identity regression; evidence: artifacts/provider-save-hotfix-self-check.json. Full install/uninstall smoke was not repeated: packaging changed only the version, and the user's installed app is running with the global app mutex. Prior 0.4.1.9 installer smoke passed. No hotfix push/release publication yet; the running installed EXE is still 0.4.1.9 until the user closes it and installs 0.4.1.10.

---

# AI Trial source handoff (2026-10-17)

Hotkey settings follow-up: MainWindow now has a **Cài đặt** sidebar page with seven editable shortcuts (selection, replace, Live toggle, Region Translate, VI/EN/繁 target selection), release delay and suppress toggle. `parse_hotkey_section` normalizes portable Qt sequences to the `keyboard` format, rejects empty/duplicate shortcuts and bounds the delay. Controller persists the validated section atomically and reloads/re-registers `HotkeyService`; reset restores `HotkeySection` defaults. New settings icon is `app/assets/icons/tab_settings.svg`. Full validation: 189 tests, compileall and native offline self-check pass. No live external hotkey acceptance or installer rebuild/publish performed.

Endpoint follow-up: Trial now shows the existing auto/responses/chat_completions/completions selector. app/trial.py validates and preserves endpoint_mode; new profiles default to auto, existing saved modes stay unchanged. Gateway URL, default paths and model allowlist stay fixed. On each app/store startup, `TrialUsageStore` records the current Vietnam date/time, compares the latest check, resets spent after a new day and retains only the two latest checks. The visible timer still detects a day change within one minute. New tests verify endpoint routing/auto fallback charged once, save/reload, startup history/reset and timer-driven visible refill. Latest validation: 188 tests (13 Trial tests), compileall and seven native offline self-checks pass. Updated renders inspected: artifacts/trial-ui/trial-endpoint-1280.png and trial-endpoint-900.png. No live gateway call, build or publication.

User approved implementation after confirming the gateway has no quota API. Fresh app/defaults/providers.json and providers.example.json now contain only Google Translate Free + Trial, both with empty keys; config.example.json defaults to Google Free. Existing catalog files remain intact; the manager's + Trial action adds the built-in profile to the working copy and persists only on Save & Apply. Personal trial.json is ignored/excluded from publishing and never bundled; public URL/model values were copied into clean defaults and app/trial.py only.

app/trial.py owns ai_trial identity, the fixed https://api.vilao.ai/v1 endpoint, allowed gateway model IDs gemini-3.8-flash/gpt-6-luna/gpt-6-sol, 100 VND/day estimate and fixed illustrative costs Luna=1/Flash=3/Sol=4 VND per successful request. Display labels include friendly names and prices; QComboBox user data keeps raw IDs for saving/API payloads. Only key, selected model, endpoint mode and per-mode streaming overrides survive Trial normalization. Config/catalog/factory pin connection settings and reject unsupported active models. Canonical gateway URL infers Trial after portable export/import/rename; explicit ai_trial type remains in config overrides. Factory revalidates direct dataclass profiles and gives a missing-key setup error. Server restrictions remain necessary; client settings are not authorization.

User correction on 2026-10-17 supersedes the initial one-switch UI: Trial exposes the original three streaming combos, independently inherit/on/off for ultra_fast/fast/quality. Advanced connection rows and model editing stay hidden. Ordinary/custom/Google forms retain their behavior. app/providers/trial_provider.py extends the existing OpenAI-compatible transport and records a local estimate only after normal/streaming success, once per call rather than per delta. Worker/cache/popup remain shared. Provider tests count as one request; cache hits bypass the provider and failures do not count. A usage-write error is logged without losing the translation. Automated transport tests use MockTransport, no personal key.

User explicitly requested a locally estimated bar despite no gateway quota API. It starts full, deducts the fixed model-specific cost from a 100 VND/day estimate, has no numeric quota labels, and displays: Hạn mức ước lượng, không chính xác. Chi phí thực tế tùy độ dài văn bản. app/services/trial_usage.py reuses RuntimeSettingsStore atomic writes in data/trial_usage.json with a shared lock across provider/test instances, hashes each key, persists across restart and resets by Vietnam calendar day (UTC+7). No raw key in this file. MainWindow refreshes on key/form changes, translation/test results and a local timer while visible. This is one machine's estimate, not actual gateway usage; other devices/outside requests, real token cost and failed/partial streams can differ. Zero does not block translation. Gateway key/model limits and daily reset remain authoritative; no admin/upstream credential is shipped.

Validation: 189 unit/widget tests pass including tests/test_trial.py (13 checks) and the hotkey/settings UI coverage. Covers independent per-mode overrides, raw IDs behind priced labels, fixed settings/imports, missing key, bootstrap/catalog retention, per-key/day estimate persistence, two-check startup reset, 20 concurrent records across store instances, success/cache/429 handling, stream charged once, duplicate hotkey validation and retaining translation after a disk-write failure. Final renders: artifacts/trial-ui/trial-endpoint-1280.png, trial-endpoint-900.png and artifacts/settings-hotkeys-900.png. Final compileall passes. Native offline source self-check passes all eight checks, including the settings page, revised Trial form, Qt HTTPS backend, Quick UX, UIA/input imports without hooks and real synthetic RapidOCR inference (artifacts/settings-source-self-check.json). No paid/live gateway translation performed.

No installer rebuilt, no personal config/catalog changed, no sync/push/release performed. Source APP_VERSION is still 0.4.1.9. Existing release/Setup predates Trial; never publish it as this source's installer without rebuilding and verifying, and choose a new release version if the tag is already published. README, current_plan.md, design/plan docs and release exclusion checklist are updated. Next: user acceptance with a personal Trial key, then normal push/release workflow only when requested. Earlier handoff below is historical.

---

# V0.4.1.9 GitHub updater handoff (2026-10-16)

Release presentation preference (2026-10-17): title `AI Screen Translator <APP_VERSION>`; short English `Windows Desktop Release` feature list as in the user's reference, followed by `What's new` describing actual shipped changes since the previous release. Upload only the matching Setup.exe; standalone Uninstall.exe/SHA256.txt remain local build outputs. GitHub adds source archives automatically. This supersedes earlier multi-asset upload instructions. See docs/Release_Workflow.md for the template. No publication requested by this preference update.

Publishing workflow agreed 2026-10-17: keep development/testing here in FINEPRO. After user acceptance, **push repo** means sync approved source to `C:\Users\kietj\Documents\GitHub\ScreenTranslator`, commit/push and publish a matching stable release with installer assets. Target remote verified as TKNguyenn/ScreenTranslator; working tree clean at inspection. Preserve `.git`, repo-only changes/license and personal data; do not copy the whole development tree. See docs/Release_Workflow.md. No sync/push/release was requested or performed while recording this workflow.

app/services/updates.py owns stable release parsing, numeric version comparison, QNetworkAccessManager checks/streaming download and installed helper launch. Hardcoded public repository TKNguyenn/ScreenTranslator. Accept exact stable tag/name/URL and GitHub sha256 digest, bounded size; no auth/provider config. MainWindow's footer has action/status/progress only. AppController connects checks/download/install handoff and closes UpdateManager on shutdown. No startup network request. Source mode checks but cannot install.

packaging/Update.cs is compiled by build.ps1 and installed as Update.exe. A separate copy runs from app/data/updates/update-*/ so Setup can replace the installed helper. Wait for app PID exit before reading/locking/rechecking downloaded SHA256 and invoking /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /UPDATE=1 /DIR=<current app> /LOG=<download dir>/update.log. Restart exe only on exit code 0, then delete installer. Failed install retains download/log and shows an error. Partial files are deleted on cancel/error; tiny successful helper/log cache is removed with app/data during uninstall. /UPDATE=1 skips creation of a new desktop shortcut without removing existing shortcuts.

Unit/widget tests: tests/test_updates.py and test_update_ui.py. Native/real GitHub verification: tests/windows_update_smoke.py --live uses harmless compiled fixture executables for PID waiting, quoted paths, setup flags, relaunch and config retention; downloads/verifies the actual GitHub asset but never executes that real public installer. Existing windows_release_smoke.py covers real Setup/install/reinstall/uninstall. Offline packaged self-check also asserts Qt HTTPS backend and new footer. Real future-version app-to-app update acceptance remains pending until a later release exists. GitHub currently serves v0.4.1.8; first install of 0.4.1.9 must be manual. No .git in this workspace, no push/publish performed.

Earlier handoff follows.

0.4.1.9 validation: 175 unit/widget tests pass; compile and compact sidebar render pass. artifacts/update-smoke.json: 6 checks including live Qt HTTPS public installer verification and harmless native helper handoff; artifacts/release-install-uninstall.json: 17 checks including real frozen TLS/Qt/UIA/OCR and real install/uninstall, sandbox ast-release-smoke-3kqovytn. Targeted update-mode real Setup install/reinstall/removal passed (artifacts/update-installer-smoke.json). Setup is 111927729 bytes; release/SHA256.txt verified. Sandbox installed app/data/registry/shortcuts removed; test sources/logs/sentinels remain. No user installation or GitHub repository modified. Last script additions assert helper inclusion and no desktop link in the final /UPDATE=1 cycle; equivalent targeted checks were run against the compiled installer without repeating compression.

# V0.4.1.8 colocated layout handoff (2026-10-16)

Current frozen root is Path(sys.executable).resolve().parent. Source mode is unchanged. All default JSONs and .env are beside the exe, relative data/ beside them. Installer LegacyDataDir is only an import/cleanup location. [Files] external onlyifdoesntexist copies known old data when no config/catalog exists in the destination; originals remain until uninstall for recovery. No personal data is bundled at build time.

Uninstall removes known runtime files, app-owned data/, tracked installed payload, legacy app data, shortcuts and registry. Never recursively remove {app}: it may contain unrelated user files. Keep mode backs up only catalogs to LegacyDataDir.keep-<unique temp name> outside either removal tree, then restores to {app}. Full mode deletes catalogs too and removes empty app root. Older append-only logs may still delete the legacy root; recovery handles that. Reinstall with retained catalogs skips legacy import entirely. Smoke fixture includes an actual older uninstall log and checks both deletion modes plus unrelated-file survival.

Earlier implementation history follows; the split data paths below were superseded by 0.4.1.8.

Validation: 165 tests/compile pass; artifacts/release-self-check.json reports version 0.4.1.8 and ok=true. artifacts/release-install-uninstall.json has 16 successful checks, sandbox Temp/ast-release-smoke-97gbt0zs. App and legacy sandbox data removed; test fixture sources/logs/sentinels remain. release/AI-Screen-Translator-0.4.1.8-Setup.exe (111907159 bytes), release/Uninstall.exe and SHA256.txt verified. No installation into the user's actual app location. Unsigned; clean second-PC and interactive acceptance pending.

# V0.4.1.7 uninstall handoff (2026-10-16)

Uninstall.exe is a small C#/.NET Framework launcher (packaging/Uninstall.cs); registry resolves custom install location and minimum installed version 0.4.1.7 prevents calling an older destructive uninstaller. It exits immediately after launching native unins000.exe so its installed copy can be deleted. Build compiles it with Windows csc before bundling; installer replaces legacy Uninstall.bat.

Native Inno InitializeUninstall offers two exclusive radio options: keep exactly providers.json/prompts.json (default), or remove everything. Silent /DATA=keep|all has the same semantics; invalid values abort. Before file removal (usUninstall, after the app mutex check), keep mode copies the two files to a unique persistent sibling recovery directory. The ordinary logged data-tree deletion then runs, including deletion entries inherited from older installers. usPostUninstall restores the two files and deletes recovery. Backup failure aborts before removal. Restore failure keeps recovery and reports the location. Original files are never modified during backup; no key contents are logged. Source/exports/explicit external data paths remain out of scope.

Validation: 165 tests pass and compile passes. Native Windows release smoke passes real frozen self-check/OCR and custom-location install/reinstall. Default keep through the standalone launcher leaves exactly two byte-identical catalog files and no recovery folder; reinstall preserves them. Full removal through the installed launcher removes itself and all installed files/data/shortcuts/registration. Exclusive file lock on providers.json causes a fatal pre-removal abort; releasing it allows subsequent successful uninstall. Invalid /DATA also aborts without removal. Mutex and unrelated junction target checks pass. Interactive radio selection/clean second-PC remain unchecked; release is unsigned. Reports: artifacts/release-install-uninstall.json and release-self-check.json.

## Earlier release history

# V0.4.1.6 Windows release handoff (2026-10-16)

Installer follow-up: destination page always visible/editable with Browse; desktop shortcut checkbox is on FinishedPage and creates the link on ssDone only when checked. [UninstallDelete] removes the custom-created link. Standalone helper resolves HKCU x64 InstallLocation for custom folders. Installer rejects paths over 180 characters before installation because deeply nested sandbox installs caused Qt platform plugin initialization to abort. Custom-path smoke now uses a short Temp sandbox and asserts registry-based helper removal.

Follow-up validation: sandbox install/self-check/reinstall/helper-uninstall passes for a custom path with spaces; long-path guard verified at 212 characters (exit 7 before file installation). Native destination/Browse UI observed. Interactive finish-checkbox acceptance was interrupted by the user's physical Escape (Computer Use stopped); no further UI automation performed. The launched test installer and its failed-run sandbox installation were cleaned up through exact process/path and the standard uninstaller.

User requested standalone exe and an uninstall file that removes everything owned by the app. `packaging/ScreenTranslator.spec` creates a windowless onedir exe, collecting app assets/defaults, local RapidOCR models, ONNX Runtime, UIA data/COM wrappers, Windows input backends and runtime license metadata. `packaging/installer.iss` wraps this in a per-user Windows 10/11 x64 Inno Setup installer with Desktop/Start Menu shortcuts and Windows Apps registration. Build via `packaging/build.ps1` (PyInstaller 6.22.3 + Inno Setup 7.1.0 used locally). Unsigned release; no publication or user installation performed.

`application_root()` in config.py uses LocalAppData/AIScreenTranslator for frozen apps, project root for Python. Frozen first run seeds only missing files from app/defaults (Google Free, no secrets) after the single-instance guard. Source config/catalog/data remains untouched. `.env` loads beside the selected config. SingleInstanceGuard also holds a pointer-safe native mutex in frozen Windows; Inno refuses install/uninstall while it exists. `--self-check` writes a local JSON report, testing real Qt/theme/widgets/Google forms, COM/UIA and synthetic local OCR without API calls or input hooks.

App files install in LocalAppData/Programs/AIScreenTranslator. Standard `unins000.exe` plus Uninstall.bat remove tracked app files/shortcuts/registry and the fixed per-user LocalAppData/AIScreenTranslator tree. Uninstall.bat is also supplied beside Setup and forwards to the installed uninstaller. Confirmation states saved keys/prompts/cache/logs are deleted; source project/exported files/explicit external data paths stay untouched. No recursive deletion of arbitrary install or config paths is implemented in custom scripts.

Validation: 164 unit/widget/source tests and compile pass. `tests/windows_release_smoke.py` compiles an installer with isolated app/data/shortcut/AppId values, installs, runs the actual frozen self-check from an unrelated cwd, reinstalls preserving modified config and uninstalls; verifies app/data/shortcut/registry removal and unrelated-file survival. Reports: artifacts/release-self-check.json and release-install-uninstall.json. Frozen OCR recognizes HELLO WORLD 123 using bundled models. Clean second-PC/signing/real-provider acceptance remains pending. Release folder contains Setup, Uninstall.bat and SHA256.txt; docs/Windows_Release.md includes use/build instructions.

---

# V0.4.1.5 Google providers handoff (2026-10-15)

UI follow-up: removed the redundant catalog subtitle/banner, moved both Google preset buttons into the Import/Export row, and hide the entire Models and Streaming override groups for both Google types (restore for AI). Values remain available to the existing save flow. Compact-layout widget tests load actual Segoe UI fonts under Windows offscreen Qt, matching native Qt instead of the empty offscreen font database. Native Google smoke also checks group visibility/restoration.

Integrated the user-supplied standalone addon as `app/providers/google_translate_addon.py`, subclassing TranslationProvider and rejecting empty translation responses. Source addon remains untouched. Canonical HTTPS Google host inference is used in profile parsing/factory; explicit non-Google types and existing provider routes remain. URL validation forbids custom hosts/paths/userinfo/ports to protect key/text. Web splits Unicode GET text by encoded size with a bounded chunk count; errors omit raw body, URL, key and selected text. Web suppresses httpx/httpcore request logging to WARNING process-wide. Cloud key is X-goog-api-key; no redirects or fallback to paid Cloud.

TranslationWorker consumes optional `cache_scope` and optional streaming override hooks, retaining old LLM prompt hashes. Google is non-streaming and cache entries can be reused across speed/style/prompt, still isolated by source/target/provider/model/text. Controller effective streaming mirrors this. Provider tests now send a real English-to-Vietnamese translation rather than an LLM OK instruction.

MainWindow preset buttons add/select working profiles without applying them or overwriting existing names. Save/rename/delete/import/export use the existing portable catalog and app-only overrides. Type selection sets canonical Google URL/model; endpoint, alternative-model, streaming and Free-key controls are disabled. Active Google disables Prompt Editor sections and tray style/speed actions but does not erase their values. Empty-key Cloud is allowed as inactive catalog entry, rejected by construction when applied/tested.

Validation: 160 tests PASS (18 new adapter/integration/widget/controller tests), compile PASS, `tests/windows_google_ui_smoke.py` PASS, existing Windows Quick UX smoke PASS. Synthetic preview files are in `artifacts/google-v0415/`. No real Google call/key/billing acceptance check. No changes to the user's live providers.json/config.json or dependencies. Runtime version is 0.4.1.5. User guide: `docs/Google_Providers_V0_4_1_5.md`.

---

# V0.4.1.4 Dark Ocean Aurora Bento handoff (2026-10-14)

Approved identity: concept 1 Glyph Slash logo + concept 1 Aurora Bento UI from the user's `G:/My Drive/VibeCode/demo_UI/demo_UI_ver2`. Assets are copied into `app/assets` and have no runtime dependency on G:. `app/ui/theme.py` applies Fusion, a dark palette and `ocean_theme.qss` once during bootstrap; it also provides icon lookup and native dark title bars. `aurora.py` paints the main ocean backdrop and decorative hero using Qt.

`main_window.py` keeps the six existing pages/signals, adds branded icon navigation and cards connected to runtime state, and wraps each page in a vertical scroll area. Capture honors the feature flag; overview shortcuts reflect config. Provider footer and prompt action grids fit compact windows. All titles wrap instead of forcing a larger page. Tray, legacy popup and region selection follow the theme. `FloatingSurface` still paints an opaque ocean gradient directly, now with a cyan-to-emerald rim. Do not replace this with only translucent QWidget QSS: that caused the missing-background bug. Quick Popup dragging/resizing, result geometry, pinning, no-activate and source panes are retained.

Validation: 142 unittest tests PASS, compileall PASS, native Windows Qt smoke PASS with `apply_theme` enabled. New widget tests cover navigation/assets, actual runtime state, region feature flag, masked provider key/save signals, Quick settings and compact layout. `python tests/ocean_ui_preview.py` creates synthetic previews for all six real pages (1180×800 and 900×620) and both popup variants without API/clipboard/hooks. Offscreen Qt on Windows requires explicitly loading system fonts in the preview script. `python tests/windows_quickux_ui_smoke.py` checks native opaque backgrounds, topmost/no-activate, drag and final geometry. External-app/provider and broader DPI checks remain user acceptance work. See `docs/Ocean_UI_Design_V0_4_1_4.md`.

---

# V0.4.1.3 Quick UX UI handoff (2026-10-12)

User confirmed selection toolbar is now visible. New request: fix missing backgrounds and redesign toolbar/popup; allow moving and resizing the popup after clicking a language.

`app/ui/floating_surface.py` paints the solid navy card explicitly with QPainter while keeping rounded transparent outer corners. The former custom QWidget only relied on stylesheet background painting, which did not reliably paint the translucent toolbar. The shared surface also handles mouse-based edge resize and draggable header labels without activating the source window.

`quick_toolbar.py` adds a badge, separated language controls, consistent menu styling and suspends auto-dismiss while its menu is open. `quick_popup.py` adds readable header, metadata, primary Copy action, Pin, drag hints, expandable vertical splitter and bottom-right QSizeGrip. It has minimum 360x280 and initial 460x360, without fixed/max body sizing. `finish`/`fail` no longer call `_show_near`, so streaming/final/error events preserve user geometry and never reopen a dismissed popup. Popup size persists across requests for the lifetime of the instance; position is reset near the new selection only on start.

Validation: 135 tests PASS, compile PASS. `python tests/windows_quickux_ui_smoke.py` verifies actual Windows Qt opaque background, topmost/no-activate styles, header drag and retained geometry using offscreen-positioned windows with synthetic text. `python tests/quickux_ui_preview.py` renders the real widgets to `artifacts/quickux-v0413-preview.png` without provider or clipboard access. Widget tests cover alpha painting, drag, edge/grip resize, minimum dimensions, final/error geometry, pin/source toggles and late results. Broader source-app/DPI acceptance remains pending.

---

# V0.4.1.2 UIA compatibility handoff (2026-10-12)

User reports no toolbar in any app, running global Python 3.11 on Windows 11. Latest log confirms the pynput hook starts and recognizes gestures; UIA probing returns no snapshot. Root cause of the reported cross-app failure is not yet confirmed: the former reader hid provider exceptions and assumed typed GetTextPattern helpers plus only five ancestors.

Changes: generic GetPattern access; 12 ancestor levels and bounded source-window subtree search (64 nodes, six levels), password/process/foreground guards; content-free UIA status propagated to Diagnostics; pointer-sized Win32 bindings. Added nine regression tests and `python tests/windows_quickux_smoke.py` (offscreen synthetic RichEdit, no focus/clipboard/API changes). Also explicitly close SQLite connections and specify UTF-8 in old source tests to fix Windows test failures.

Verified on this Windows environment: 124/124 unittest tests PASS; compile PASS; actual native RichEdit selected text read through UIA PASS. This does not certify mouse selection in all third-party apps. Restart the app completely, check v0.4.1.2, test Notepad then Edge/Chrome. Unsupported TextPattern providers still use manual Alt+T; no passive clipboard fallback was introduced.

---

# V0.4.1.1 quick bugfix handoff (2026-10-12)

Symptom: Mouse highlight produces no floating toolbar. Confirmed source-level bug: `MouseSelectionMonitor._on_click` had a four-parameter signature while pynput >=1.8 can invoke it with five parameters including `injected`. Listener exceptions can terminate global listener in background without visible UI warnings.

Fix: fifth `injected=False` callback parameter with backward compatibility; ignore injected clicks; catch/log unexpected callback exceptions rather than kill hook; start/gesture INFO logs; `MouseSelectionMonitor.is_running()`; Diagnostics shows hook health and last UIA detection stage. Added `tests/test_v0411_mouse_hook.py`; added `docs/QuickUX_Windows_Troubleshooting.md`. No API, prompt, cache, provider or clipboard change.

Windows acceptance: Exit old app completely, launch new folder, verify v0.4.1.1 tray label; select in Notepad; check UIA toolbar; translate. If missing, use Diagnostics and `data/logs/app.log`; UIA non-support still requires hotkey. Headless tests don't validate Windows UIA.

---

# IMPLEMENTATION HANDOFF - AI SCREEN TRANSLATOR V0.4.1

## 1. Current milestone

Current release: **V0.4.1 Quick UX (Floating Selection Toolbar P0)**.

This version continues **V0.4.0 Region Translate** and adds **Quick UX P0** with an auto-show toolbar enabled by default. The existing screen/OCR pipeline is preserved:

```text
Region selector -> local screenshot -> OcrWorker -> RapidOCR -> TranslationWorker -> popup
```

Do not collapse this project back into one script. V0.4.0 intentionally separates screen selection, OCR inference and translation because the same pieces will be reused by Live Translate and scanned-PDF translation.

---

## 2. Existing architecture that must remain intact

### Main/UI thread

Owns:

- `AppController`
- `MainWindow`
- `TrayIcon`
- `TranslationPopup`
- `RegionSelectorOverlay`

No network inference or OCR inference may run here.

### Hotkey thread

`HotkeyService` owns global keyboard registration.

### InputWorker

Owns selected-text clipboard capture and replace/paste operations.

### OcrWorker - new in V0.4.0

Owns local OCR jobs and OCR engine replacement on runtime reload.

### TranslationWorker

Owns:

- prompt resolution;
- cache lookup/write;
- provider requests;
- streaming.

Region Translate must feed OCR text into the existing TranslationWorker, not create a second translation stack.

---

## 3. V0.4.0 new modules

### `app/ui/region_selector.py`

Responsibilities only:

- identify monitor under cursor;
- capture that monitor before overlay is shown;
- show translucent drag overlay;
- accept left-drag selection;
- cancel on Escape/right-click;
- map logical Qt coordinates to screenshot pixel coordinates;
- encode selected crop to PNG bytes;
- emit `RegionCaptureResult`.

It must not run OCR or call providers.

### `app/ocr/base.py`

OCR engine interface.

### `app/ocr/rapidocr_engine.py`

Default local OCR backend using `rapidocr_onnxruntime`.

Important behavior:

- import is lazy;
- model initialization is lazy;
- confidence filter is applied locally;
- backend output is normalized to `OcrBlock` objects and a newline-joined text string.

### `app/ocr/mock_engine.py`

Deterministic backend used by tests/development.

### `app/ocr/factory.py`

Creates OCR backend from `OcrSection`.

### `app/workers/ocr_worker.py`

Queue-based worker with:

- `OcrTask`
- `OcrReloadTask`
- ordered engine replacement
- result callback returning `OcrResult`

---

## 4. New models

`RequestMode` now includes:

```text
REGION
```

New dataclasses:

- `RegionCaptureResult`
- `OcrBlock`
- `OcrResult`

Region requests use `foreground_hwnd=None` and cannot use Replace-in-source.

---

## 5. Region Translate runtime flow

### Start sources

Region Translate can start from:

- global hotkey `Alt+S`;
- Tray action;
- Main Window Screen Translate page.

Controller method:

```text
_begin_region_job()
```

### UI capture phase

```text
_begin_region_job
 -> optionally hide Main Window
 -> QTimer delay
 -> RegionSelectorOverlay.begin(job_id)
 -> screenshot current cursor monitor
 -> user drag
 -> RegionCaptureResult
```

The small delay is configurable so the manager window has time to disappear before screen capture.

### OCR phase

```text
_on_region_captured
 -> popup: OCR processing
 -> OcrWorker.submit(PNG)
 -> RapidOCR local
 -> OcrResult
```

### Translation phase

```text
_on_ocr
 -> popup: OCR source text + translating status
 -> TranslationRequest(mode=REGION)
 -> TranslationWorker
 -> cache/provider/streaming
 -> TranslationPopup
```

The provider receives text only.

---

## 6. Multi-monitor and DPI decision

V0.4.0 supports any attached monitor but selection is constrained to one monitor per job.

Monitor selection:

```python
QGuiApplication.screenAt(QCursor.pos())
```

DPI mapping:

```text
scale_x = screenshot_pixel_width / screen_logical_width
scale_y = screenshot_pixel_height / screen_logical_height
```

Selection logical rect is multiplied by these scale factors before `QPixmap.copy`.

Do not remove this conversion and assume 1:1 coordinates.

Future cross-monitor selection must explicitly handle different DPI per monitor, not concatenate rectangles blindly.

---

## 7. OCR configuration

New config section:

```json
"ocr": {
  "engine": "rapidocr",
  "min_confidence": 0.45
}
```

Supported engines in V0.4.0:

- `rapidocr`
- `mock` (testing)

Unknown engine names fail config validation.

`min_confidence` must be within `[0.0, 1.0]`.

Runtime Reload builds a new OCR engine and queues replacement behind any OCR job already in flight.

---

## 8. UI configuration additions

`UiSection` adds:

- `region_capture_delay_ms`
- `region_min_size_px`
- `region_overlay_opacity`

These are app behavior values and therefore belong in `config.json`, not `providers.json` or `prompts.json`.

---

## 9. Feature flags

V0.4.0 defaults:

```json
"features": {
  "live_screen_enabled": false,
  "region_translate_enabled": true
}
```

Tray and Main Window reflect Region enabled/disabled state after reload.

Live Translate remains disabled until V0.4.5.

---

## 10. Popup behavior

`TranslationPopup` now supports:

- `show_ocr_processing(...)`
- `allow_replace` flag

Region results must use:

```text
allow_replace=False
```

Selected-text POPUP mode retains Replace capability.

---

## 11. Portable configuration rules from V0.3.x remain frozen

### `providers.json`

Portable source of truth only for:

- provider name
- base URL
- API key
- model list

Do not add OCR fields here.

### `prompts.json`

Only user prompt overrides.

### `config.json`

App behavior including OCR/region settings.

---

## 12. Prompt architecture remains unchanged

Prompt override grid remains exactly:

```text
3 performance modes x 3 styles = 9 independent slots
```

Supported placeholders:

- `{source_language}`
- `{target_language}`
- `{style}`
- `{engineering_terms}`
- `{glossary}`

`{glossary}` is still reserved for the planned V0.6 glossary system.

Region OCR text uses the same effective prompt as selected text for the active speed/style.

---

## 13. Cache behavior

Region OCR text is a normal TranslationRequest source string, so translation cache works without a separate region cache.

Effective prompt hash remains part of cache identity.

Changing prompt/model/provider/style/target can therefore invalidate/re-scope cache correctly.

Do not cache raw screenshots in the translation cache.

---

## 14. Dependencies

V0.4.0 adds:

```text
rapidocr_onnxruntime>=1.4,<2
```

It is imported lazily from the OCR backend.

Recommended Windows source runtime remains Python 3.11/3.12 x64.

---

## 15. Tests added in V0.4.0

New tests cover:

- OCR config defaults/validation;
- RapidOCR record parsing/order/confidence filtering;
- OcrWorker execution;
- ordered OCR engine reload;
- Region selector DPI/source decisions via source assertions;
- Controller capture -> OCR -> Translation wiring;
- tray/main Region UI exposure;
- OCR dependency declaration.

Existing V0.3.x test suite remains active.

The build environment can run compile/unit/source tests but cannot certify actual Windows overlay/DPI behavior. Do not claim Windows GUI validation until run on Windows.

---

## 16. Required Windows smoke tests before Live Translate

Test:

1. `Alt+S` on primary monitor.
2. `Alt+S` on secondary monitor.
3. Escape cancel.
4. Right-click cancel.
5. Small-selection retry.
6. Chinese Traditional OCR.
7. English OCR.
8. 100% DPI.
9. 125% DPI.
10. 150% DPI.
11. mixed-DPI monitors if available.
12. app started from Main Window button.
13. app started from Tray.
14. app started from hotkey while Main Window hidden.
15. config reload changing OCR threshold.

If any crop/DPI bug exists, fix it in V0.4.1 before V0.4.5.

---

## 17. Next milestone

See `current_plan.md` sections 18–19 for the updated roadmap.

Recommended next sequence:

```text
V0.4.1 Quick UX P0 source build (current)
 -> Windows smoke test (UIA, no-activate popup, safe Replace, DPI)
 -> V0.4.1.1 bugfix only if necessary
 -> V0.4.2 Quick Compose / Explain OR V0.4.5 Live Translate
```

Live Translate must reuse the V0.4 capture/OCR abstractions and add change detection/block tracking rather than repeatedly translating every frame.

---

## 18. V0.4.1 Quick UX addendum (P0)

**User decision:** auto-show is ON by default on mouse-highlight, unlike the first UX draft. All data transfer remains opt-in: mouse selection alone never initiates provider calls.

### New modules

- `app/quickux/selection.py`: immutable candidate/snapshot/check models + pure `MouseGestureRecognizer` (drag/double-click).
- `app/quickux/mouse_monitor.py`: daemon `pynput.mouse.Listener` for global LEFT press/release. Filters own windows via Win32 hit-testing, sends Python data only through `WorkerBridge.quick_mouse` to Qt GUI. No direct Qt calls from hook.
- `app/quickux/uia_reader.py`: uses `uiautomation.GetFocusedControl/ControlFromPoint`, `TextPattern.GetSelection`, max length cap. Password guard; no clipboard.
- `app/quickux/selection_worker.py`: dedicated COM-initialized thread; ordered async probe and verify results. Mouse candidates are debounced via Qt timer and generation counter; UIA timeout/fail is safe (bar does not show).
- `app/ui/quick_toolbar.py`: noactivate dark pill VI/EN/繁/⋯; position clamped to current screen availableGeometry.
- `app/ui/quick_popup.py`: noactivate ~414px card; status, coalesced streaming delta, Copy, Replace, Pin, toggle original, Close.

### New settings (not portable provider/prompt files)

`QuickUxSection` in `app/config.py` is part of `AppConfig`. `config.json.quick_ux` default:

```json
{
  "auto_show_toolbar": true,
  "selection_delay_ms": 250,
  "languages": ["vi", "en", "zh-Hant"],
  "dismiss_popup_on_blur": true,
  "toolbar_timeout_ms": 8000,
  "max_selection_chars": 6000
}
```

MainWindow Quick UX Settings saves atomically through ConfigFileStore. Tray checkbox persists the same setting. `Reload config` reinitializes settings without reopening the app. `providers.json` and `prompts.json` are unchanged.

### Controller integration

`PendingJob(quick=True)` routes separate quick jobs, while Region/Alt+T still use `TranslationPopup`. Quick jobs call the existing `TranslationWorker`; the one-shot target button does not mutate global target. Old stream/final events are filtered by `job_id`; UIA snapshots by serial. `QuickPopup` aggregates SSE deltas at 55ms cadence.

Before Quick Replace, **two checks** are intentionally applied:

1. `QuickSelectionWorker.verify()` checks original HWND, exact UIA text, control signature and read-only state.
2. `InputWorker._paste()` re-captures clipboard-copyable selected text on explicit Replace and compares it against the original snapshot. Any mismatch cancels paste. This is not an atomic guarantee against all cross-process races, but substantially reduces the risk of replacing the wrong text.

Escape is observed through an additional non-suppressing keyboard handler in `HotkeyService`; `Alt+T`, `Alt+Shift+T`, `Alt+S` remain unchanged. Main Window still opens first, minimizes to tray, and closes on X.

### Dependency and deployment

`requirements.txt` adds `pynput>=1.7.7,<2` and Windows-only `uiautomation>=2.0,<3`. On Windows, run `run.bat`; it installs dependencies into `.venv` automatically. New dependencies are used **only** for passive toolbar detection. If COM/UIA does not support an app, no clipboard fallback is attempted automatically; hotkeys are supported as before.

### Test, risk and follow-up

- Completed source-level checks: **109/109 tests PASS** and full compileall PASS. This is **not** equivalent to Windows GUI/hook validation.
- Late canceled Quick UX translation results are tombstoned so they never re-enter the legacy replacement handler.
- Closing popup, Escape, or external mouse click cancels queued Quick Replace. InputWorker checks the expected HWND and selected text without forcibly foregrounding the former app; the paste service checks a cancellation event before Ctrl+V.
- UIA text selections lacking explicit writable ValuePattern are allowed for translation but must not allow Replace.

- `python -m unittest discover -s tests -v` and `python -m compileall -q app` must pass.
- Python unit coverage includes QuickUxSection validation, drag/double-click classification, UIA selection simulation, password guard, read-only reject, no selection, worker callbacks and source architecture assertions.
- **Windows GUI validation has not been performed in this Linux container** (PySide6 runtime and Windows UIA unavailable here). Test Chrome/Edge, Notepad, VS Code, Word under Win10/11 x64 and 100/125/150% DPI, including negative-coordinate monitors. Pay particular attention to noactivate toolbar/menu click and Replace focus.
- P1: Explain/Summarize and Quick Compose remain **not implemented**, even if visible in earlier UX prototype.
- Future Windows-specific refinements: selection via keyboard, app exclusions, more tolerant UIA traversal, clipboard preservation of non-text formats, improved source-app replace transactions.

See `current_plan.md` section 4A for detailed acceptance matrix and next plan.
