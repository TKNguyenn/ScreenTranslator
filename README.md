# AI Screen Translator V0.4.1.8 - Windows App

## V0.4.1.8 — App và dữ liệu chung một thư mục (2026-10-16)

Chạy [Setup 0.4.1.8](release/AI-Screen-Translator-0.4.1.8-Setup.exe) để cài hoặc cập nhật. Không cần Python hay quyền admin. Setup hiển thị đường dẫn mặc định, cho đổi bằng **Browse**; trang cuối có ô **Create a desktop shortcut**.

Tất cả dữ liệu đang sử dụng nằm trong thư mục cài đã chọn, mặc định `%LOCALAPPDATA%\Programs\AIScreenTranslator`:

```text
AIScreenTranslator/
  ScreenTranslator.exe
  Uninstall.exe
  config.json
  providers.json
  prompts.json
  data/                 # cache, runtime settings, logs
  _internal/            # runtime và model OCR
```

Các file JSON được tạo khi chạy app lần đầu. Cache/log nằm trong `data`; `.env` nếu dùng cũng đặt cạnh file cấu hình. Chạy exe từ shortcut hay thư mục khác vẫn dùng đúng dữ liệu này. Project Python tiếp tục dùng dữ liệu trong project.

Khi cập nhật từ bản lưu dữ liệu riêng ở `%LOCALAPPDATA%\AIScreenTranslator`, Setup chép config, provider, prompt, `.env` và `data` sang nếu thư mục mới chưa có cấu hình/catalog. Không ghi đè file hiện có. Bản cũ được giữ làm bản sao an toàn đến khi gỡ app; app mới chỉ đọc/ghi ở thư mục cài. Cài lại sau chế độ giữ catalog sẽ không nhập lại settings cũ.

## Gỡ cài đặt

Thoát app từ tray, mở [Uninstall.exe](release/Uninstall.exe), file cùng tên trong thư mục cài hoặc Windows Settings → Apps. Hai lựa chọn loại trừ nhau:

- **Giữ provider/prompt** (mặc định): gỡ app, shortcut, settings/cache/log; giữ nguyên `providers.json` và `prompts.json` ngay trong thư mục cài để dùng lại. API key trong provider cũng được giữ.
- **Xóa hết**: xóa cả hai file trên và dữ liệu app, dọn bản dữ liệu cũ nếu có. Thư mục cài được xóa khi trống.

Không xóa file riêng do bạn tự đặt trong thư mục cài, project source, file export hay các đường dẫn ngoài app bạn chủ động cấu hình. Nếu không sao lưu được catalog, chế độ giữ dừng trước khi xóa app. Nếu khôi phục lỗi, giữ thư mục recovery và thông báo đường dẫn.

Bản phát hành có Google Free mặc định, không đóng gói API key/cấu hình/lịch sử cá nhân trong project. Bộ cài chỉ nhận đường dẫn tối đa 180 ký tự để tránh lỗi Qt. Hướng dẫn build và kiểm thử: [Windows Release](docs/Windows_Release.md).

## V0.4.1.5 — Google Translate Free + Google Cloud (2026-10-15)

Thêm Google vào worker/cache hiện có, dùng được cho dịch bôi đen, toolbar, dịch và thay thế, và phần text sau Region OCR. Không thêm thư viện; dùng `httpx` đang có.

1. Thoát hẳn app cũ và chạy `python main.py`, kiểm tra **v0.4.1.5**.
2. Mở **Provider & Model** → **+ Google Free** hoặc **+ Google Cloud**. Nút chỉ thêm/chọn profile để chỉnh; không đổi provider đang áp dụng.
3. **Free:** không cần key, model `google-translate`. **Cloud:** nhập API key hoặc tên biến môi trường chứa key, model `nmt`; cần bật Cloud Translation API và billing trong Google Cloud.
4. Chọn Google trong **Provider đang áp dụng** rồi **Lưu & áp dụng**. Có thể bấm **Test provider / model hiện tại** để gửi `Hello` từ English sang tiếng Việt. Test Cloud có thể phát sinh phí.

