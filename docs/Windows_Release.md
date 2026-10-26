# AI Screen Translator — Windows release

Run AI-Screen-Translator-0.5.0-Setup.exe to install for the current Windows user.
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

CHECK FOR UPDATES
Click Check for updates at the bottom of the sidebar. It contacts only the public
TKNguyenn/ScreenTranslator latest stable release API; no provider keys or translated text are sent.
If current, it shows Latest version: v...; newer development builds are never downgraded.
If newer, click Update to v... to download with progress, verify GitHub's SHA256/size,
exit the app, install silently in the same folder, then restart. Settings/catalogs/data survive.
Network, missing-asset or integrity errors allow retry without starting an installer.
Closing the app while downloading cancels and removes the partial download.
Automatic installation requires the installed Windows version; Python runs update source through Git.
Version 0.4.1.8 needs a newer Setup once to acquire the updater. The app checks once per Vietnam calendar day on startup; downloads/installations require an explicit Update click.
Downloads/helper logs live in the install folder's data/updates and are removed on uninstall.
After a successful update the large downloaded installer is deleted; small helper/log files remain.

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
It also checks Microsoft Translator setup and local usage display without network requests.
It does not send text to an API, read the clipboard or install input hooks.

BUILD FROM SOURCE
Install requirements.txt and PyInstaller 6.22.3; install Inno Setup 7 (or >= 6.6).
Run powershell -ExecutionPolicy Bypass -File packaging/build.ps1
Optionally pass -Iscc with the full path to ISCC.exe.
Output: release/AI-Screen-Translator-0.5.0-Setup.exe, release/Uninstall.exe and release/SHA256.txt.
The small uninstall/update helpers use the Windows .NET Framework C# compiler; no additional Python bundle is needed.
For unattended uninstall, the native uninstaller accepts /DATA=keep (default) or /DATA=all.
PyInstaller stages the app in dist/ScreenTranslator; keep its _internal folder with the exe.
Pygments is excluded: it is an optional HTTPX CLI dependency unused by the app or usage guide.
Build from a shell without unrelated DLL tool directories on PATH; PyInstaller can collect their DLLs.
Require the EXE to survive antivirus observation, pass --self-check, and retain its SHA256 before distributing Setup.

PUBLISH AN UPDATE
Increase app/version.py, run the build and tests, then create a stable GitHub release in
TKNguyenn/ScreenTranslator tagged v<version>. Attach AI-Screen-Translator-<version>-Setup.exe
and wait for upload to finish. The tag and asset filename must match; the API must expose
the asset's sha256 digest. Upload only the Setup executable; Uninstall.exe is included in Setup
and SHA256.txt remains a local verification output. Use the title and release-notes template in
docs/Release_Workflow.md, including actual changes for each update. GitHub adds source archives
automatically. Draft/prerelease/source-only releases are not install candidates.
Do not commit release/build/dist/data or personal config/catalog/.env files into Git.
No publishing is performed by the local build. Test with python tests/windows_update_smoke.py --live
to verify native handoff and the current public download without installing the public release.
