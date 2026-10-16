# Dark Ocean Aurora Bento — V0.4.1.4

Approved on 2026-10-14: reuse logo concept 1 (Glyph Slash) and UI concept 1 (Aurora Bento) from `demo_UI_ver2`, adapted to the existing Screen Translator workflows.

## Visual system

| Element | Treatment |
| --- | --- |
| App background | Dark Ocean `#080E1A` with subtle native-painted cyan/emerald glow |
| Primary action | Cyan `#38BDF8` → Emerald `#10B981` gradient, dark text |
| Cards and fields | Rounded dark layers, visible thin borders and focus states |
| Navigation | Concept 1 icon family, cyan active edge and green/cyan selected fill |
| Typography | Segoe UI, near-white text, muted blue metadata |
| Floating cards | Opaque ocean fill with cyan/emerald rim and transparent rounded outer corners |

Glass appearance uses painted color layers. The floating toolbar and popup content intentionally stays opaque so source-app text cannot reduce readability. No desktop blur/compositor dependency is added. The Aurora illustration is painted in Qt rather than importing the reference screenshot as a functional interface.

## Layout and behavior

- Keep the six existing destinations: Overview, Provider & Model, Prompt Editor, Region Translate, Quick UX and future PDF.
- Sidebar width is 220; minimum manager size is 900×620. Form pages scroll vertically; titles wrap and action rows fit the available area.
- Overview shows the actual provider/model, style/speed, language/cache and configured shortcuts. Capture uses the current region workflow and feature flag.
- Quick Toolbar retains VI/EN/繁, menu actions and timeout handling. The popup retains Copy/Replace, original-text splitter, Pin/close, header drag, edge resize and bottom-right grip. Result/error events preserve geometry; dimensions persist for the process session.
- Legacy selection/region popup and tray/menu/dialog controls use the shared palette/theme. PDF remains marked as a future feature.

## Assets and implementation

`app/assets/app_icon.ico`, `logo.png` and `logo.svg` originate from logo concept 1. The SVG icon family under `app/assets/icons` comes from the user's demo; check and chevron assets are added for controls. All assets are local to the application. `app/ui/theme.py` loads `ocean_theme.qss`, `aurora.py` paints decorative surfaces, and `floating_surface.py` explicitly paints the floating-card backgrounds.

## Validation

```powershell
python -m unittest discover -s tests -q
python -m compileall -q app main.py tests
python tests/windows_quickux_ui_smoke.py
python tests/ocean_ui_preview.py
```

142 tests passed, compilation passed, and native Windows Qt smoke passed with the shared theme active (opaque background, topmost/no-activate, header drag and retained result geometry). Preview output: `artifacts/ocean-v0414/`, including all pages at 1180×800 and 900×620, Quick surfaces and the legacy popup. The preview explicitly loads Windows system fonts because the offscreen plugin otherwise has no system font database. Only synthetic config/text is rendered; no provider request, clipboard operation or mouse hook is started.

Remaining acceptance: run the real app with the user's provider, select text in source applications, translate and exercise Copy/Replace/Pin/resize, then check multiple monitors/DPI. Native smoke does not certify every external application or real provider.
