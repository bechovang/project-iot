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
- `SERVER_BASE_URL` la `http://<IP-LAN-cua-PC>:8000`, KHONG phai URL cong khai PayOS.

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
```
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
│   ├─ config.h
│   ├─ oled_ui.h
│   ├─ audio_vn.h
│   └─ net_client.h
├─ src/                <- trien khai
│   ├─ main.cpp        <- vong lap chinh, dieu phoi
│   ├─ oled_ui.cpp     <- ve QR + man hinh OLED
│   ├─ audio_vn.cpp    <- doc so tien tieng Viet
│   └─ net_client.cpp  <- WiFi + HTTP poll + parse JSON
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

### 6.3. `main.cpp` - vong lap chinh
- `setup()`: init OLED -> init audio (mount LittleFS + I2S) -> noi WiFi -> hien "San sang".
- `loop()`:
  1. `audio_loop()` luon chay (bom du lieu MP3).
  2. Neu dang hien man "THANH CONG": cho >= 4s va loa doc xong moi quay ve.
  3. Poll `/api/device/paid-event`: co don PAID -> hien "THANH CONG" + doc loa.
  4. Poll `/api/device/current`: co don PENDING -> ve QR (chi ve lai khi QR doi).

Trang thai noi bo:
- `showing_qr`: dang hien QR.
- `showing_paid` + `paid_until`: dang hien man thanh cong den thoi diem nao.

### 6.4. `oled_ui.cpp` - hien thi
- Dung U8g2 full frame buffer (ESP32 du RAM).
- `oled_show_qr()`: sinh QR tu chuoi EMVCo cua PayOS bang thu vien QRCode.
  - Chon QR version theo do dai chuoi (8..11). PayOS thuong ~129 ky tu -> version 8 (49x49).
  - Ve 1 pixel / 1 module -> 49..61 px, vua chieu cao OLED 64px.
  - Ben phai QR hien "QUET QR", so thu tu `#n`, so tien.
- `oled_message()`: man hinh 1-2 dong can giua (San sang / Khoi dong...).
- `oled_show_paid()`: man "THANH CONG" + so don + so tien.

### 6.5. `audio_vn.cpp` - doc so tien
Xem chi tiet o `05-doc-so-tien.md`. Tom tat:
- Mount LittleFS, cau hinh I2S (chan 26/27/25), volume.
- `audio_announce_amount(amount)`: tach so tien thanh trieu/nghin/tram/chuc/donvi, day ten
  file MP3 vao mot hang doi, phat lan luot. Khi 1 file phat xong (`audio_eof_mp3`) thi
  chuyen file ke tiep.

### 6.6. `net_client.cpp` - mang
- `net_init()`: noi WiFi STA (timeout 20s).
- `http_get()`: GET 1 endpoint, tra ve body chuoi.
- Parse JSON **thu cong** (khong dung ArduinoJson) bang cac ham `json_str/json_num/json_bool`
  vi du lieu backend don gian, co dinh key. Giam phu thuoc thu vien.
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