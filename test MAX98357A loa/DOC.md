# Hướng dẫn kiểm tra loa MAX98357A với ESP32 (PlatformIO)

Tài liệu hướng dẫn kết nối, cấu hình và kiểm tra **mạch khuếch đại âm thanh I2S MAX98357A** với **ESP32** qua PlatformIO (VS Code). 

---

## 1. Trạng thái dự án hiện tại (Cập nhật 19/06/2026)
* **Chế độ hoạt động:** Phát ghép chuỗi file MP3 từ bộ nhớ Flash (LittleFS) để tạo thành câu thông báo số tiền hoàn chỉnh (ví dụ: *"đã nhận được mười một nghìn đồng"*).
* **Kết quả kiểm tra phần cứng:** Đã chạy thử nghiệm thành công chế độ phát tiếng Beep 1kHz để xác minh kết nối dây dẫn và hoạt động của loa hoàn toàn ổn định.
* **Âm lượng (Volume):** Đang cấu hình ở mức **tối đa (21/21)** để âm thanh đầu ra to rõ nhất.

---

## 2. Sơ đồ kết nối phần cứng (ESP32 ➔ MAX98357A)

Do các board ESP32 (đặc biệt là dạng Vietduino) có ký hiệu nhãn chân in trên board khác với số thứ tự GPIO thực tế trong mã nguồn, bạn cần cắm đúng theo bảng đối chiếu dưới đây:

| Chân trên ESP32 | Nhãn in trên board | Chân trên MAX98357A | Ý nghĩa / Vai trò |
|:---|:---|:---|:---|
| **3V3** hoặc **5V** | `3V3` / `5V` | **VIN** | Nguồn cấp cho mạch khuếch đại (Dùng 5V tiếng sẽ to hơn) |
| **GND** | `GND` | **GND** | Chân nối đất chung |
| **GND** | `GND` | **GAIN** | Cấu hình độ lợi (Gain) mặc định ở mức 9dB |
| **GPIO25** | `D4` | **DIN** | Đường truyền dữ liệu âm thanh số (`I2S_DOUT`) |
| **GPIO26** | `D5` | **BCLK** | Xung nhịp bit (`I2S_BCLK`) |
| **GPIO27** | `D6` | **LRC** (hoặc WS) | Chọn kênh âm thanh Trái/Phải (`I2S_LRC`) |
| **SPK+ / SPK-** | - | **Loa** | Kết nối trực tiếp vào 2 cực của Loa (4Ω hoặc 8Ω) |

> [!WARNING]
> **Chân SD (Shutdown) trên MAX98357A:** Phải **để trống (không cắm dây)**. Nếu nối chân này xuống GND, mạch khuếch đại sẽ bị tắt hoàn toàn và không phát ra tiếng.

---

## 3. Cấu trúc thư mục âm thanh và Quy tắc đặt tên file

Để phát âm thanh tiếng Việt ổn định trên bộ nhớ Flash (LittleFS) của ESP32 mà không gặp lỗi giải mã ký tự hoặc lỗi đường dẫn, các file đã được chuẩn bị như sau:

* **Thư mục gốc lưu trữ:** Các file âm thanh gốc nằm trong `sound/` (tiếng Việt có dấu và có khoảng trắng).
* **Thư mục nạp (LittleFS):** Được sao chép vào thư mục `data/` và chuyển đổi sang tên file viết thường, không dấu, dùng dấu gạch dưới `_` thay cho khoảng trắng để ESP32 đọc tốt hơn.

### Bảng ánh xạ file âm thanh:
* `đã nhận được.mp3` ➔ `/da_nhan_duoc.mp3`
* `mười.mp3` ➔ `/muoi_10.mp3`
* `một.mp3` ➔ `/mot.mp3`
* `nghìn đồng.mp3` ➔ `/nghin_dong.mp3`
* *(Và các file số khác từ 2-9 tương tự: `hai.mp3` ➔ `/hai.mp3`, `ba.mp3` ➔ `/ba.mp3`...)*

---

## 4. Hướng dẫn nạp chương trình bằng Dòng lệnh (Windows Command Prompt)

Trong trường hợp lệnh viết tắt `pio` chưa được thêm vào biến môi trường PATH của Windows, bạn cần dùng đường dẫn tuyệt đối của PlatformIO Core để nạp.

### Bước 1: Nạp hệ thống file âm thanh (chỉ cần làm khi có thay đổi file trong thư mục `data`)
Chạy lệnh sau để chuyển đổi toàn bộ file trong thư mục `data` thành định dạng ảnh LittleFS và nạp vào phân vùng flash của ESP32:
```cmd
"%USERPROFILE%\.platformio\penv\Scripts\pio.exe" run -t uploadfs
```

### Bước 2: Nạp code điều khiển
Chạy lệnh sau để biên dịch code trong thư mục `src` và nạp vào chip:
```cmd
"%USERPROFILE%\.platformio\penv\Scripts\pio.exe" run -t upload
```

### Bước 3: Xem Log Monitor để gỡ lỗi
Để kiểm tra xem chip chạy ra sao, có đọc được file hay không, hãy bật monitor bằng lệnh:
```cmd
"%USERPROFILE%\.platformio\penv\Scripts\pio.exe" device monitor
```
*(Ấn tổ hợp phím `Ctrl + C` hoặc `Ctrl + ]` để thoát monitor).*

---

## 5. Giải thích cơ chế ghép câu trong mã nguồn (`src/main.cpp`)

Để tạo ra âm thanh liền mạch như một câu nói tự nhiên, chương trình sử dụng cấu trúc hàng đợi phát (playlist):

1. Khai báo danh sách các file cần phát nối tiếp:
   ```cpp
   const char* playlist[] = {
     "/da_nhan_duoc.mp3",
     "/muoi_10.mp3",
     "/mot.mp3",
     "/nghin_dong.mp3"
   };
   ```
2. Lắng nghe sự kiện kết thúc file MP3 (`audio_eof_mp3`) của thư viện `ESP32-audioI2S`:
   ```cpp
   void audio_eof_mp3(const char *info) {
     nextTrackFlag = true; // Kích hoạt cờ báo phát file tiếp theo
   }
   ```
3. Trong hàm `loop()`, khi cờ `nextTrackFlag` bằng `true`, chương trình sẽ tự động tăng chỉ số track `currentTrackIndex` và gọi hàm phát file tiếp theo. 
4. Khi phát hết danh sách, hệ thống sẽ đợi 3 giây (tránh bị lặp quá nhanh gây chói tai) rồi tự động phát lại từ đầu để phục vụ việc test.

---

## 6. Gỡ lỗi nhanh khi loa không kêu

Nếu gặp tình trạng nạp code thành công nhưng không nghe thấy âm thanh:
1. **Kiểm tra Log Monitor:** Xem xem log có báo `Phat file: ...` và `Xong file: ...` liên tục hay không. Nếu có chạy thì phần mềm đã hoạt động tốt, lỗi nằm ở phần cứng.
2. **Kiểm tra tiếp xúc:** Rút dây cắm ra cắm lại để đảm bảo tiếp xúc tốt. Đặc biệt là 2 chân nguồn `VIN` và `GND`.
3. **Nạp thử code Beep Test:**
   * Bạn có thể thay thế toàn bộ nội dung file `src/main.cpp` bằng code sinh sóng sin thuần (ở trong lịch sử Git hoặc liên hệ AI) để xem phần cứng có phát ra tiếng beep hay không. Code Beep Test không phụ thuộc vào LittleFS nên giúp loại bỏ 100% nguyên nhân do lỗi phân vùng nhớ.
