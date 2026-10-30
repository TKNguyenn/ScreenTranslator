# CURRENT PLAN — AI SCREEN TRANSLATOR

## Built0.6.0 — 2026-10-30

User-selected version0.6.0 packages Explain, icon-only toolbar, Markdown display and six-page guide with provider/model instructions. Build complete:253 source tests,2 native Markdown tests and10 frozen self-checks pass;59 modules/main/assets/defaults match source. Corrected Qt image-resource fallback found by clean build testing (encoded URL fixture, transparent placeholder). Delivered dist/ScreenTranslator-0.6.0/ScreenTranslator.exe (keep _internal) and release/AI-Screen-Translator-0.6.0-Setup.exe; source/version/installer aligned. SHA256 stable after observation/self-check/delivery; AV report metadata unchanged. Full evidence/hashes in .ai/implementation_handoff.md and artifacts/build-0.6.0-20261030/result.json. No install/live API/push/publish; previous entries are history.

## Explain Adaptive v1.1 — 2026-10-30 (source only)

Task `explain-adaptive-v1-20261030`: implemented the supplied v1.1 spec against current 0.5.1 source. Authoritative current plan: `.ai/current_plan.md`; handoff: `.ai/implementation_handoff.md`. Added Explain through the existing Quick UX pipeline, fixed system prompt, cache bypass, safe popup and existing-language setting. Baseline 229 tests; final 247/247 tests pass, including 18 Explain cases; native Windows render 100%/150% and compileall pass. Independent review found no actionable defects. Logs/render evidence: `artifacts/explain-*`. No live-model acceptance, new binaries/version, install, sync or publishing; existing build entries below are historical.

## Build 0.5.1 — 2026-10-26

Đã tăng source/installer lên 0.5.1 và build phần hướng dẫn menu khay hệ thống mới. 229 tests đạt, 11 guide tests native Windows scale 150% đạt; EXE qua 10 frozen self-checks gồm hướng dẫn/OCR, 59 module khớp source, không kèm Pygments. EXE và Setup còn nguyên, hash ổn định, không có thay đổi log Trend Micro trong thời gian kiểm tra.

Setup `release/AI-Screen-Translator-0.5.1-Setup.exe`: 111990119 byte, SHA256 `eb1d80c1b655a510e6888b68cd3fe0dca8b610cf2f7362a07017eaba47b9e57e`. Portable `dist/ScreenTranslator-0.5.1/ScreenTranslator.exe`: 7954116 byte, SHA256 `0dd41b563531a960d6a1f6bcafadbcc4431cfdeb07d9192fb0a469340868b87b`; giữ `_internal`. Evidence `artifacts/build-0.5.1-20261026/`. Chưa cài/update, gọi provider thật, security rescan hoặc push/release 0.5.1. Các mục bên dưới là lịch sử.

## Bổ sung hướng dẫn menu khay hệ thống — 2026-10-26

Mẫu `artifacts/usage-guide-tray-preview/preview.py` đã được người dùng duyệt và yêu cầu đưa vào code. Thực hiện trực tiếp trong workspace phát triển hiện tại (không có Git); không tạo checkout khác hoặc thay đổi bản phát hành.

- [x] Viết và chạy test trước: 2 test mới thất bại vì chưa có icon/menu minh họa; sau tích hợp, 11 guide tests đạt.
- [x] Tích hợp mẫu vào `app/ui/usage_guide.py`: giữ 5 trang, chuột phải/bấm icon bật tắt menu, đổi ngôn ngữ mẫu, giải thích các mục menu và dấu ^. Demo chỉ tác động widget, không đổi cấu hình thật hoặc thoát app.
- [x] 229 unittest tests đạt; 11 guide tests đạt trên Qt offscreen và native Windows scale 150%; render native 100%/150% đạt ở 5 trang và cửa sổ 600x500, gồm wrapping/footer/cuộn đến icon. Compileall đạt. Review riêng không thấy blocker, reviewer chạy lại 11 guide tests đạt. Log full suite có exception `synthetic-failure` do test mouse callback chủ động tạo; kết quả suite OK.
- [x] Cập nhật README, handoff và Shared Brain; đã đọc lại xác minh note sau khi ghi. Không build, tăng version hoặc publish; EXE/Setup hiện có chưa chứa phần bổ sung này.