Google dịch trực tiếp, không dùng prompt/style Engineer/Chat/Email/tốc độ AI hay streaming. Các điều khiển không áp dụng được khóa hoặc đánh dấu; thiết lập AI đã lưu được giữ lại khi đổi provider. Cache Google được dùng lại giữa các style/speed/prompt, vẫn phân biệt nội dung, ngôn ngữ nguồn/đích, provider và model.

**Giới hạn:** Free dùng endpoint Web không chính thức, có thể bị chặn/giới hạn/ngừng hoạt động; văn bản được gửi đến Google qua URL GET. Cloud là dịch vụ chính thức có tính phí; allowance miễn phí không phải giới hạn chi tiêu. App không tự chuyển Free sang Cloud hoặc gọi API khi chỉ bôi đen.

`providers.json` vẫn đúng 3 trường `base_url`, `api_key`, `models`; URL chuẩn Google được tự nhận diện khi import/reload. Key Cloud gửi qua header, không qua URL. Profile cũ và provider đang dùng không bị tự thay đổi. Thêm preset không ghi file cho tới khi Lưu & áp dụng. Hướng dẫn cấu hình: [Google Providers](docs/Google_Providers_V0_4_1_5.md).

Đã kiểm tra **160 test PASS**, compile PASS, native Windows Google UI smoke PASS và Quick UX UI smoke PASS. Test mạng dùng `httpx.MockTransport`, không gọi Google thật hoặc dùng key của bạn.

## V0.4.1.4 — Giao diện toàn app (2026-10-14)

Áp dụng **logo mẫu 1 (Glyph Slash)** và **giao diện mẫu 1 (Aurora Bento)** từ bộ `demo_UI_ver2`, điều chỉnh theo chức năng và layout hiện có. Theme Dark Ocean `#080E1A`, điểm nhấn Cyan `#38BDF8` chuyển sắc Emerald `#10B981` thống nhất trên Main Window, sáu trang điều hướng, tray/menu, hộp thoại, toolbar, popup dịch và vùng chọn OCR.

- Tổng quan có Aurora hero, các thẻ hiển thị provider/model, chế độ dịch và ngôn ngữ/cache thực tế; nút chọn vùng gọi workflow OCR hiện có. Phím tắt lấy từ config.
- Provider, Prompt Editor và Quick UX bố trí lại để dùng được ở cửa sổ 900×620; nội dung dài cuộn dọc.
- Toolbar/popup có nền Dark Ocean **vẽ đặc**, viền chuyển sắc và nút dễ đọc. Hiệu ứng kính được thể hiện bằng lớp màu và ánh sáng, không làm nền xuyên qua nội dung app nguồn.
- Popup từ toolbar vẫn kéo bằng tiêu đề/thông tin model, đổi kích thước bằng cạnh/góc dưới phải, giữ geometry khi streaming/dịch xong/lỗi và giữ kích thước trong phiên chạy.
- Tài nguyên nằm trong `app/assets/`; chạy app không cần truy cập thư mục demo trên G:.

Thoát hẳn phiên cũ rồi chạy `python main.py`; phiên bản mới là **v0.4.1.4**. Xem ảnh widget thật: [Tổng quan](artifacts/ocean-v0414/overview.png), [Toolbar và popup](artifacts/ocean-v0414/quick-surfaces.png), [Provider](artifacts/ocean-v0414/providers.png), [Quick UX cửa sổ nhỏ](artifacts/ocean-v0414/compact-4.png).

Đã kiểm tra **142 test PASS**, compile PASS và native Windows Qt smoke PASS khi bật theme mới: nền đặc, topmost, không lấy focus, kéo popup và giữ geometry. Đây là kiểm tra UI với dữ liệu giả lập; chuỗi chọn chữ trong app bên ngoài → dịch qua provider thật và nhiều màn hình/DPI cần kiểm tra thực tế. Chi tiết: [Ocean UI Design](docs/Ocean_UI_Design_V0_4_1_4.md).

## V0.4.1.3 — Toolbar / popup redesign

Toolbar và Quick Popup dùng nền xanh đậm **vẽ trực tiếp, không xuyên nội dung app nguồn**, viền rõ và nút có tương phản cao. Popup hiển thị phía trên app nguồn mà không lấy focus.

