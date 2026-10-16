# AI Screen Translator — Windows release

Run AI-Screen-Translator-0.4.1.8-Setup.exe to install for the current Windows user.
Python and administrator access are not required. Windows 10/11 x64 only.
Launch AI Screen Translator from Desktop or Start Menu.
Setup shows the default destination and lets you choose another folder with Browse.
On the final page, tick or untick "Create a desktop shortcut", then click Finish.
Start Menu shortcuts are always created.
Minimize keeps the app in the tray. Exit from the tray before updating or uninstalling.

The release includes a clean configuration with Google Translate Free selected.
It does not include the developer's API keys, providers, custom prompts or history.
Use Provider & Model to add your own provider or import your own providers.json.
Cloud providers require internet and may charge for usage; Google Free is unofficial.
OCR models are bundled and run locally.

INSTALL LOCATION
%LOCALAPPDATA%\Programs\AIScreenTranslator
This is the default; Setup can install to a different writable folder.
Installation paths longer than 180 characters are rejected to avoid Qt plugin loading failures.

SETTINGS AND DATA
The chosen installation folder above, alongside ScreenTranslator.exe.
Contains config.json, providers.json, prompts.json and data\ (cache, runtime settings, logs).
JSON defaults are created on first launch; .env can also live beside config.json.
Existing settings are retained on reinstall/update. The Python source project uses its own files.
When no local config/catalog exists, Setup copies legacy config/catalog/.env/data from
%LOCALAPPDATA%\AIScreenTranslator without overwriting destination files.
Legacy originals remain as a safety copy until uninstall; the updated app uses only the install folder.
Retained catalogs prevent importing stale legacy settings on reinstall.

UNINSTALL OPTIONS
Exit the app from the tray. Open Uninstall.exe in the install folder,
or use Settings > Apps > AI Screen Translator > Uninstall.
Uninstall.exe beside the downloaded Setup also finds a custom install location.
Install this updated Setup first to use the combined app/data layout.
The standard uninstaller unins000.exe is also available in the install folder.
Choose one of two options:
1. Uninstall app; keep only providers.json and prompts.json (default).
   Both files remain unchanged in the settings/data folder above for reuse on reinstall.
   This retains API keys saved in providers.json. All other app settings/cache/logs are removed.
2. Remove everything: also delete providers.json and prompts.json. Remove the install folder if empty.
Both options remove installed files, app-owned data (including legacy data), shortcuts and uninstall registration.
Unrelated files you placed in the install folder are preserved; the folder remains if it contains any.
The two choices are exclusive. Cancel closes the dialog without uninstalling.
If preserving either file fails, uninstall stops before deleting the app.
If restoring the preserved files fails, a recovery folder is retained and its path is shown/logged.
It does not erase exported files, downloads, the source project or external paths
you explicitly configured with APP_CONFIG_PATH/PROVIDER_CATALOG_PATH/PROMPT_CATALOG_PATH/data_dir.
Windows-managed history/security caches are controlled by Windows.

TROUBLESHOOTING
Run ScreenTranslator.exe --self-check to generate self-check.json in the settings folder.
This checks bundled Qt/assets, Google provider setup, Windows UI Automation and real local OCR.
It does not send text to an API, read the clipboard or install input hooks.

BUILD FROM SOURCE
Install requirements.txt and PyInstaller 6.22.3; install Inno Setup 7 (or >= 6.6).
Run powershell -ExecutionPolicy Bypass -File packaging/build.ps1
Optionally pass -Iscc with the full path to ISCC.exe.
Output: release/AI-Screen-Translator-0.4.1.8-Setup.exe, release/Uninstall.exe and release/SHA256.txt.
The small launcher uses the Windows .NET Framework C# compiler; no additional Python bundle is needed.
For unattended uninstall, the native uninstaller accepts /DATA=keep (default) or /DATA=all.
PyInstaller stages the app in dist/ScreenTranslator; keep its _internal folder with the exe.