Phạm vi: `app/ui/usage_guide.py`, `tests/test_usage_guide.py`, README và tài liệu trạng thái. Các caller controller/sidebar/tray và frozen self-check giữ giao diện `UsageGuideDialog(hotkeys, parent)`/5 trang. Review tập trung: demo không ghi runtime; Thoát chỉ giải thích; lựa chọn ngôn ngữ mẫu loại trừ nhau; icon dùng được bằng bàn phím; nội dung dài cuộn mà footer vẫn dùng được.

## Trạng thái hiện tại — 2026-10-26, v0.5.0

Popup hướng dẫn năm trang đã được người dùng dùng thử và chấp nhận. Giữ hành vi hiện lần đầu và mở lại từ sidebar/tray. Packaging loại Pygments (dependency tùy chọn của HTTPX CLI, app không dùng). Build sạch 0.5.0: 227 tests đạt, native frozen self-check 10/10, 59 module ứng dụng khớp source; EXE/Setup tồn tại, hash ổn định, không có cảnh báo Trend Micro mới trong thời gian theo dõi.

Setup `release/AI-Screen-Translator-0.5.0-Setup.exe`: 111993576 byte, SHA256 `5bdd281f6e3716edd3895e2d618c82311b199a56e3b0012de095801847d9bbab`. Portable `dist/ScreenTranslator-0.5.0/ScreenTranslator.exe`: 7952226 byte, SHA256 `def91ab5e7133cc722dc6643b5e7e21f55e4d8b1270d75691a7d38cee0d100eb`; giữ `_internal`. Người dùng đã yêu cầu push và phát hành v0.5.0; public baseline trước lượt này là v0.4.1.12 tại commit `6c24b9b32e55745a4df46cb7e2781bbab340ec95`.

Security review tập trung có một lỗi thấp còn mở: raw response lỗi của OpenAI-compatible provider có thể đi vào log cục bộ (CWE-532); chưa sửa ở 0.5.0. Phạm vi review partial, không phải chứng nhận malware-free. Chưa lặp full install/update hoặc gọi provider thật trong verification tự động. Các mục ngày 24/10 và 21/10 bên dưới là lịch sử, không ghi đè trạng thái này.

## Hướng dẫn sử dụng — 2026-10-24 (source, chưa build)

Đã tích hợp popup PySide6 năm trang theo mẫu được duyệt: minh họa dịch bôi đen, OCR vùng, thay văn bản, popup và Help. Các demo dùng nội dung cố định, không gọi provider; Sao chép ghi bản dịch mẫu vào clipboard. Mở qua nút Hướng dẫn sử dụng ở cuối sidebar và menu tray; giữ một dialog đang hiện, mở lại từ trang đầu, lấy hotkeys hiện tại. Startup mở sau cửa sổ chính và lỗi provider ban đầu nếu có; lưu `onboarding_seen=true` vào RuntimeSettingsStore sau khi hiện thành công, đóng/bỏ qua vẫn tính đã xem. Thiếu cờ thì hiện một lần, bao gồm user cũ nhận tính năng lần đầu; cập nhật bình thường giữ marker. Lỗi ghi marker được log, không chặn app/hướng dẫn. Nội dung có scroll khi màn hình thấp, footer luôn ngoài scroll.

Validation: 227 unittest tests pass; 9 guide tests pass riêng trên Qt Windows ở scale 150%; native smoke cả 100%/150% kiểm tra năm trang, text wrapping, sidebar và compact scroll; source offline self-check 10/10 pass; compileall pass. Evidence `artifacts/usage-guide/` (PNG, smoke.py, source-self-check.json). Chưa build EXE/Setup hoặc thử live provider; version giữ 0.4.1.12. Các artifact build bên dưới có trước thay đổi này.

**Cập nhật:** 2026-10-21 · giờ Việt Nam
**Source hiện tại:** v0.4.1.12 — thêm loading wave cho popup trên nền MicrosoftOnly .11.
**Trạng thái:** .12 đã build và verify local ngày 2026-10-21; public baseline là v0.4.1.11 đã phát hành ngày 2026-10-20.
**Nền tảng:** Windows 10/11 x64; môi trường build đã kiểm chứng: Python 3.11.9.

Plan này thay thế bản từ nhánh Azure Monitor OAuth cũ. Đây là trạng thái và roadmap cho source MicrosoftOnly hiện tại; lịch sử thay đổi chi tiết nằm ở Releases và tài liệu thiết kế liên quan. Không coi các đề xuất tương lai là chức năng đã có.

## 1. Workspace và release hiện tại

