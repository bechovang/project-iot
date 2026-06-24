# 03 - Firmware ESP32 (PlatformIO)

## 1. Yeu cau

- **VS Code + extension PlatformIO IDE**, hoac PlatformIO Core (CLI).
- Cap USB noi ESP32.
- Da dau day OLED + loa theo `01-phan-cung.md`.

Duong dan pio.exe tren Windows (neu chua co trong PATH):
```
%USERPROFILE%\.platformio\penv\Scripts\pio.exe
```

## 2. Cau hinh truoc khi nap: `firmware/include/config.h`

```c
// --- WiFi (STA - noi mang nha) ---
#define WIFI_SSID       "TenWifi"
#define WIFI_PASS       "MatKhau"

// --- Server backend tren LAN ---
//  Vi du PC chay backend co IP 192.168.1.50:
#define SERVER_BASE_URL "http://192.168.1.50:8000"

// --- Chu ky poll ---
#define POLL_CURRENT_MS   1500
#define POLL_PAID_MS      1500

// --- Chan OLED I2C ---
#define I2C_SDA   21
#define I2C_SCL   22

// --- Chan loa I2S ---
#define I2S_DOUT  25
#define I2S_BCLK  26
#define I2S_LRC   27
#define AUDIO_VOLUME 21   // 0..21
```

**Bat buoc sua:** `WIFI_SSID`, `WIFI_PASS`, `SERVER_BASE_URL`.
- ESP32 va PC chay backend phai cung mang WiFi LAN.
- **Khuyên dùng LAN IP:** `SERVER_BASE_URL` nên là `http://<IP-LAN-cua-PC>:8000` (ví dụ: `http://192.168.137.1:8000`), KHONG dùng URL công khai của tunnel (như `.loca.lt` hay `.ngrok-free.dev`) cho ESP32. Việc chạy trực tiếp qua LAN giúp ESP32 gửi nhận request siêu tốc, không phụ thuộc vào đường truyền Internet bên ngoài và loại bỏ hoàn toàn các lỗi kết nối/mạng chập chờn.
- `SERVER_BASE_URL` KHONG phải URL công khai webhook của PayOS.

## 3. Nap firmware - 2 buoc

Firmware can ca **file am thanh** (LittleFS) va **code**. Phai nap ca hai.

### Buoc 1: Nap file am thanh (LittleFS) - lam 1 lan / khi doi file MP3
```powershell
cd version1\firmware
pio run -t uploadfs
```
Lenh nay dong goi thu muc `data/` (cac file MP3) thanh anh LittleFS va ghi vao flash.

### Buoc 2: Nap code
```powershell
pio run -t upload
```

### Xem log
```powershell
pio device monitor -b 115200
```

> Neu `pio` chua co trong PATH, thay `pio` bang duong dan day du:
> `"%USERPROFILE%\.platformio\penv\Scripts\pio.exe"`

## 4. Log khoi dong mong doi

```
=== SMART QR PAYMENT - ESP32 ===
[AUDIO] LittleFS OK
[AUDIO] I2S ready
[NET] connecting to TenWifi....
[NET] connected, IP=192.168.1.77
[AUDIO] play: /da_nhan_duoc.mp3
[AUDIO] play: /chin.mp3
[AUDIO] play: /tram.mp3
[AUDIO] play: /chin.mp3
[AUDIO] play: /muoi.mp3
[AUDIO] play: /chin.mp3
[AUDIO] done
```
*Lưu ý: Thiết bị sẽ tự động phát âm thanh thông báo 999đ ngay sau khi khởi động để giúp bạn kiểm tra nhanh tình trạng hoạt động của Loa.*

Sau do khi co don:
```
[MAIN] show QR #1 amount=11000 len=129
```
Khi thanh toan:
```
[MAIN] PAID #1 amount=11000
[AUDIO] play: /da_nhan_duoc.mp3
[AUDIO] play: /muoi_10.mp3
[AUDIO] play: /mot.mp3
[AUDIO] play: /nghin_dong.mp3
[AUDIO] done
```

## 5. Bo nho da dung (tham khao)

Tu lan build that:
```
RAM:   18.3% (59896 / 327680 bytes)
Flash: 63.9% (1171945 / 1835008 bytes)
```
Con du cho mo rong.

## 6. Cau truc code firmware

```
firmware/
├─ platformio.ini      <- cau hinh build, thu vien
├─ partitions.csv      <- phan vung flash (app + LittleFS)
├─ include/            <- header (khai bao ham)
│   ├─ config.h        (them: cau hinh polling, stack size, core ID)
│   ├─ oled_ui.h
│   ├─ audio_vn.h
│   ├─ net_client.h    (chi lam nhiem vu goi HTTP thuan)
│   └─ sync_state.h    (MOI: khai bao struct shared state + accessor mutex/queue)
├─ src/                <- trien khai
│   ├─ main.cpp        (sua: tao NetworkTask, loop chi con UI + Audio)
│   ├─ oled_ui.cpp     <- ve QR (zoom x2 alphanumeric) + OLED
│   ├─ audio_vn.cpp    <- doc so tien tieng Viet
│   ├─ net_client.cpp  (sua: bo blocking trong loop, ket noi WiFi background)
│   └─ sync_state.cpp  (MOI: mutex cho current order, queue cho paid events)
└─ data/               <- MP3 (nap vao LittleFS)
```

