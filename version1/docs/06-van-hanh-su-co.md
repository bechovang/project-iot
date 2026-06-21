# 06 - Van hanh & Xu ly su co

## 1. Quy trinh chay hang ngay

1. **Bat backend** (PC hoac VPS):
   ```powershell
   cd version1\server
   .\venv\Scripts\activate
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
2. **Bat tunnel/VPS** de webhook cong khai hoat dong (neu chay LAN: cloudflared).
   Cap nhat `PUBLIC_BASE_URL` neu URL doi, dang ky lai webhook tren my.payos.vn.
3. **Bat quay thu ngan**:
   ```powershell
   streamlit run cashier.py
   ```
4. **Bat man hinh TV** (trinh duyet): `http://<IP>:8000/tv`
5. **Cap nguon ESP32** -> doi log "San sang".

## 2. Quy trinh ban 1 don

1. Thu ngan chon mon / nhap tien -> **TAO DON & QR**.
2. ESP32 hien QR len OLED (trong ~1.5s).
3. Khach quet QR, chuyen tien.
4. PayOS bao webhook -> backend mark PAID.
5. ESP32 doc loa so tien + OLED "THANH CONG"; TV doi the don sang xanh "DA THANH TOAN".
6. He thong tu quay ve "San sang" cho don sau.

## 3. Checklist truoc khi mo ban

- [ ] Backend chay, mo duoc `http://<IP>:8000/docs`
- [ ] `.env` dien dung 3 khoa PayOS + `PUBLIC_BASE_URL`
- [ ] Webhook da dang ky va PayOS xac thuc thanh cong
- [ ] Tao 1 don test 2.000d, quet thu, thay loa doc + TV doi trang thai
- [ ] ESP32 cung WiFi voi PC, `SERVER_BASE_URL` dung IP LAN
- [ ] Loa keu ro, OLED hien QR sac net

## 4. Bang su co thuong gap

### 4.1. Server / PayOS

| Trieu chung | Nguyen nhan | Khac phuc |
|-------------|-------------|-----------|
| Tao don bao `502 PayOS error` | Sai key / het han / mat mang | Kiem tra `.env`, thu lai bang muc 8 doc 04 |
| Webhook khong ve | URL chua dang ky / tunnel tat / sai PUBLIC_BASE_URL | Kiem tra tunnel, dang ky lai webhook, xem log uvicorn |
| Webhook ve nhung don khong PAID | Chu ky sai (sai checksum key) | Doi chieu `PAYOS_CHECKSUM_KEY` voi my.payos.vn |
| `401 Invalid API token` | API_TOKEN dat o backend, cashier khong gui | Dong bo `API_TOKEN` trong `.env` (ca 2 deu doc cung file) |
| Mat het don sau restart | (Khong con xay ra - da dung SQLite) | Kiem tra file `orders.db` co quyen ghi |

### 4.2. ESP32 / mang

| Trieu chung | Nguyen nhan | Khac phuc |
|-------------|-------------|-----------|
| `[NET] WiFi connect FAILED` | Sai SSID/pass, song yeu | Sua `config.h`, lai gan router |
| OLED "WiFi loi" | Khong noi duoc WiFi | Nhu tren |
| ESP32 bị lỗi kết nối SSL / `SSL - The connection indicated an EOF` | Ngrok tự động chuyển hướng sang HTTPS và không tương thích TLS/SSL mbedTLS cũ trên ESP32 | Chuyển sang dùng LocalTunnel (`npx localtunnel --port 8000 --subdomain <tên_miền>`) và trỏ `SERVER_BASE_URL` về `http://<domain>.loca.lt` |
| ESP32 bị khởi động lại liên tục (Reboot/Stack Overflow) | Cấu hình sai QR version gây tràn bộ nhớ Stack, hoặc kích thước ngăn xếp quá nhỏ | Đảm bảo kích thước ngăn xếp `NET_TASK_STACK` tối thiểu là 10KB (10240) và sử dụng kết nối HTTP thường |
| Da thanh toan nhung loa khong doc | Chua `uploadfs` / SD noi GND / sai chan I2S | `pio run -t uploadfs`, kiem tra dau day muc 01 |
| Loa doc lap lai nhieu lan | (Khong nen xay ra) paid-event tra 1 lan | Kiem tra chi 1 ESP32 goi `/api/device/paid-event` |

### 4.3. Firewall Windows (hay gap)

PC chay backend co the chan ket noi tu ESP32. Mo port 8000:
```powershell
New-NetFirewallRule -DisplayName "SmartQR 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

## 5. Kiem thu khong can phan cung that

Mo phong toan bo luong bang script (giong cach da kiem thu khi xay dung):
```powershell
cd version1\server
.\venv\Scripts\activate
# 1) chay backend o terminal khac: uvicorn app:app --port 8000
python - <<'PY'
import requests as r, hmac, hashlib, os
from dotenv import load_dotenv; load_dotenv()
B="http://127.0.0.1:8000"; CK=os.environ["PAYOS_CHECKSUM_KEY"]
o=r.post(B+"/api/orders",json={"amount":11000,"description":"Test","items":[]}).json()
print("order:",o["order_code"],"queue:",o["queue_no"])
print("device/current:",r.get(B+"/api/device/current").json())
def sig(d,k):
    qs="&".join(f"{x}={'' if v is None else v}" for x,v in sorted(d.items()))
    return hmac.new(k.encode(),qs.encode(),hashlib.sha256).hexdigest()
data={"orderCode":o["order_code"],"amount":11000,"description":"Test","accountNumber":"x",
 "reference":"FT1","transactionDateTime":"2026-01-01 00:00:00","paymentLinkId":"x",
 "code":"00","desc":"success","currency":"VND","counterAccountBankId":"",
 "counterAccountBankName":"","counterAccountName":"","counterAccountNumber":"",
 "virtualAccountName":"","virtualAccountNumber":""}
body={"code":"00","desc":"success","success":True,"data":data,"signature":sig(data,CK)}
print("webhook:",r.post(B+"/api/payment/payos-webhook",json=body).status_code)
print("paid-event:",r.get(B+"/api/device/paid-event").json())
PY
```
Ket qua mong doi: tao don OK -> device/current co don -> webhook 200 -> paid-event `paid:true`.

## 6. Sao luu & lam moi du lieu

- Sao luu don: copy file `server/orders.db`.
- Lam moi (xoa het don demo): tat backend -> xoa `orders.db` -> chay lai (tu tao moi).

## 7. Gioi han da biet (ban v1)

- QR ve OLED 64px o ti le 1px/module: quet o khoang cach gan. Muon de quet, dung OLED lon
  hon, hoac cho khach quet QR tren man TV/Streamlit.
- Backend 1 worker (mac dinh) + SQLite + khoa tuyen: du cho 1 quay. Nhieu quay/nhieu worker
  thi nen chuyen sang Postgres + WAL.
- `description` toi da 25 ky tu (gioi han PayOS).
- Doc so tien chuan nhat voi boi so 1.000 duoi 1 trieu (xem `05-doc-so-tien.md`).

## 8. Mo rong goi y (huong phat trien)

- Them in bill/hoa don nhiet.
- Them quan ly mon/menu qua giao dien thay vi sua code.
- Luu lich su doanh thu theo ngay (da co `created_at`, `paid_at` trong DB).
- Nhieu thiet bi OLED cho nhieu quay (tach theo `device_id`).
- WebSocket thay vi poll de realtime hon.