| Mục | Giá trị |
| --- | --- |
| Workspace phát triển | `C:/Users/kietj/Documents/FINEPRO/Image Processing/ScreenTranslator_V0_4_1_11_MicrosoftOnly` |
| Checkout phát hành | `C:/Users/kietj/Documents/GitHub/ScreenTranslator` |
| Repository | https://github.com/TKNguyenn/ScreenTranslator |
| Version source | `app/version.py`: `0.4.1.12` |
| Commit release | `3bddac70a64815dd216949c7de7944b0789ef5ff` |
| Release | [v0.4.1.11](https://github.com/TKNguyenn/ScreenTranslator/releases/tag/v0.4.1.11) |
| Bộ cài public .11 | `release/AI-Screen-Translator-0.4.1.11-Setup.exe` |
| Portable EXE | `dist/ScreenTranslator/ScreenTranslator.exe`; phải giữ `_internal` bên cạnh |

Setup đã phát hành: **111973776 byte**, SHA256:

```text
e8955af08a532aacf6f1a4b088d13257378ce2f11b068f6c653d9154d98f7e28
```

EXE .11 đã phát hành có SHA256 `82e7a5bd407565f88ba5134dca1542a4229b55d398501368f9e57aea593fd84e`. EXE trong dist được thay bởi build local .12; không dùng checksum .11 để xác minh .12.

### Thay đổi local .12 — loading wave

WaveTranslationOutput vẽ từng ký tự “Đang dịch...” thành sóng trái sang phải, cao 5 logical pixels, chu kỳ 1650 ms, lệch mỗi ký tự 85 ms, màu cyan ở đỉnh. Timer chỉ chạy khi loading và visible; dừng khi streaming/result/cache/error/hide/close. Text thật vẫn trong document cho accessibility. Không đổi provider/controller API hoặc thêm dependency.

Source .12 qua 218 tests, compile và native Windows Quick UX smoke; 17 popup tests trên Qt Windows cũng qua. Build exit 0; EXE cuối qua 9 offline self-checks, 58 product modules khớp source và có WaveTranslationOutput. Setup metadata 0.4.1.12. Chưa sync/push/release .12 hoặc lặp install/uninstall/live provider.

Artifact local: `release/AI-Screen-Translator-0.4.1.12-Setup.exe`, 111958270 byte, SHA256 `95f6b8a7537936ac335c0eae55f2e606f6910fa9b2880d91aaf6a28f13732ae9`. EXE .12 SHA256 `bd109e3c9b5110183965170269c11ceff833c9a967653e8891ed7d2565eaa6b6`. Evidence: `artifacts/build-0.4.1.12-20261021-114924/result.json`.

## 2. Chức năng đã triển khai và phát hành

### Dịch và quản lý provider

- Dịch text selection bằng hotkey, popup kết quả, dịch và thay thế trong ô nhập; không tự Enter/send.
- API tương thích OpenAI, Google Translate Free, Google Cloud Translation, Microsoft Translator và AI Trial; mock provider phục vụ test.
- Provider/model manager: thêm, kiểm tra, lưu/áp dụng, import/export catalog. Prompt manager theo Engineer/Chat/Email và Ultra Fast/Fast/Quality; hỗ trợ override/reset.
- Streaming cho AI theo cấu hình và cache có bật/tắt. Google/Microsoft dịch trực tiếp, không dùng prompt/style/speed AI hoặc streaming.
- Defaults sạch có Google Translate Free + Trial, Google Free active; không kèm API key cá nhân.

### Quick Toolbar và popup

- Auto-show mặc định ON; mouse drag/double-click → debounce 250 ms → UIA selection → toolbar. Chỉ bôi đen không gọi API hoặc dùng Ctrl+C thăm dò.
- Toolbar hiện logo, Dịch và các ngôn ngữ được bật: **VI / EN / 繁**. Menu `…` đã bỏ. Chọn ngôn ngữ là one-shot override, không đổi target toàn app.
- Timeout mặc định 8000 ms; hover dừng timer, rời toolbar khởi động lại timer 1400 ms. Selection tối đa mặc định 6000 ký tự.
- Popup mặc định 460×360, tối thiểu 360×280; kéo header để di chuyển, kéo cạnh/góc để resize. Giữ kích thước trong phiên và qua streaming/final/error.
- Có Sao chép, Thay thế khi nguồn đủ điều kiện, Xem gốc, đóng và ghim; không chiếm focus. Esc đóng Quick UI; click ngoài đóng popup chưa ghim nếu dismiss_popup_on_blur bật.
- Ghim là **📌 U+1F4CC**, Segoe UI Emoji 20px, vùng bấm 34×34; không nền/viền kể cả hover/checked; **50% opacity khi chưa ghim, 100% khi ghim**. Tooltip/accessibility name mô tả thao tác.
- Giữ giao diện Dark Ocean #080E1A, Cyan #38BDF8, Emerald #10B981; floating surfaces có nền đặc. Quick UX settings và tray toggle áp dụng trực tiếp.

### Region Translate / OCR

- Alt+S mặc định, tray hoặc Main Window mở selector; chọn một vùng trên một monitor/lần. Esc/right-click hủy. Capture ánh xạ logical coordinates sang pixel theo DPI.
- RapidOCR/ONNX Runtime chạy local trong worker, lazy init; confidence mặc định 0.45, chỉnh qua config. Có log thời gian OCR.
- Ảnh giữ local; chỉ text OCR đi vào pipeline dịch. Region không hỗ trợ Replace. OCR runtime/model **đã bundle trong bản Windows**.

### Microsoft Translator và local usage

- Adapter `app/providers/microsoft_provider.py` dùng `microsoft_translator.py` và `microsoft_translator_usage.py`. HTTPS Text Translation v3; nhập API key trực tiếp và Region, mặc định southeastasia. Hỗ trợ auto-detect và Traditional Chinese.
- Có + Microsoft, key/Region test và thống kê tháng. Region giữ qua save/rename/import/export. Microsoft bỏ api_key_env và timeout_s khỏi cấu hình lưu; dùng client timeout mặc định 20 giây. Provider khác giữ các tùy chọn hiện có.
- `data/microsoft_usage.sqlite3` ghi request thành công, ưu tiên X-Metered-Usage; thiếu thì ước lượng. Cache không tính thêm; dedup request ID; tháng theo giờ Việt Nam.
- Usage cộng các Microsoft profile trên máy, không lưu key/text. Lỗi ledger không làm mất bản dịch. Mốc 2 triệu ký tự chỉ tham khảo; không phải số dư Azure trực tiếp, không đồng bộ thiết bị khác và không chặn dịch.
- **Nhánh này không có Azure Monitor OAuth, Connect/Disconnect tài khoản, Resource/Tenant ID, remote metrics sync, MSAL hay token cache DPAPI.** Bảng snapshot legacy nếu có được giữ nguyên nhưng bỏ qua. Không đưa lại phần đã bỏ khi chưa có yêu cầu.

### Trial, hotkeys, update và đóng gói

- Trial có URL/model cố định, key riêng, endpoint auto/responses/chat_completions/completions và streaming override theo chế độ. Thanh quota là ước lượng cục bộ theo model; cache/lỗi không trừ, reset theo ngày Việt Nam, không đọc quota gateway và không chặn dịch khi về 0.
- Trang Cài đặt chỉnh bảy hotkey, release delay, suppress; từ chối hotkey rỗng/trùng và đăng ký lại sau lưu. Hotkey Live là phần dành sẵn, chưa có Live Translate.
- Check for updates dùng GitHub stable release. Startup kiểm tra metadata một lần/ngày Việt Nam, gồm lần đầu; manual retry không hạn chế. Tải/cài cần bấm Update; xác minh tên/kích thước/SHA256, không downgrade.
- PyInstaller + Inno Setup đã tạo Windows EXE/Setup; người dùng không cần Python. Giữ workflow unsigned hiện có. Cấu hình/data cùng thư mục cài, hỗ trợ custom path và migration legacy không ghi đè file sẵn có.
- Gỡ cài có lựa chọn giữ providers.json/prompts.json hoặc xóa dữ liệu thuộc app, không xóa file không thuộc app. Key hiện vẫn plaintext trong providers.json; chưa có kho credential bảo mật cho key dịch.

## 3. Kiến trúc và ràng buộc cần giữ

| Thành phần | Trách nhiệm |
| --- | --- |
| main.py | Bootstrap Qt/config/single-instance/controller |
| app/controller.py | Điều phối UI/worker, runtime state và vòng đời job |
| app/quickux/ | Mouse candidate, UIA probe và xác minh selection |
| app/ui/ | Hiển thị và tương tác cửa sổ/selector |
| app/ocr/ và OcrWorker | OCR local và lịch chạy nền |
| TranslationWorker | Hàng đợi dịch, cache, prompt/provider, streaming |
| app/providers/ | Adapter/transport cho provider |
| app/services/ | Config/catalog, hotkey, clipboard, cache, update và runtime settings |

Runtime data gồm config.json, providers.json, prompts.json, data/runtime_settings.json, data/trial_usage.json, data/microsoft_usage.sqlite3 và cache/log. Daily update marker cùng Trial store nhưng độc lập số dư. Không đưa runtime data/key vào Git hoặc release.

1. Network, OCR và UIA chạy ngoài Qt UI thread; mouse hook không gọi Qt trực tiếp.
2. Auto-selection không Ctrl+C thăm dò, bỏ qua password fields; thiếu bằng chứng editable thì không cho Quick Replace.
3. Trước dán xác minh HWND/focus/selection; Esc/Close/đổi selection/callback muộn không làm paste nhầm. Không tự Enter/send.
4. Screenshot OCR mặc định local; cloud image upload chỉ có thể thêm qua opt-in rõ ràng. Không log key/full sensitive text.
5. Live/PDF tương lai reuse capture/OCR/TranslationWorker/cache/provider/prompt; không thêm pipeline trùng.
6. Bảo toàn cấu hình và dữ liệu khi nâng version; migration phải có kiểm chứng. Không gom business logic vào main.py.

## 4. Kiểm chứng và giới hạn

### Bằng chứng của v0.4.1.11

- **215 unit/widget/source tests** qua tại workspace và checkout phát hành ngày 2026-10-20.
- **9 offline checks trên EXE cuối** qua: Qt/TLS/assets/forms, Quick UI, UIA backend và OCR HELLO WORLD 123; không gọi provider thật.
- **58 product modules** trong EXE khớp source; version Setup/EXE 0.4.1.11. Remote main/tag đúng commit, một Setup asset, digest GitHub khớp local.
- Native Windows Quick UX smoke qua nền đặc/topmost/no-activate/drag/geometry. Pin render normal/hover/on/off và opacity/dismiss được kiểm tra.
- Evidence: `artifacts/build-0.4.1.11-20261020-155323/` và `artifacts/pin-icon/`.

### Chưa xác nhận đầy đủ / còn giới hạn

- Chưa lặp install/reinstall/gỡ hai chế độ hoặc update end-to-end từ bản cài cũ lên .11. Test của bản trước không thay thế kiểm tra này.
- Chưa chạy live Microsoft key/gateway Trial trong lượt phát hành này.
- Cần acceptance Chrome/Edge/Notepad/Word/VS Code, password/readonly/editable và DPI 100/125/150%, nhiều monitor khác DPI hoặc tọa độ âm.
- Auto toolbar phụ thuộc UIA app nguồn; dùng hotkey fallback khi không hỗ trợ. Replace liên app vẫn có race nhỏ do Windows không có transaction chung.
- OCR lần đầu có thể chậm, một monitor/lần; chưa có OCR tuning UI đầy đủ.
- **Live Screen Translate và dịch file PDF trực tiếp chưa triển khai**; UI hiện là placeholder. Chưa có Quick Compose, Explain/Summarize, Glossary, History user-facing, Translation Memory hoặc Benchmark Center. Cache không phải History/TM.
- Bản cài chưa ký; SmartScreen/AV trên máy khác chưa được xác nhận. MicrosoftOnly build được quan sát giữ EXE, không phải chứng nhận AV hay kết luận chắc nguyên nhân phát hiện ở nhánh OAuth trước. Không sửa AV settings để vượt lỗi build.

## 5. Việc tiếp theo

**Chưa có feature mới được chốt.** Ưu tiên xác nhận bản đã phát hành và sửa lỗi có bằng chứng trước milestone lớn.

- [ ] Update bản đã cài lên .11: giữ config/provider/prompt, restart và không tự thêm shortcut ngoài ý muốn.
- [ ] Toolbar chỉ có language actions; không request khi chỉ chọn chữ; target VI/EN/繁 chỉ áp dụng một lần.
- [ ] Pin mờ/rõ, không nền/viền cả hover; ghim giữ popup, bỏ ghim cho phép đóng khi click ngoài, Esc/Close vẫn đóng được.
- [ ] Copy/Replace; hủy paste khi focus/selection đổi hoặc popup đóng trong lúc job chờ.
- [ ] Region OCR, popup placement và focus trên DPI/multi-monitor thực tế; ghi app/monitor/DPI khi có lỗi.
- [ ] Microsoft với key riêng khi user chủ động: key/Region, auto/繁, network error, cache và local usage qua restart/đổi tháng. Không tự test tính phí.
- [ ] Sửa theo ưu tiên: dữ liệu/clipboard/focus/Replace → crash → UIA/DPI/OCR → polish.
- [ ] Cùng user chọn phạm vi và version tiếp theo sau acceptance; không tự bắt đầu feature từ roadmap.

## 6. Roadmap dài hạn — chưa triển khai, chưa cam kết lịch/version

Giữ hướng sản phẩm của plan cũ; các nhãn V0.4.2/V0.4.5/V0.5… là dự kiến trước đây. Quick UX P0 và EXE/installer đã hoàn thành sớm, không tiếp tục xếp như hạng mục tương lai.

| Hướng | MVP khi được chọn | Ràng buộc / để sau |
| --- | --- | --- |
| Quick Compose / Explain / Summarize | User chủ động gọi từ text đang nhập hoặc selection | Không tự Enter/send; toolbar mới phải được duyệt nếu đổi UX |
| Live Screen Translate | Selected Region hoặc Current Window: frame differ/hash → local OCR → block tracking → dịch phần đổi → overlay | Reuse worker/cache; không API mỗi frame; rate/cancel và no-focus trước whole-desktop |
| PDF Translator | Extract text layer trước, scan mới local OCR; original/translation pane, page navigation, queue/progress/cancel | Reuse pipeline; layout-preserving export để sau MVP |
| Glossary | Chỉ đưa thuật ngữ khớp source vào prompt qua placeholder đã dành sẵn | Không gửi toàn glossary mỗi request; direct-provider cần thiết kế riêng |
| History / Translation Memory | History có tìm kiếm/bật tắt; reuse exact approved translation trước | Cache hiện tại không thay History/TM; fuzzy chỉ gợi ý |
| Benchmark / Diagnostics | TTFT, total latency, success/error, streaming và cache-off trên input cố định | Chỉ khuyến nghị theo số đo; không đoán từ tên model |
| Credential storage / Startup | Cân nhắc Credential Manager/DPAPI cho key; start-with-Windows nếu cần | Chưa có; chốt portable mode và migration trước |

V1.0 cần tiêu chí ổn định/acceptance theo phạm vi đã chốt, nâng cấp không mất dữ liệu và credential protection phù hợp. Không coi tất cả ý tưởng là điều kiện bắt buộc của bản kế tiếp.

## 7. Kiểm tra, build và phát hành các lần sau

Sau thay đổi chức năng:

```powershell
python -m unittest discover -s tests
python -m compileall -q app main.py microsoft_translator.py microsoft_translator_usage.py
python tests/windows_quickux_ui_smoke.py
```

Native smoke chạy trên Windows, không QT_QPA_PLATFORM=offscreen. Unit tests không thay acceptance ứng dụng ngoài/DPI. Tài liệu thuần túy chỉ cần kiểm tra nội dung/link/version.

Build khi user yêu cầu:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build.ps1
# Nếu compiler không ở đường dẫn mặc định, thêm -Iscc '<đường dẫn ISCC.exe đã có>'.
```

Đã dùng PyInstaller 6.22.3 và Inno Setup 7.1.0. Build exit 0 chưa đủ: xác nhận EXE còn tồn tại, source/version khớp, chạy ScreenTranslator.exe --self-check, đọc report và kiểm tra Setup/hash. Không đổi dependency/signing/pipeline chỉ dựa giả định AV.

Khi user yêu cầu push/release, theo `docs/Release_Workflow.md`:

1. Kiểm tra publishing checkout, branch/upstream/local edits; không force-push hoặc ghi đè thay đổi user.
2. Sync source/assets/tests/docs/clean examples/defaults; giữ file riêng của repo. Loại config cá nhân, .env, data/cache/build/dist/release/artifacts.
3. Review staged diff/secret và version/source/Setup trước commit/push. Không âm thầm thay published tag/release.
4. Stable tag v<APP_VERSION>, title AI Screen Translator <APP_VERSION>; release notes tiếng Anh theo mẫu, chỉ upload Setup đúng version.
5. Xác minh remote commit/tag, published release, tên/kích thước asset và GitHub SHA256 khớp local.

Sau thay đổi có ý nghĩa, cập nhật trạng thái/giới hạn/next task trong plan và handoff. Chỉ ghi kiểm chứng thực sự đã làm; không append status mới mà giữ phần hiện trạng mâu thuẫn phía dưới.
