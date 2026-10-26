# AI Screen Translator

Ứng dụng dịch văn bản trên Windows: bôi đen để dịch nhanh, chụp một vùng màn hình để nhận diện chữ, hoặc dịch và thay thế trực tiếp trong ô đang nhập. Bạn có thể dùng Google Translate Free không cần API key, hoặc kết nối dịch vụ AI của mình.

Giao diện Dark Ocean với nền xanh biển sâu, điểm nhấn Cyan–Emerald và các cửa sổ dịch nổi giúp bạn đọc kết quả ngay bên cạnh nội dung đang làm việc.

**[Tải ứng dụng cho Windows](https://github.com/TKNguyenn/ScreenTranslator/releases/latest)** · [Báo lỗi / góp ý](https://github.com/TKNguyenn/ScreenTranslator/issues)

## App làm được gì?

| Tính năng | Cách sử dụng |
| --- | --- |
| **Dịch văn bản được chọn** | Bôi đen nội dung rồi dùng toolbar hoặc phím tắt để xem bản dịch trong popup. |
| **Quick Toolbar** | Chọn nhanh **VI / EN / 繁** để dịch sang tiếng Việt, tiếng Anh hoặc tiếng Trung phồn thể. |
| **Dịch vùng màn hình bằng OCR** | Khoanh vùng có chữ trong hình ảnh hoặc nội dung không thể bôi đen; app nhận diện chữ rồi dịch. |
| **Dịch và thay thế** | Thay văn bản đang chọn trong ô nhập bằng bản dịch, không tự nhấn Enter hay gửi tin nhắn. |
| **Popup linh hoạt** | Kéo để di chuyển, kéo cạnh hoặc góc để đổi kích thước; ghim cửa sổ, xem văn bản gốc và sao chép kết quả. |
| **Nhiều dịch vụ dịch** | Dùng Google Translate Free, Microsoft Translator, Google Cloud Translation hoặc API tương thích OpenAI. |
| **Tùy chỉnh cách dịch với AI** | Chọn model, phong cách Engineer / Chat / Email, chỉnh prompt và bật streaming khi dịch vụ hỗ trợ. |
| **Quản lý cấu hình** | Thêm, kiểm tra, nhập và xuất danh sách provider/model cùng các prompt riêng. |
| **Cài đặt hotkey** | Đổi phím tắt dịch bôi đen, thay thế, OCR vùng màn hình, Live Translate và ngôn ngữ đích ngay trong app. |
| **Dùng hằng ngày** | Chạy dưới khay hệ thống, gọi bằng phím tắt và dùng cache để tái sử dụng kết quả dịch. |
| **Cập nhật trong app** | Kiểm tra GitHub Releases và cài bản cập nhật ngay từ ứng dụng. |

## Cài đặt

Yêu cầu **Windows 10 hoặc Windows 11, 64-bit** và kết nối Internet để sử dụng dịch vụ dịch.

1. Mở [GitHub Releases](https://github.com/TKNguyenn/ScreenTranslator/releases/latest), tải file có tên kết thúc bằng **Setup.exe** trong phần **Assets**.
2. Chạy bộ cài, giữ đường dẫn mặc định hoặc chọn thư mục cài đặt khác.
3. Ở bước cuối, chọn có tạo shortcut trên desktop hay không rồi mở app.

Bản cài đặt đã kèm môi trường chạy và OCR, không cần cài Python hay quyền quản trị viên. Cài vào thư mục mà tài khoản Windows của bạn có quyền ghi để app lưu cấu hình và dữ liệu.

## Bắt đầu sử dụng

### Hướng dẫn bằng hình minh họa

Lần đầu mở app, cửa sổ **Hướng dẫn sử dụng** tự hiện với năm trang: dịch bôi đen, dịch chữ trong ảnh, dịch và thay thế, sử dụng popup, và thiết lập/trợ giúp. Mỗi trang có giao diện minh họa cùng thao tác thử bằng văn bản mẫu; không gửi yêu cầu dịch. Nút **Sao chép** sao chép bản dịch mẫu vào clipboard. Phím tắt trong hướng dẫn lấy từ cấu hình hiện tại.

Bấm **Tiếp theo**, **Quay lại** hoặc dấu trang để chuyển; **Bỏ qua**, **Esc** hoặc nút đóng để kết thúc. Sau khi cửa sổ hiện thành công, app lưu cờ `onboarding_seen` trong `data/runtime_settings.json`, nên các lần mở tiếp theo không tự hiện nữa, kể cả khi đã bỏ qua. Nếu chưa có cờ (bao gồm lần đầu dùng tính năng sau khi cập nhật), hướng dẫn sẽ hiện một lần; xóa dữ liệu runtime sẽ làm hiện lại.

Bạn luôn có thể mở lại bằng **Hướng dẫn sử dụng** ở cuối sidebar hoặc menu biểu tượng app trong khay hệ thống. Mở lại bắt đầu từ trang đầu và nạp phím tắt mới nhất.

### Chọn dịch vụ dịch

Bản cài mới có sẵn **Google Translate Free** và **Trial**. Mặc định app dùng Google Free và dịch sang **tiếng Việt**, nên bạn có thể thử dịch ngay mà không cần nhập API key.

Trong **Provider & Model**, bạn có thể chọn dịch vụ phù hợp:

| Dịch vụ | Cần chuẩn bị | Phù hợp khi |
| --- | --- | --- |
| **Google Translate Free** | Không cần API key | Muốn dịch nhanh và tiết kiệm chi phí. |
| **ScreenTranslator AI Trial** | Liên hệ người phát triển để nhận key riêng | Muốn thử AI với danh sách model có sẵn. |
| **Google Cloud Translation** | API key, bật Cloud Translation API và billing | Muốn dùng dịch vụ Google Cloud chính thức. |
| **Microsoft Translator** | Azure Translator key và Region của resource | Dùng Text Translation chính thức, gói F0 có mốc miễn phí 2 triệu ký tự/tháng. |
| **AI / API tương thích OpenAI** | Địa chỉ API, API key và model của nhà cung cấp | Muốn điều chỉnh cách diễn đạt bằng prompt và phong cách dịch. |

Sau khi chỉnh provider/model, bấm **Lưu & áp dụng**. Với Google và Microsoft, app dịch trực tiếp; prompt, phong cách AI và streaming không áp dụng.

Để dùng **Microsoft Translator**, bấm **+ Microsoft**, nhập **Key 1 hoặc Key 2**, rồi nhập Region đúng với Azure resource (mặc định `southeastasia`). App dùng endpoint **Text Translation** `https://api.cognitive.microsofttranslator.com`, hỗ trợ phát hiện ngôn ngữ và tiếng Trung phồn thể. Bấm **Kiểm tra Microsoft Translator**, chọn Microsoft ở **Provider đang áp dụng**, rồi **Lưu & áp dụng**.

Thống kê Microsoft nằm trong `data/microsoft_usage.sqlite3`, tính request thành công và ký tự theo tháng giờ Việt Nam. App ưu tiên header `X-Metered-Usage`, thiếu header thì ước lượng; cache không tính thêm. Thống kê cộng các profile Microsoft trên máy này, không chứa key hay nội dung dịch, không đồng bộ số dư Azure/thiết bị khác và không chặn dịch khi vượt mốc tham khảo. Quota, chu kỳ và giá thực tế phụ thuộc resource/gói Azure của bạn. Region được giữ khi xuất/nhập providers.json; các provider khác vẫn dùng schema cũ.

Trong **Trial**, nhập key được cấp, chọn **Endpoint** (`auto`, `responses`, `chat_completions` hoặc `completions`), model và chỉnh streaming riêng cho **Ultra Fast / Fast / Quality**. `auto` tự chọn endpoint phù hợp; URL và danh sách model được cấu hình sẵn. Giá cạnh model là ước lượng mỗi lượt: Luna từ 1đ, Flash từ 3đ, Sol từ 4đ; văn bản dài có thể tốn nhiều hơn.

Thanh hạn mức không hiện số tiền, bắt đầu từ mốc ước lượng 100đ/ngày và giảm theo model sau mỗi lượt dịch hoặc kiểm tra kết nối thành công. Mỗi lần mở app, app đọc ngày/giờ Việt Nam hiện tại và so với lần kiểm tra gần nhất; nếu đã qua 00:00 thì xóa lượt dùng của ngày cũ, lưu mốc mới và chỉ giữ hai mốc kiểm tra gần nhất. Khi app đang mở, timer cũng kiểm tra tối đa mỗi phút. Kết quả lấy từ cache không trừ thêm. Đây là **ước lượng không chính xác**, không đồng bộ số dư gateway hoặc máy khác và không chặn dịch khi thanh hết. Hạn mức thật vẫn do gateway quản lý. Nếu đang dùng catalog cũ, bấm **+ Trial** để thêm mà vẫn giữ các provider của bạn.

### Dịch bằng toolbar hoặc phím tắt

1. Bôi đen đoạn văn bản bằng chuột trong ứng dụng đang dùng.
2. Khi toolbar xuất hiện, bấm **VI**, **EN** hoặc **繁**.
3. Đọc kết quả trong popup; kéo thanh tiêu đề để di chuyển, kéo cạnh hoặc góc dưới phải để đổi kích thước.

Toolbar phụ thuộc vào khả năng cung cấp vùng chọn qua Windows UI Automation của ứng dụng đang dùng. Nếu toolbar không xuất hiện, thử **Alt+T**; với nội dung dạng ảnh hoặc không thể sao chép, dùng **Alt+S** để khoanh vùng OCR.

Các phím tắt mặc định:

| Phím tắt | Chức năng |
| --- | --- |
| **Alt+T** | Dịch văn bản đang chọn và mở popup. |
| **Alt+Shift+T** | Dịch và thay thế văn bản đang chọn trong ô có thể chỉnh sửa. |
| **Alt+S** | Chọn vùng màn hình, nhận diện chữ và dịch. |
| **Alt+1** | Đổi ngôn ngữ đích sang tiếng Việt. |
| **Alt+2** | Đổi ngôn ngữ đích sang tiếng Anh. |
| **Alt+3** | Đổi ngôn ngữ đích sang tiếng Trung phồn thể. |

Muốn đổi phím tắt, mở mục **Cài đặt** ở sidebar, bấm vào ô tương ứng rồi nhấn tổ hợp phím mới. Bấm **Lưu & áp dụng hotkey** để app kiểm tra trùng phím và đăng ký lại ngay; các thay đổi được lưu trong `config.json`.

App có thể tiếp tục chạy trong khay hệ thống. Để thoát hoàn toàn, dùng menu của biểu tượng app tại đó.

## Cập nhật ứng dụng

Bấm **Check for updates** ở sidebar để kiểm tra bản ổn định mới nhất trên GitHub.

- Nếu đã mới nhất, app hiển thị **Latest version** cùng phiên bản hiện tại.
- Nếu có bản mới, bấm **Update to…** để tải bộ cài. App kiểm tra file tải xuống, thoát để cài vào thư mục hiện tại rồi mở lại.

Cấu hình, provider, prompt và dữ liệu được giữ khi cập nhật. App tự kiểm tra một lần mỗi ngày khi mở, tính theo giờ Việt Nam; lần đầu mở cũng kiểm tra. Bạn vẫn có thể bấm nút để kiểm tra thủ công hoặc thử lại khi mất mạng. App chỉ tải/cài bản mới khi bạn bấm cập nhật. Cập nhật bằng bộ cài áp dụng cho bản Windows đã đóng gói; nếu chạy từ source, cập nhật mã bằng Git.

## Cấu hình và gỡ cài đặt

Cấu hình và dữ liệu nằm chung trong thư mục cài đặt, mặc định là `%LOCALAPPDATA%\Programs\AIScreenTranslator`:

| File / thư mục | Nội dung |
| --- | --- |
| `config.json` | Cấu hình ứng dụng. |
| `providers.json` | Danh sách dịch vụ, model và thông tin kết nối. |
| `prompts.json` | Các prompt tùy chỉnh. |
| `data/` | Cache, thiết lập runtime và log. |

Để gỡ app, chạy **Uninstall.exe** trong thư mục cài đặt hoặc mở **Windows Settings → Apps → AI Screen Translator → Uninstall**. Bạn có thể chọn giữ lại duy nhất `providers.json` và `prompts.json`, hoặc xóa toàn bộ dữ liệu thuộc app.

## Dữ liệu và phạm vi hỗ trợ

- OCR xử lý ảnh ngay trên máy. Văn bản cần dịch được gửi tới dịch vụ bạn chọn; ảnh chụp OCR không được gửi tới dịch vụ dịch.
- Việc chỉ bôi đen văn bản để hiện toolbar chưa gửi yêu cầu dịch. Yêu cầu được gửi khi bạn chọn thao tác dịch.
- API key có thể được lưu dạng văn bản trong `providers.json`. Giữ riêng file này và bản xuất provider nếu có chứa key.
- Google Translate Free dùng endpoint không chính thức, có thể bị giới hạn hoặc ngừng hoạt động. Google Cloud và các dịch vụ AI tính phí theo tài khoản của bạn.
- Toolbar không hoạt động tự động trong mọi ứng dụng. **Live Screen Translate** và **dịch file PDF trực tiếp** hiện chưa được triển khai.

## Chạy từ source

Cài **Python 64-bit** với Python Launcher (`py`) và Git trên Windows, sau đó chạy trong PowerShell:

```powershell
git clone https://github.com/TKNguyenn/ScreenTranslator.git
cd ScreenTranslator
.\run.bat
```

`run.bat` tạo môi trường ảo, cài thư viện, tạo các file cấu hình từ mẫu nếu chưa có rồi khởi động app. Lần đầu cần Internet để tải thư viện. Nếu gặp lỗi, xem `data/logs/app.log`.

## Tài liệu và hỗ trợ

- [Hướng dẫn cài đặt, đóng gói và cập nhật trên Windows](docs/Windows_Release.md)
- [Cấu hình Google Translate Free và Google Cloud](docs/Google_Providers_V0_4_1_5.md)
- [Khắc phục sự cố toolbar và phím tắt trên Windows](docs/QuickUX_Windows_Troubleshooting.md)
- [Lịch sử phát hành và bộ cài](https://github.com/TKNguyenn/ScreenTranslator/releases)
- [Báo lỗi hoặc đề xuất tính năng](https://github.com/TKNguyenn/ScreenTranslator/issues)

Khi báo lỗi, ghi rõ phiên bản Windows, ứng dụng đang dịch, dịch vụ đã chọn và các bước tái hiện. Nếu gửi log, hãy xóa API key và nội dung riêng tư trước khi đăng.
