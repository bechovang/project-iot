# Smart QR Payment (PayOS) - ESP32 + OLED + Loa

He thong thanh toan QR cho quan nho (kieu quan cafe):

> **Tai lieu chi tiet day du nam trong thu muc [`docs/`](docs/README.md)** - gom tong quan,
> phan cung, server, firmware, PayOS/webhook/deploy, engine doc so tien, va van hanh/su co.
> File README nay chi la huong dan nhanh.

- **ESP32 + OLED SH1106**: hien QR PayOS de khach quet.
- **Loa MAX98357A**: doc to so tien khi thanh toan thanh cong ("da nhan duoc muoi mot nghin dong").
- **Server Python**:
  - `app.py` (FastAPI): nao - tao link PayOS, nhan **webhook**, phuc vu ESP32 + trang TV.
  - `cashier.py` (Streamlit): quay thu ngan - chon mon / nhap tien -> tao don.
  - Trang **/tv**: man hinh chieu cho khach xem hang doi don.

```
[ESP32 + OLED + Loa]  --WiFi LAN-->  [Server (PC/VPS)]  --Internet-->  [PayOS]
   hien QR / doc tien      REST/poll      FastAPI + Streamlit     webhook PAID
```

## Luong hoat dong
1. Thu ngan tao don tren Streamlit -> backend goi PayOS lay `qrCode` + `orderCode`.
2. ESP32 poll `GET /api/device/current` -> ve QR len OLED.
3. Khach quet & thanh toan -> PayOS goi **webhook** `POST /api/payment/payos-webhook`.
4. Backend verify chu ky -> danh dau don PAID.
5. ESP32 poll `GET /api/device/paid-event` -> phat loa doc so tien + OLED "THANH CONG".

---

## A. Chay Server

### 1. Cai dat
```powershell
cd version1\server
py -3.11 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```
> PayOS SDK 0.1.4 yeu cau Python < 3.11.5. Code goi PayOS qua REST truc tiep
> (chi muon ham ky chu ky tu SDK) nen mien nhiem khi PayOS them field moi.

### 2. Cau hinh
Copy `.env.example` -> `.env` va dien key PayOS:
```
PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...
PUBLIC_BASE_URL=https://your-public-url   # URL cong khai backend (VPS / cloudflare tunnel)
API_TOKEN=                                # tuy chon, bao ve API tao don
BACKEND_URL=http://127.0.0.1:8000
```

### 3. Chay backend (FastAPI)
```powershell
.\venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 8000
```
- TV cho khach:  `http://<IP-PC>:8000/tv`
- API cho ESP32: `http://<IP-PC>:8000/api/device/current`

### 4. Chay quay thu ngan (Streamlit) - cua so khac
```powershell
.\venv\Scripts\activate
streamlit run cashier.py
```

### 5. Webhook cong khai
PayOS can goi vao `PUBLIC_BASE_URL/api/payment/payos-webhook`.
- Demo nhanh: `cloudflared tunnel --url http://localhost:8000`
- Production: deploy len VPS (DigitalOcean...) co domain/IP cong khai.

Dang ky webhook url tren trang my.payos.vn (hoac dung API confirm-webhook).
URL webhook day du:  `https://<public>/api/payment/payos-webhook`

---

## B. Nap Firmware ESP32

### 1. Cau hinh `firmware/include/config.h`
```c
#define WIFI_SSID       "TenWifi"
#define WIFI_PASS       "MatKhau"
#define SERVER_BASE_URL "http://192.168.1.50:8000"   // IP PC chay backend trong LAN
```

### 2. Dau day
**OLED SH1106 (I2C):** VCC->3V3, GND->GND, SDA->GPIO21, SCL->GPIO22

**Loa MAX98357A (I2S):**
| MAX98357A | ESP32 |
|-----------|-------|
| VIN  | 3V3 (hoac 5V to hon) |
| GND  | GND |
| GAIN | GND |
| DIN  | GPIO25 |
| BCLK | GPIO26 |
| LRC  | GPIO27 |
| SD   | de trong |

### 3. Nap
```powershell
cd version1\firmware
# Nap file am thanh (LittleFS) - chi can lam 1 lan / khi doi file
pio run -t uploadfs
# Nap firmware
pio run -t upload
# Xem log
pio device monitor -b 115200
```

---

## C. Doc so tien (loa)

`firmware/data/` chua cac file MP3 tieng Viet: `mot..chin, muoi_10, muoi, tram, nghin_dong, da_nhan_duoc`.
Engine `audio_vn.cpp` tu ghep cau cho so tien bat ky.

**Doc tot:** so tien la boi so 1.000, duoi 1 trieu (vd 11.000, 35.000, 250.000).

**De doc chuan hon cac so dac biet**, them cac file MP3 (tuy chon) vao `firmware/data/`:
- `lam.mp3` ("lam") - cho duoi 5 sau hang chuc: 25 = "hai muoi **lam**"
- `mot2.mp3` ("mot") - cho duoi 1 sau hang chuc: 21 = "hai muoi **mot**"
- `le.mp3` ("le") - 105.000 = "mot tram **le** nam nghin"
- `nghin.mp3`, `trieu.mp3`, `khong.mp3`

Khong co cac file nay van chay duoc (fallback gan dung).

---

## D. API tham khao
| Method | Path | Mo ta |
|--------|------|-------|
| POST | `/api/orders` | Tao don (body: amount, description, items) |
| GET  | `/api/orders` | Danh sach don |
| POST | `/api/orders/{code}/cancel` | Huy don |
| POST | `/api/payment/payos-webhook` | Webhook PayOS goi vao |
| GET  | `/api/device/current` | ESP32: don dang cho hien QR |
| GET  | `/api/device/paid-event` | ESP32: don vua PAID (tra 1 lan) |
| GET  | `/tv` | Trang TV hang doi |

## Ghi chu / Han che ban v1
- Don luu trong **SQLite** (orders.db, tu tao). Ben vung qua restart backend. queue_no reset moi ngay.
- `description` PayOS gioi han 25 ky tu (da tu cat).
- QR ve len OLED 64px o ti le 1px/module - quet o khoang cach gan. Muon de quet hon co the dung OLED to hon hoac hien QR tren trang TV.