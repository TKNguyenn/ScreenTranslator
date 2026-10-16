> **Approved change (2026-10-12): auto-show ON is the V0.4.1 default. Prototype copy initially suggested OFF; user chose ON. P0 only.**
>
> **V0.4.1.3 implemented update:** user requested visible solid backgrounds and a movable/resizable popup. Toolbar/popup now use explicitly painted navy cards with teal accents. Popup starts at 460×360, minimum 360×280; drag its header or metadata to move, drag its border/bottom-right grip to resize. Size stays between requests for the current session. Streaming/final/error responses preserve user geometry. A vertical splitter divides translation and optional original text. Pin keeps the popup open on external clicks; the windows remain no-activate/topmost. The earlier fixed-size proposal below is historical.

> **V0.4.1.4 identity update (2026-10-14):** approved logo 1 Glyph Slash and UI 1 Aurora Bento are now used across the app. Floating surfaces retain their opaque directly painted content, with Dark Ocean #080E1A and a Cyan #38BDF8 → Emerald #10B981 rim. Moving/resizing behavior above remains implemented. See `Ocean_UI_Design_V0_4_1_4.md` for the current design.

# QUICK UX — THIẾT KẾ ĐỀ XUẤT

**Dự án:** AI Screen Translator (Windows 10/11)
**Code baseline:** V0.4.0 Region Translate
**Milestone dự kiến:** V0.4.1 Quick UX (đưa hạng mục V0.7 lên trước)
**Trạng thái:** thiết kế đã được chốt và V0.4.1 P0 đã được code. Tài liệu này lưu lại proposal gốc; `current_plan.md` và `IMPLEMENTATION_HANDOFF.md` mô tả implementation thực tế và những mục dời sang P1.

## 1. Mục tiêu

Dịch trong 1–2 thao tác từ nội dung đang đọc trên Windows; không cần mở Main Window, không chiếm màn hình, không làm gián đoạn việc nhập liệu. Tận dụng dịch bôi đen và replace đã có, cùng provider/model, prompt Engineer/Chat/Email và Ultra Fast/Fast/Quality.

## 2. Mô hình giao diện

### A. Floating Selection Toolbar

- Khi user bôi đen văn bản và **bật tùy chọn tự hiện**: sau 250 ms, xuất hiện toolbar bên cạnh hoặc dưới điểm kết thúc vùng bôi đen.
- Nếu người dùng chủ động **tắt tính năng tự hiện** (đề xuất OFF ban đầu đã bị thay bằng **ON mặc định** theo quyết định của user): không tự nổi khi người dùng chọn chữ; các phím tắt hiện tại vẫn hoạt động. Có thể bổ sung hotkey riêng để chỉ mở toolbar.
- Giao diện mặc định: `[ VI ] [ EN ] [ 繁 ] | [ ✦ ] [ ⋯ ]`.
- Bấm ngôn ngữ sẽ gọi dịch một lần theo model/style/speed hiện hành rồi bật Quick Translation Popup.
- `✦` mở giải thích kỹ thuật; `⋯` chứa Dịch và thay thế, Tóm tắt, Settings. Explain/Summarize có thể chuyển sang nhánh P1 nếu muốn ship MVP sớm.
- Thanh tự biến mất khi selection bị bỏ, người dùng đổi vùng hoặc timeout, trừ khi đang hiển thị bản dịch được ghim.
- Không hiển thị khi không có selection; không hiển thị trên password field, secure desktop, game fullscreen hoặc ứng dụng trong danh sách loại trừ.
- Không bắt đầu request API **chỉ vì** người dùng bôi đen. API chỉ được gọi sau một lệnh rõ ràng.

### B. Quick Translation Popup

- Popup xuất hiện sát toolbar/chữ được chọn; tự lật hướng nếu gần mép màn hình. Kích thước đề xuất 400–440 px rộng, chiều cao co theo nội dung, có giới hạn/scroll cho văn bản dài.
- Header: ngôn ngữ đích, style, speed, provider/model đang dùng, Pin, Close.
- Nội dung: trạng thái đang dịch, có thể hiển thị dần nếu streaming được bật trong profile.
- Actions: `Sao chép`, `Thay thế`, `Xem văn bản gốc`, `Ghim`, `Đóng`.
- `Thay thế` chỉ hoạt động khi text gốc vẫn có vị trí/focus hợp lệ và app nguồn cho phép paste. Không tự nhấn Enter hoặc gửi chat/email.
- Khi copy hoặc thay thế xong cần có feedback nhỏ; khi lỗi phải hiển thị lý do, không im lặng.
- `Escape` hoặc click ngoài vùng đóng popup nếu chưa được ghim; ghim thì chỉ đóng thủ công.

### C. Quick Compose / Dịch khi gõ (đề xuất sau bản toolbar MVP)

- Gọi từ hotkey tùy chỉnh (ví dụ Alt+Enter, **không tự áp mặc định do có thể xung đột**).
- Có ô soạn thảo, chọn đích, dịch và xác nhận `Thay vào ô đang gõ`.
- Không tự send/Enter; có `Hoàn tác`.
- MVP vẫn có cách nhanh tương đương với selected text: chọn đoạn đang gõ rồi dùng `Alt+Shift+T` của app hiện tại.

## 3. Main Window — Quick UX Settings

Đưa phần cấu hình này vào Settings của app lớn (về lâu dài thuộc tab riêng `Quick UX`).