- Bấm VI / EN / 繁 trên toolbar để mở popup dịch.
- **Di chuyển:** kéo tiêu đề `Bản dịch` hoặc phần thông tin provider/model.
- **Đổi kích thước:** kéo các cạnh hoặc tay nắm ở góc dưới phải. Kích thước được giữ giữa các lần dịch trong cùng phiên chạy.
- Khi streaming / dịch xong / có lỗi, popup giữ nguyên vị trí và kích thước đã chỉnh.
- **Xem gốc:** mở phần văn bản gốc; kéo thanh phân cách để đổi tỷ lệ hai phần.
- **Ghim:** giữ popup khi click ra ngoài. Esc / nút × vẫn đóng được.

Thoát hẳn app từ tray rồi chạy lại `python main.py`; kiểm tra phiên bản **v0.4.1.3**. Đã kiểm tra 135 test, compile và native Windows Qt smoke (nền đặc, topmost, không lấy focus, kéo popup, giữ geometry). Ảnh giao diện render từ widget thật: [`artifacts/quickux-v0413-preview.png`](artifacts/quickux-v0413-preview.png).

## V0.4.1.2 — UIA selection detection hotfix

- Read TextPattern/ValuePattern through generic UIA `GetPattern`, including Custom/Pane controls without typed helper methods.
- Search up to 12 ancestors and a bounded 64-node/6-level subtree of the source window when focus/hit-testing lands on a container.
- Diagnostics reports controls examined, TextPatterns found and exception types without storing selected text.
- Declare pointer-sized Win32 HWND signatures; explicitly close SQLite connections so Windows releases database files.
- Verified locally: 124 unit/source tests PASS, compile PASS, synthetic native Windows RichEdit selection smoke PASS. Cross-application mouse/toolbar tests in Notepad, Edge/Chrome and VS Code still require validation.

When running directly with `python main.py`, exit the previous tray instance completely before restarting. Confirm tray version **v0.4.1.2**. If the toolbar is still absent, `Chẩn đoán / cấu hình` -> `Quick UX last probe` and `data/logs/app.log` now distinguish unsupported patterns, empty selection, foreground changes and provider errors. Passive probing still never sends Ctrl+C or calls the API.

V0.4.1 phát triển trực tiếp từ V0.4.0. Milestone này đưa Quick UX lên trước Live Screen: **bôi đen text bằng chuột -> floating toolbar -> chọn VI/EN/繁 -> popup dịch**, vẫn giữ Region OCR, selection hotkeys, Provider Manager, Prompt Studio, cache và streaming override.

**Thiết kế đã chốt:** tự hiện floating toolbar **mặc định ON**. Có thể tắt ở Main Window hoặc tray. *Không có API call nào chỉ vì highlight text.*

## V0.4.1.1 - Fix auto-toolbar khong hien

V0.4.1 had an important Windows compatibility bug: its global mouse listener callback accepted four `pynput` arguments, while newer releases supply a fifth `injected` argument. A `TypeError` could silently stop the listener, so selecting text never displayed the toolbar. The callback now supports both forms and traps hook-thread exceptions. **No changes to translation prompts or provider settings.**

V0.4.1.1 Diagnostics additionally displays `Quick UX mouse hook running` and `Quick UX last probe`. On Windows, check the tray version label is **v0.4.1.1** after quitting the previous instance (the app has a single-instance guard). Full instructions: [`docs/QuickUX_Windows_Troubleshooting.md`](docs/QuickUX_Windows_Troubleshooting.md).

**Correct behavior:** mouse-select -> toolbar `VI | EN | 繁`; click a language to open the translation popup. Pure keyboard selection alone is not observed automatically. UIA may still be unavailable in some apps; manual `Alt+T` still works.

## Quick UX — mới ở V0.4.1

Khi m kéo bôi đen chữ (hoặc double-click chọn từ) trong một app Windows hỗ trợ UI Automation TextPattern:

