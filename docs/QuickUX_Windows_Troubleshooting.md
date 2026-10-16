# Quick UX V0.4.1.3 - Windows troubleshooting

## V0.4.1.3 UI update

Exit the tray app completely and restart `python main.py`; confirm **v0.4.1.3**. Backgrounds are now explicitly painted solid navy. Drag the popup title/metadata to move it, or its edges/bottom-right grip to resize. Translation completion preserves the geometry you chose. Use Ghim to keep it open after clicking elsewhere.

`python tests/windows_quickux_ui_smoke.py` checks native Windows Qt opacity/topmost/no-activate and dragging without changing clipboard, focus or contacting the provider. `python tests/quickux_ui_preview.py` renders an interface preview from actual widgets.

## V0.4.1.2 UIA detection update

Exit the running tray app completely and restart `python main.py` from this folder. Confirm tray version **v0.4.1.2**. Existing V0.4.1.1 upgrade instructions below describe the earlier release.

The new reader uses generic UIA patterns and a bounded search within the source window. If selection still fails, Diagnostics -> `Quick UX last probe` reports:

- `TextPatterns=0`: no selected-text pattern found in the controls examined. Alt+T remains the manual fallback.
- `TextPatterns` greater than zero, `errors=none`: patterns were present but their selections were empty.
- `errors=COMError` or another exception type: UIA access failed; log details include exception type/HRESULT, never source text.
- `source window ... foreground/changed`: the source lost focus before/during probing.
- `password control excluded` / `character limit`: intentionally excluded.

Verification commands: `python -m unittest discover -s tests -q` and `python tests/windows_quickux_smoke.py`. The second command creates an offscreen synthetic native RichEdit and reads its selection without changing focus or clipboard. It verifies native UIA access, not third-party mouse/toolbar behavior.

## What should appear?

1. Select text **with a mouse drag or double-click** in another application (e.g. Notepad).
2. Wait the configured delay (default 250 ms).
3. Floating toolbar `VI | EN | 繁 | ...` appears near the selection.
4. Click `VI` to request translation and open the smaller translation popup.

Selecting text alone does **not** call the translation API or show the translated result.

## Fix in V0.4.1.1

- The previous callback in `app/quickux/mouse_monitor.py` accepted **four** positional arguments.
- `pynput` releases with mouse injected-event information can call it with **five** positional arguments.
- That TypeError stopped the background pynput mouse listener, leaving auto-toolbar inactive. V0.4.1.1 accepts both signatures and catches listener callback errors.
- Log entries identify selection gesture detection vs Windows UI Automation (UIA) selection availability. The app never logs selected text.

## Upgrade without accidentally running the old version

The app uses a **single-instance lock**. Launching a second copy while the old app is running opens the OLD window and exits the NEW process. Therefore:

1. Right-click the old app's tray icon and choose **Thoát ứng dụng**.
2. Extract `ScreenTranslator_V0_4_1_1_QuickUX_MouseHookFix.zip` into a separate folder.
3. Copy personal settings from the old folder as needed: `providers.json`, `prompts.json`, `config.json`; do not publish these files if they contain API keys. If using centralized `PROVIDER_CATALOG_PATH` / `PROMPT_CATALOG_PATH`, no copy is needed for those catalogs.
4. Launch `run.bat` in the **new** folder.
5. Right-click the tray icon and confirm the version label is **v0.4.1.1**.
6. Confirm **Tự hiện Quick Toolbar khi bôi đen** is checked.

## Troubleshoot in Notepad first

Paste `設備設定 - Interlock - Test selection` into Notepad, then drag-select the text using the mouse. Test simple local text before Chrome or specialized industrial apps.

Right-click tray -> **Chẩn đoán / cấu hình** (Diagnostics). Find:

- `Quick UX mouse hook running: True` -- the global pynput hook is alive.
- `Quick UX last probe: Chua nhan selection gesture ...` -- mouse selection gesture has not been observed; try drag-selecting from left to right, or double-click a word. Selecting with Shift+arrows alone does not trigger the mouse monitor.
- `Quick UX last probe: Mouse gesture detected; reading UI Automation` -- waiting for UIA.
- `Quick UX last probe: UIA could not read selected text ...` -- mouse hook works; the target application didn't expose the current selected text through UIA `TextPattern`. Try Notepad; use Alt+T hotkey as fallback in apps without UIA support.
- `Quick UX last probe: UIA read selection successfully ...` -- detection worked; if the toolbar is invisible, investigate Windows topmost windows, DPI and monitor positioning.
- `Quick UX mouse hook running: False` -- the hook is not active; see `data/logs/app.log`, confirm requirements installed in the `.venv`, and test that other system-level mouse hooks can run.

`data/logs/app.log` includes: `Quick UX global mouse hook started`, `Quick UX mouse selection gesture recognized`, and either `Quick UX toolbar shown` (DEBUG level) or `Quick UX UI Automation did not expose selected text`.

## Known limitations

- No automatic toolbar for keyboard-only selection, text selected inside this translator's own GUI, secured/password fields, or third-party applications that do not expose UIA `TextPattern` selection.
- Windows admin/elevated applications and some Chromium/Electron processes may not expose accessibility text selection to an ordinary process. Some Chromium/Electron UIA accessibility support depends on application settings or launch flags.
- The code intentionally does **not** send automatic Ctrl+C after every mouse selection, since that would modify the user's clipboard and could read sensitive content.
- `Alt+T` and `Alt+Shift+T` still work through the existing manual clipboard workflow.
- Automated tests do not prove cross-application behavior: real Windows smoke tests are required.
