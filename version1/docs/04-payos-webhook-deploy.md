# 04 - PayOS, Webhook & Deploy

## 1. PayOS la gi

PayOS la cong thanh toan cho phep tao **link/ma QR** thanh toan chuyen khoan ngan hang.
Khach quet QR bang app ngan hang -> chuyen tien -> PayOS bao ket qua ve he thong cua ban
qua **webhook**.

Tai lieu: https://payos.vn | Bang dieu khien: https://my.payos.vn

## 2. Lay thong tin tich hop

Tren my.payos.vn -> tao **Kenh thanh toan** -> lay 3 khoa:

| Khoa | Dung de |
|------|---------|
| Client ID | Dinh danh kenh |
| API Key | Goi API |
| Checksum Key | Ky chu ky khi tao QR + verify webhook |

Dien vao `server/.env` (xem `02-server.md`).

## 3. Co che chu ky (signature)

PayOS dung **HMAC_SHA256** voi `checksum_key`.

### 3.1. Khi TAO link thanh toan
Chuoi ky duoc sap theo thu tu alphabet co dinh:
```
amount=$amount&cancelUrl=$cancelUrl&description=$description&orderCode=$orderCode&returnUrl=$returnUrl
```
`signature = HMAC_SHA256(chuoi_tren, checksum_key)`

`payos_client.create_payment()` tu tao chu ky nay truoc khi POST.

### 3.2. Khi NHAN webhook
PayOS gui `{code, desc, success, data:{...}, signature}`.
Cach verify (trong `payos_client.verify_webhook`):
1. Lay `data`, sap xep cac key theo alphabet.
2. Noi thanh chuoi `key1=value1&key2=value2&...` (gia tri None -> rong).
3. `HMAC_SHA256(chuoi, checksum_key)` phai bang `signature` nhan duoc.
4. Khop -> du lieu tin cay -> mark_paid. Khong khop -> tu choi (400).

> Day la lop bao ve quan trong: chi PayOS (giu checksum key) moi tao duoc chu ky dung,
> nen khong ai gia mao "da thanh toan" duoc.

## 4. Vi sao goi PayOS qua REST truc tiep (khong dung wrapper SDK)

SDK `payos==0.1.4` parse response bang dataclass co dinh truong. PayOS production hien tra
them truong moi (vd `expiredAt`), khien `CreatePaymentResult(**data)` bao loi:
```
TypeError: CreatePaymentResult.__init__() got an unexpected keyword argument 'expiredAt'
```
Vi vay `payos_client.py`:
- **Goi REST** (`requests`) toi `https://api-merchant.payos.vn/v2/payment-requests` -> doc
  truc tiep JSON, chi lay truong can (qrCode, checkoutUrl, orderCode, paymentLinkId). Them
  truong moi khong gay vo.
- **Tai dung** ham ky chu ky chuan tu `payos.utils` de dam bao thuat toan dung.

## 5. Webhook - duong cong khai

PayOS o ngoai Internet, can goi vao `POST <PUBLIC_BASE_URL>/api/payment/payos-webhook`.
Backend chay LAN khong co dia chi cong khai -> can mot trong hai:

### 5.1. Cloudflare Tunnel (nhanh, mien phi, cho demo/dev)
```powershell
# Cai cloudflared (https://github.com/cloudflare/cloudflared)
cloudflared tunnel --url http://localhost:8000
```
Se in ra mot URL dang `https://abc-xyz.trycloudflare.com`. Dat URL nay vao `PUBLIC_BASE_URL`
trong `.env` (khong co `/` cuoi), restart backend.

> URL trycloudflare doi moi lan chay. Moi lan doi phai cap nhat `.env` va dang ky lai webhook.

### 5.2. Ngrok Tunnel (ổn định hơn Cloudflare khi dev, hỗ trợ static domain miễn phí)
```powershell
# Chạy ngrok trỏ tới port 8000 của backend (sử dụng domain tĩnh miễn phí nếu có)
ngrok http 8000 --domain sciatic-cristi-tearfully.ngrok-free.dev
```
Đặt URL ngrok tĩnh này vào `PUBLIC_BASE_URL` trong `.env` (không có `/` cuối), khởi động lại backend.