1. Đợi mặc định **250 ms** (chỉnh được 150–600ms), thanh **`VI | EN | 繁 | ⋯`** hiện gần vùng chọn.
2. Bấm **VI / EN / 繁** để dịch 1 lần bằng provider/model, style, speed, custom prompt và streaming hiện tại.
3. Popup nhỏ có **Sao chép, Thay thế, Văn bản gốc, Ghim và Đóng**; hỗ trợ streaming token khi được bật trong provider.
4. `⋯` có **Dịch và thay thế** (theo target toàn app), **Cài đặt Quick UX**, **Ẩn toolbar**.
5. Bấm Escape/click ngoài ẩn popup theo setting; Pin giữ popup trước click ngoài.

**An toàn:** auto-detection sử dụng `pynput` mouse hook + Windows UI Automation `TextPattern.GetSelection`, không `Ctrl+C` hay gọi API khi chỉ bôi đen. Chỉ lệnh Replace rõ ràng mới kiểm tra vùng chọn lại và dùng clipboard để paste. Trong UIA password fields, không đọc selection. Nếu ứng dụng không cung cấp text selection qua UIA, toolbar không xuất hiện; dùng hotkey **Alt+T** như trước.

### Quick UX Settings

Vào **Main Window -> Quick UX**:

- `Tự hiện toolbar khi bôi đen`: **ON** mặc định.
- `Đợi sau khi chọn`: **250ms**.
- `Nút`: VI, EN, 繁 (có thể bật/tắt từng nút, ít nhất một).
- `Tự ẩn toolbar`: mặc định **8 giây**.
- `Đóng popup khi click ngoài`: **ON**; Pin giữ popup.
- `Giới hạn text`: mặc định 6000 ký tự; chọn quá dài sẽ không tự hiện toolbar.
- **Lưu & áp dụng / Khôi phục mặc định** lưu ngay trong `config.json`, không restart.

Tray có thêm checkbox **Tự hiện Quick Toolbar khi bôi đen**, cùng shortcut vào **Cài đặt Quick UX...**. Reload config cũng cập nhật Quick UX.

### Test nhanh trên Windows

- Thu nhỏ Main Window xuống tray; mở Edge/Chrome/Notepad, kéo bôi đen text, đợi ~250ms.
- Nếu thấy toolbar, bấm VI; xác nhận popup dùng đúng model và chữ được dịch.
- Copy và Pin; thử click ngoài, Escape. Muốn Replace hãy dùng trong ô có thể chỉnh sửa; app xác minh control/selection/window, không tự refocus cửa sổ nguồn và có thể từ chối khi không xác minh được. Kết quả Quick UX đã hủy không được chuyển qua đường Replace cũ.
- Bỏ tick `Tự hiện Quick Toolbar...` trong tray; các hotkey cũ vẫn phải hoạt động.
- Test ở màn hình khác DPI/monitor trái nếu có.

**Chưa có trong P0:** Explain, Summarize và Quick Compose (để V0.4.2). Không đảm bảo UIA auto-selection trong tất cả app Windows; không có tự động Ctrl+C fallback vì ảnh hưởng clipboard. Native Qt/UIA smoke đã pass trên Windows hiện tại; ma trận ứng dụng và DPI rộng hơn vẫn cần kiểm tra.

## Tính năng chính

### Selection translation

- `Alt+T`: dịch text đang bôi đen -> popup.
- `Alt+Shift+T`: dịch và replace text đang bôi đen.
- Không tự Enter/send.

### Region Translate - mới trong V0.4.0

Có ba cách bắt đầu:

- Hotkey `Alt+S`.
- Right-click tray -> **Dịch vùng màn hình**.
- Main Window -> **Dịch vùng màn hình** -> **Chọn vùng và dịch**.

Workflow:

```text
Chọn vùng
 -> capture PNG local
 -> RapidOCR local
 -> OCR text
 -> TranslationWorker
 -> provider/model đang chọn
 -> popup
```

Ảnh chụp **không được gửi tới translation provider**. Provider chỉ nhận text do OCR local nhận dạng.

Selector:

