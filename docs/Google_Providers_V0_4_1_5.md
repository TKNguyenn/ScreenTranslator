# Google Translation Providers — V0.4.1.5

Integrated on 2026-10-15 from `google_translate_addon_for_codex.py`.

## Chọn dịch vụ

| Provider | Base URL | Model | Yêu cầu |
| --- | --- | --- | --- |
| Google Translate Free | `https://translate.googleapis.com` | `google-translate` | Không cần key; endpoint Web không chính thức, có thể bị giới hạn hoặc thay đổi |
| Google Cloud Translate | `https://translation.googleapis.com` | `nmt` | Cloud Translation API được bật, billing và API key; có tính phí |

Không có fallback từ Free sang Cloud. Cả hai dùng dịch máy trực tiếp, không hỗ trợ prompt, style Engineer/Chat/Email hay streaming/tốc độ AI. Các setting AI vẫn được giữ để dùng khi chuyển lại provider AI.

Nút Google Free/Cloud nằm cùng hàng Import/Export. Khi chọn một trong hai loại Google, khung Models và Streaming override theo profile được ẩn hẳn; chọn provider AI sẽ hiện lại.

## Cấu hình qua GUI

1. Thoát hẳn app từ tray, chạy `python main.py` và kiểm tra v0.4.1.5.
2. Vào Provider & Model, bấm **+ Google Free** hoặc **+ Google Cloud**. Nút chọn form để chỉnh, chưa đổi provider đang áp dụng và chưa ghi file.
3. Với Cloud, nhập key hoặc tên biến môi trường chứa key vào API key env. Key nhập trực tiếp được ưu tiên. Có thể lưu Cloud chưa có key nếu nó chưa phải provider đang áp dụng.
4. Tùy chọn Test provider gửi câu Hello từ English sang tiếng Việt; với Cloud request này có thể phát sinh phí.
5. Chọn Google tại **Provider đang áp dụng**, bấm **Lưu & áp dụng**. Google được dùng cho toolbar, hotkey bôi đen/replace và text từ OCR.

Thêm preset lần nữa sẽ chọn profile cùng tên hiện có, không ghi đè key/cấu hình. Có thể đổi tên và xóa như các provider khác. Sau khi đổi tên, bấm thêm preset tạo entry với tên preset nếu chưa tồn tại.

## Portable catalog

```json
{
  "Google Translate Free": {
    "base_url": "https://translate.googleapis.com",
    "api_key": "",
    "models": ["google-translate"]
  },
  "Google Cloud Translate": {
    "base_url": "https://translation.googleapis.com",
    "api_key": "",
    "models": ["nmt"]
  }
}
```

Ví dụ trên minh họa schema, không thay thế catalog đang dùng. Import file vẫn theo hành vi import catalog hiện tại; dùng nút preset để thêm vào danh sách sẵn có. App tự suy ra type từ URL Google chuẩn, còn type/timeout/env key/active model và setting ứng dụng nằm ở config.json. Không cần dependency mới.

## Dữ liệu, cache và lỗi

- Web gửi text qua URL GET tới Google. Tránh dùng cho text cần bảo mật nếu chưa được phép gửi ra dịch vụ. Log ứng dụng không ghi GET URL/text/key; addon hạ logger httpx/httpcore về WARNING, làm giảm chẩn đoán HTTP cho cả tiến trình.
- Cloud gửi text trong JSON POST và key trong X-goog-api-key. API key nhập trực tiếp vẫn được lưu vào providers.json theo cơ chế catalog hiện tại; dùng biến môi trường nếu không muốn ghi key vào file portable.
- Source Auto được hỗ trợ; zh-Hant → zh-TW, zh-Hans → zh-CN. Web chia đoạn dài theo giới hạn URL, tối đa 12 chunk; quá dài báo lỗi trước khi gửi, không tự dùng Cloud.
- Cache Google bỏ qua prompt/style/speed nhưng giữ text, ngôn ngữ nguồn/đích, provider và model. Cache vẫn dùng cơ chế lưu text/bản dịch SQLite hiện có. Tắt cache bằng tùy chọn hiện tại nếu không muốn lưu các bản dịch mới.
- HTTP 403: kiểm tra key, quyền/API/billing hoặc hạn chế dịch vụ. HTTP 429: đợi rồi thử lại. HTML/captcha/JSON sai hoặc timeout hiển thị lỗi đã lọc dữ liệu nhạy cảm.
- Cloud allowance không phải spending cap; quản lý quota/billing trong tài khoản Google Cloud.

## Kiểm tra

```powershell
python -m unittest discover -s tests -q
python -m compileall -q app main.py tests
python tests/windows_google_ui_smoke.py
python tests/windows_quickux_ui_smoke.py
```

160 tests pass, compile pass, cả hai native Windows UI smoke pass. MockTransport kiểm tra payload, response parsing, language aliases, encoded chunking, missing/env key, HTTP/timeout/malformed/empty-response handling, cache isolation/reuse, provider inference, preset/rename/delete/save, AI control restoration và real-translation test request. Native Google smoke dùng cửa sổ ngoài vùng màn hình, config giả lập, không mouse hook/API; ảnh ở `artifacts/google-v0415/`.

Chưa gọi endpoint thật, chưa xác minh quota/billing/key hoặc chuỗi dịch qua Google trong từng app bên ngoài. Người dùng cần thử nút Test và toolbar sau khi áp dụng provider.