| Setting | Mặc định đề xuất | Ghi chú |
| --- | --- | --- |
| Auto-show toolbar | OFF | Opt-in; tránh toolbar xuất hiện liên tục |
| Delay | 250 ms | Cho phép 150–600 ms |
| Languages | vi, en, zh-Hant | Cho phép thêm, đổi thứ tự (tương lai) |
| Dismiss popup on blur | ON | Pin sẽ override |
| Active style/speed | Kế thừa runtime | Không tạo thêm preset prompt riêng |
| Exclude apps | danh sách trống | Tương lai bổ sung UI chọn app |
| Privacy | No auto-request | Cố định: không gửi text chỉ vì chọn |

Cấu hình Quick UX nên ở `config.json`/runtime settings, **không** đặt vào `providers.json` hoặc `prompts.json`, vì 2 file portable kia đã có trách nhiệm riêng.

## 4. Luồng thao tác mong muốn

```text
User selects text
       |
[Auto toolbar ON and supported app?]
       | yes
       v
Lightweight FloatingToolbar, no network
       |
User clicks VI/EN/繁 or a command
       |
Capture source app/selection safely
       |
Existing InputWorker -> TranslationWorker -> Cache/Provider
       |
QuickPopup: loading -> stream partial (optional) -> final
       |
      +-- Copy
      +-- Replace (only if source is valid, never auto-send)
      +-- Pin / Close
```

## 5. Ràng buộc triển khai quan trọng

1. **Focus/source window:** Thanh nổi không nên chiếm focus của ứng dụng nguồn; nếu không `Ctrl+C` có thể copy nhầm toolbar. Lưu HWND và dùng UI Automation/capture an toàn trước khi thực hiện thao tác; fallback sang phím tắt cũ khi app không hỗ trợ.
2. **Windows compatibility:** Không cam kết phát hiện selection tự động trong mọi app. Browser, editor, Office và phần mềm công nghiệp sử dụng control đặc thù phải được test riêng.
3. **Clipboard:** Restore dữ liệu cũ an toàn nhất có thể; tránh phá text/image/format clipboard của user khi chỉ mở toolbar.
4. **Vị trí:** DPI-aware, đa màn hình, kể cả monitor phía trái/trên tạo tọa độ âm; tránh cạnh màn hình/taskbar.
5. **Thread model:** UI trên Qt main thread, translation giữ worker queue; thay ngôn ngữ liên tiếp phải tránh kết quả cũ ghi đè yêu cầu mới.
6. **Streaming:** Reuse từng profile streaming override; cập nhật popup theo delta có throttling, không stream riêng bằng UI thread.
7. **Selection privacy:** Ignore password/secure fields; không log văn bản nguồn hay bản dịch nguyên văn ở cấp INFO.
8. **Replace:** Chỉ cho phép khi source selection vẫn hợp lệ; không bật trong Region OCR; xác nhận lỗi thay thế nếu app nguồn không hỗ trợ paste.
9. **Keyboard support:** ESC đóng, Tab/Enter điều hướng nút khi thanh được focus; không cướp hotkey Alt+S/Alt+T/Alt+Shift+T hiện có.
10. **No duplicate requests:** Reuse cache and shared TranslationWorker; bỏ qua/đánh dấu stale progress nếu người dùng liên tục bấm nhiều ngôn ngữ.

## 6. Scope đề xuất nếu chuyển sang code

**P0 — V0.4.1 (mục tiêu đầu tiên)**

- Toolbar compact, click VI/EN/繁.
- QuickPopup compact với Copy/Replace/Pin/Close, status và streaming khi bật.
- Main Window Settings: bật/tắt tự hiện, delay, ngôn ngữ hiển thị.
- Giữ các hotkey và tray cũ.
- Selection compatibility fallback, multi-monitor/DPI, privacy guard.
- Unit tests + Windows smoke tests với Chrome/Edge/Notepad/Word/VS Code.

**P1 — V0.4.2**

- Explain selection + Summarize (prompt tác vụ riêng, không gây ảnh hưởng 9 prompt dịch).
- Quick Compose/translation while typing, hotkey tùy chỉnh, Undo.
- Per-app exclusions và một số điều chỉnh bố cục nâng cao.

## 7. Acceptance criteria trước khi ship

- Bôi đen chữ mà **không click toolbar** sẽ không gọi API.
- Dịch và replace vẫn hoạt động bằng hotkey cũ khi toolbar disabled.
- Copy/Replace không paste vào nhầm cửa sổ do toolbar cướp focus.
- UI không bị khuất ở 100/125/150% DPI, monitor trái/phải.
- QuickPopup không giật lag khi nhận chunk streaming hoặc OCR/translation đang chạy.
- Reset settings quay về mặc định, không ảnh hưởng `providers.json` và `prompts.json`.
- Có hành vi rõ ràng khi app không hỗ trợ auto selection và khi clipboard copy thất bại.

## 8. Những gì mockup thể hiện và không thể hiện

**Có:** Bố cục đề xuất, lựa chọn ngôn ngữ, popup kết quả, copy/replace/undo mô phỏng, pin, mở rộng thao tác, compose, settings tương tác.

**Chưa có:** Bắt selection ngoài Windows thật, clipboard thật, API network, dịch thật, OCR thật, UI Automation, hotkeys hệ thống. Các bản dịch trong mockup là ví dụ cố định.

### Cần duyệt

1. Hình dạng floating bar và vị trí popup có vừa ý không?
2. Auto-show mặc định OFF hay ON?
3. Ship MVP P0 trước hay gom cả Explain + Compose vào đợt code đầu tiên?