- Left-drag để chọn vùng.
- `Esc` hoặc right-click để hủy.
- Vùng quá nhỏ sẽ bị reject.
- Selector mở trên monitor đang chứa con trỏ chuột.
- Hỗ trợ nhiều monitor, nhưng V0.4.0 giới hạn một selection trong một monitor.

### OCR

Default:

```json
"ocr": {
  "engine": "rapidocr",
  "min_confidence": 0.45
}
```

OCR chạy trong thread riêng (`OcrWorker`). RapidOCR được khởi tạo lazy nên lần Region Translate đầu tiên có thể chậm hơn các lần sau.

### Prompt Studio

Prompt override độc lập cho 9 tổ hợp:

```text
Ultra Fast x Engineer/Chat/Email
Fast       x Engineer/Chat/Email
Quality    x Engineer/Chat/Email
```

Prompt custom được lưu trong `prompts.json`; default prompt gốc không bị ghi đè và có thể reset bất kỳ lúc nào.

### Provider Manager

`providers.json` portable chỉ giữ:

```json
{
  "Provider Name": {
    "base_url": "https://example.com/v1",
    "api_key": "...",
    "models": ["model-a", "model-b"]
  }
}
```

Main Window hỗ trợ:

- thêm/xóa/đổi tên provider;
- thêm/xóa model;
- chọn active model;
- test provider/model;
- import/export provider catalog;
- streaming override theo provider.

### Runtime reload

**Reload config.json** đọc lại:

- `config.json`
- `providers.json`
- `prompts.json`
- `.env`

V0.4.0 còn áp dụng live:

- OCR engine/config;
- Region Translate feature flag;
- hotkey;
- provider/model;
- prompt;
- cache/streaming.

## Config files

- `providers.json`: portable provider/base URL/API key/models.
- `prompts.json`: custom prompt overrides.
- `config.json`: app/runtime behavior, OCR, endpoint, streaming, hotkey, UI.
- `data/runtime_settings.json`: lựa chọn provider/target/style/speed gần nhất.
- `.env`: optional secret env variables/backward compatibility.
- `current_plan.md`: roadmap chi tiết và architecture target.

## Cài và chạy trên Windows

Khuyến nghị Python 3.11 hoặc 3.12 x64.

Chạy:

```powershell
run.bat
```

`run.bat` sẽ tạo `.venv` và cài dependencies, bao gồm `rapidocr_onnxruntime` cho OCR local.

Hoặc chạy thủ công:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Hotkey mặc định

```text
Alt+T        Translate Selection
Alt+Shift+T  Translate + Replace
Alt+S        Region Translate
Alt+L        Live Translate placeholder (chưa triển khai)
Alt+1        Target Vietnamese
Alt+2        Target English
Alt+3        Target Traditional Chinese
```

## Region Translate và DPI

V0.4.0 capture screenshot trước khi overlay xuất hiện. Crop region map từ Qt logical coordinate sang pixel coordinate của screenshot bằng `scale_x/scale_y`, nhằm hỗ trợ Windows DPI scaling tốt hơn.

Cần smoke-test thực tế trên:

- 100%
- 125%
- 150%
- multi-monitor khác DPI

Nếu có crop lệch, đây là blocker cho V0.4.1 trước khi làm Live Translate.

## Known limitations (V0.4.1)

- Selection không kéo xuyên hai monitor.
- Chưa có Live Screen Translate.
- Chưa có PDF translation thực tế.
- OCR Settings UI hiện chỉ hiển thị trạng thái; tuning sâu vẫn ở `config.json`.
- Bản đóng gói đã chạy OCR thật trên Windows hiện tại; Region overlay trong app bên ngoài và nhiều mức DPI vẫn cần kiểm tra thực tế.

## Verification

Automated suite kiểm tra:

- provider/config/prompt/cache cũ;
- OCR config validation;
- RapidOCR output normalization/confidence filtering;
- OcrWorker queue/reload;
- Region pipeline wiring;
- tray/main window Region actions;
- source compile.

Xem `IMPLEMENTATION_HANDOFF.md` cho kiến trúc kỹ thuật và `current_plan.md` cho roadmap chi tiết. Tài liệu UX tham chiếu: `docs/QuickUX_Design_Spec_V0_4_1.md`.
