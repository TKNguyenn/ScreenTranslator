# ScreenTranslator release workflow

Agreed with the user on 2026-10-17.

Development and testing workspace:
`C:\Users\kietj\Documents\FINEPRO\Image Processing\ScreenTranslator_V0_4_1_1_QuickUX_MouseHookFix\ScreenTranslator_V0_4_1_1_QuickUX_MouseHookFix`

Publishing checkout:
`C:\Users\kietj\Documents\GitHub\ScreenTranslator`

Remote: `https://github.com/TKNguyenn/ScreenTranslator.git`

After the user accepts the changes, the instruction **push repo** means:

1. Check the publishing checkout's branch, remote, local changes and upstream changes. Preserve edits made there; do not blindly overwrite a dirty checkout or force-push.
2. Synchronize the approved source, assets, tests, example/default configuration and documentation from the development workspace. Preserve the publishing checkout's `.git`, license and repository-specific files. Reconcile intentional source deletions explicitly; do not mirror-delete the whole destination.
3. Exclude personal `config.json`, `providers.json`, `prompts.json`, local `trial.json` / `Trial.json`, `.env`, `data/`, caches, virtual environments and generated `build/`, `dist/`, `release/`, `artifacts/`, `.build-tools/`. Keep `.env.example`, other clean examples and `app/defaults/`. Inspect the staged diff for accidental secrets and unrelated files.
4. Confirm the release version and installer match the accepted code; build and verify if needed. Commit and push the approved source to the normal upstream branch.
5. Create a stable GitHub release tagged `v<APP_VERSION>` at that source commit, titled `AI Screen Translator <APP_VERSION>`. Use the release notes format below and upload only `AI-Screen-Translator-<APP_VERSION>-Setup.exe` as a release asset, not a Git-tracked file. Do not upload standalone `Uninstall.exe` or `SHA256.txt`; uninstall is included in Setup and the updater uses GitHub's asset digest. Never replace an existing published tag/release silently.
6. Verify the remote commit, published tag, installer asset and GitHub SHA256 digest, then report the release URL.

Coding alone does not trigger publication. The user's **push repo** instruction after acceptance authorizes synchronization, commit/push and release publication without another routine confirmation.

## Release presentation

User preference confirmed 2026-10-17. Keep the short English introduction from the reference release and add the actual changes since the preceding release. Use user-facing descriptions of added features, improvements and fixes; omit empty categories and internal task/test logs. Never publish the placeholder below unchanged or list planned work as shipped.

Title: `AI Screen Translator <APP_VERSION>`

Release body:

```markdown
Windows Desktop Release

- Standalone Windows installer
- AI translation and Google Translate
- Quick Toolbar and Region OCR
- Provider and Prompt Manager

### What's new

- <Describe each feature, improvement or fix shipped in this update.>
```

Upload only the matching Setup executable. GitHub automatically adds **Source code (zip)** and **Source code (tar.gz)**; these are not extra manual uploads. Local build output may still include uninstall/checksum files for verification, but they are not published separately.