> ⚠️ **Lưu ý quan trọng cho ESP32:** Mặc định ngrok free sẽ tự động chuyển hướng mọi yêu cầu HTTP sang HTTPS. Việc này có thể khiến ESP32 bị lỗi `SSL - The connection indicated an EOF` (lỗi handshake do cấu hình mã hóa ngrok quá mới so với mbedTLS cũ trên ESP32). Để khắc phục, bạn có thể cấu hình tắt chuyển hướng HTTPS trên Dashboard ngrok hoặc dùng giải pháp LocalTunnel bên dưới.

### 5.3. LocalTunnel (Khuyên dùng cho ESP32 - Tên miền cố định miễn phí & Hỗ trợ HTTP)
LocalTunnel cho phép tự cấu hình Subdomain cố định và hỗ trợ kết nối trực tiếp bằng giao thức HTTP thường (không bị tự động chuyển sang HTTPS), giúp ESP32 kết nối rất nhẹ và không bị lỗi SSL.

Chạy lệnh (cần cài đặt NodeJS):
```powershell
npx localtunnel --port 8000 --subdomain bechovang
```
Lấy URL nhận được dạng `http://bechovang.loca.lt` (hoặc cấu hình tên miền tùy chỉnh của bạn) để điền vào `SERVER_BASE_URL` của ESP32 và `PUBLIC_BASE_URL` trong file `.env` của backend.

### 5.4. VPS (ổn định, cho production - vd DigitalOcean)
- Tạo Droplet (Ubuntu), mở port 80/443.
- Cài Python, clone code, chạy backend (xem mục 7).
- Trỏ domain về IP VPS, bật HTTPS (Caddy/Nginx + Let's Encrypt).
- `PUBLIC_BASE_URL=https://your-domain.com`.

## 6. Dang ky Webhook URL voi PayOS

URL webhook day du:
```
https://<public>/api/payment/payos-webhook
```

Cach 1 - Tren my.payos.vn: vao kenh thanh toan -> muc Webhook -> dan URL -> Luu. PayOS se gui
1 request thu de xac thuc; backend tra 200 la dat.

Cach 2 - Qua API (PayOS SDK co `confirmWebhook`), neu muon tu dong.

> Backend da xu ly request thu nghiem cua PayOS (description "Ma giao dich thu nghiem" /
> "VQRIO123") -> tra 200 ma khong tao don gia.

## 7. Trien khai backend tren VPS (vi du Ubuntu)

```bash
# 1. Cai Python + venv
sudo apt update && sudo apt install -y python3.11 python3.11-venv git

# 2. Lay code
git clone <repo> && cd version1/server
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Cau hinh .env (dien key + PUBLIC_BASE_URL = domain VPS)
cp .env.example .env && nano .env

# 4. Chay (tam thoi)
uvicorn app:app --host 0.0.0.0 --port 8000

# 5. Chay nen lau dai: dung systemd hoac pm2/supervisor
```

Vi du service systemd `/etc/systemd/system/smartqr.service`:
```ini
[Unit]
Description=Smart QR Backend
After=network.target

[Service]
WorkingDirectory=/root/version1/server
ExecStart=/root/version1/server/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now smartqr
```

> Tren VPS cong khai: BAT BUOC dat `API_TOKEN` trong `.env` de bao ve API tao/huy don, va
> nen dat sau HTTPS. Webhook van an toan nho verify chu ky.

## 8. Kiem thu PayOS doc lap

Tao 1 link that tu CLI de kiem tra key:
```powershell
cd version1\server
.\venv\Scripts\python.exe -c "import payos_client as p; r=p.create_payment(2000,'Test',[{'name':'Test','quantity':1,'price':2000}]); print(r['checkout_url']); print('qr len', len(r['qr_code']))"
```
Mo `checkout_url` tren trinh duyet -> thay trang QR PayOS la key dung.

## 9. Luu y so tien & mo ta

- `amount` la **VND**, so nguyen (vd 11000 = 11.000d).
- `description` PayOS gioi han **25 ky tu** voi tai khoan ngan hang thuong -> code tu cat bot.
- `orderCode` phai la so nguyen duy nhat -> sinh tu `timestamp*100 + random` trong `gen_order_code()`.