### 6.1. `platformio.ini`
```ini
[env:esp32dev]
platform = espressif32@6.9.0      ; core Arduino 2.x (tuong thich audio lib 2.0.6)
board = esp32dev
framework = arduino
monitor_speed = 115200
board_build.partitions = partitions.csv
board_build.filesystem = littlefs
lib_deps =
    olikraus/U8g2@^2.35.9                                  ; ve OLED
    https://github.com/ricmoo/QRCode.git                  ; sinh ma QR
    https://github.com/schreibfaul1/ESP32-audioI2S.git#2.0.6  ; phat MP3 qua I2S
```
> `platform@6.9.0` khoa core Arduino 2.x. Audio lib pin `#2.0.6` de tuong thich. Khong
> nen nang tuy tien vi audio lib doi API giua cac major version.

### 6.2. `partitions.csv`
Chia flash 4MB: app (factory) ~1.75MB + LittleFS ~2.19MB cho MP3.

### 6.3. `main.cpp` - vong lap chinh (Dual-Core)
- `setup()`: Khởi tạo phần cứng -> Khởi tạo `sync_state` -> Tạo `NetworkTask` chạy ngầm trên **Core 0** -> Luồng `loop()` chính thức chạy độc lập trên **Core 1**.
- `loop()` (Core 1):
  1. `audio_loop()` luôn chạy để bom dữ liệu âm thanh số (đảm bảo không bao giờ trễ tiếng).
  2. Nếu đang hiện màn "THANH CONG": chờ >= 4s và loa đọc xong mới quay về.
  3. Lấy sự kiện đã thanh toán từ `paid-event` queue: hiển thị "THANH CONG" + phát loa.
  4. Theo dõi WiFi (`g_wifi_connected`) để vẽ trạng thái thích hợp.
  5. Lấy thông tin đơn hàng hiện tại từ `sync_state` bằng cơ chế loại trừ tương hỗ (Mutex) -> hiển thị QR Code (Zoom x2).

### 6.4. `oled_ui.cpp` - hien thi
- Dung U8g2 full frame buffer (ESP32 du RAM).
- `oled_show_qr()`: sinh QR tu link rut gon cua PayOS (`https://.../q/{no}`).
  - Chuyển URL sang dạng in hoa để tự động kích hoạt **Alphanumeric Mode** giúp tối ưu hóa số lượng ô vuông (giảm xuống Version 3 - 29x29 ô vuông).
  - Tự động phóng to lên **`scale = 2`** (58x58 pixel) giúp quét cực kỳ nhạy và nét trên OLED 64px.
  - Ben phai QR hien chu "QUET BANG: CAMERA/ZALO", so thu tu `#n`, so tien.
- `oled_message()`: man hinh 1-2 dong can giua (San sang / Khoi dong...).
- `oled_show_paid()`: man "THANH CONG" + so don + so tien.

### 6.5. `audio_vn.cpp` - doc so tien
Xem chi tiet o `05-doc-so-tien.md`. Tom tat:
- Mount LittleFS, cau hinh I2S (chan 26/27/25), volume.
- `audio_announce_amount(amount)`: tach so tien thanh trieu/nghin/tram/chuc/donvi, day ten
  file MP3 vao mot hang doi, phat lan luot. Khi 1 file phat xong (`audio_eof_mp3`) thi
  chuyen file ke tiep.

### 6.6. `net_client.cpp` - mang
- `net_init()`: khởi tạo luồng kết nối WiFi STA (không chặn tiến trình khởi động).
- `http_get()`: thực hiện gọi HTTP thô sơ và tối giản để tránh gây tốn bộ nhớ Stack của hệ thống mạng.
- Parse JSON **thu cong** (khong dung ArduinoJson) bang cac ham `json_str/json_num/json_bool`
  vi du lieu backend don gian, co dinh key. Giam phu thuoc thu vien.

### 6.7. `sync_state.cpp` - Dong bo hoa chia se du lieu (Core 0 <-> Core 1)
- **Mutex (`g_current_mutex`)**: Đảm bảo an toàn luồng dữ liệu khi đọc và viết thông tin đơn hàng hiện tại `CurrentState` (tránh hiện tượng tranh chấp bộ nhớ khi copy chuỗi QR Code).
- **Queue (`g_paid_queue`)**: Hàng đợi FreeRTOS dài 8 phần tử, dùng để lưu trữ các sự kiện thanh toán thành công được nhận về từ NetworkTask (Core 0) và truyền an toàn sang Core 1 xử lý đọc loa, tránh mất mát sự kiện.
- **`g_wifi_connected`**: Biến kiểu nguyên thủy (`volatile bool`) thể hiện trạng thái kết nối WiFi thời gian thực của thiết bị.
- `net_get_current()`, `net_get_paid_event()`: bao state ve cho main.

## 7. Tuy chinh thuong gap

| Muon | Sua o dau |
|------|-----------|
| Doi WiFi / server | `config.h`: WIFI_SSID, WIFI_PASS, SERVER_BASE_URL |
| Loa to/nho hon | `config.h`: AUDIO_VOLUME (0..21) |
| Poll nhanh/cham hon | `config.h`: POLL_CURRENT_MS, POLL_PAID_MS |
| Doi chan I2S/I2C | `config.h` + dau lai day |
| Man "THANH CONG" lau hon | `main.cpp`: `paid_until = now + 4000` (ms) |

## 8. Nap thuong gap loi

| Loi | Nguyen nhan | Khac phuc |
|-----|-------------|-----------|
| `Wrong boot mode detected` | Board CH340 khong tu vao boot | Noi chan AR/IO0 -> GND, nhan RESET, nap, roi thao day |
| `Failed to connect` | Sai cong COM | `pio device list`, chon dung COM |
| OLED trang/khong hien | Sai I2C / dia chi | Quet I2C, kiem tra SDA=21 SCL=22 |
| Loa cau xong nhung khong doc | Chua `uploadfs` | Chay `pio run -t uploadfs` truoc |