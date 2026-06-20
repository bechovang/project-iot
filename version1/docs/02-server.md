# 02 - Server (Backend FastAPI + Cashier Streamlit)

## 1. Yeu cau moi truong

- **Python 3.11.x** (khuyen nghi 3.11.0 - 3.11.4). PayOS SDK 0.1.4 dinh kem co rang buoc
  Python < 3.11.5, nhung code nay goi PayOS qua REST truc tiep nen Python 3.11.9 van chay tot
  (da kiem thu). Tranh Python 3.13 vi mot so phu thuoc co the chua co wheel.
- Ket noi Internet (de goi PayOS).
- Windows / Linux / macOS deu chay duoc.

## 2. Cai dat

```powershell
cd version1\server
py -3.11 -m venv venv
.\venv\Scripts\activate            # Windows
# source venv/bin/activate          # Linux/macOS
pip install -r requirements.txt
```

`requirements.txt`:

```
fastapi==0.110.0
uvicorn[standard]==0.29.0
python-dotenv==1.0.1
requests==2.31.0
streamlit==1.33.0
payos==0.1.4
```

> Vi sao van cai `payos==0.1.4` du goi REST truc tiep? Vi `payos_client.py` tai dung
> ham ky chu ky chuan tu `payos.utils` (`createSignatureFromObj`). Day la phan "loi" da
> dung thuat toan HMAC_SHA256, ta khong viet lai de tranh sai sot.

## 3. Cau hinh `.env`

Copy `.env.example` thanh `.env` roi dien:

```
PAYOS_CLIENT_ID=<client id tu my.payos.vn>
PAYOS_API_KEY=<api key>
PAYOS_CHECKSUM_KEY=<checksum key>

# URL cong khai cua backend (cloudflare tunnel / VPS). KHONG co dau / o cuoi.
PUBLIC_BASE_URL=https://your-public-url

# Token bao ve API ghi (tao don / huy don). De trong = TAT bao ve (chi dung trong LAN demo).
API_TOKEN=

# Backend cho Streamlit cashier goi vao
BACKEND_URL=http://127.0.0.1:8000
```

| Bien | Bat buoc | Y nghia |
|------|----------|---------|
| `PAYOS_CLIENT_ID` | Co | Dinh danh kenh thanh toan PayOS |
| `PAYOS_API_KEY` | Co | Khoa goi API PayOS |
| `PAYOS_CHECKSUM_KEY` | Co | Khoa ky/verify chu ky (tao QR + webhook) |
| `PUBLIC_BASE_URL` | Nen co | Dung lam `returnUrl`/`cancelUrl`. Webhook cung tro vao day |
| `API_TOKEN` | Tuy chon | Neu dat, moi request tao/huy don phai gui header `x-api-token` |
| `BACKEND_URL` | Co (cho cashier) | Streamlit goi vao backend |

> File `.env` da duoc gitignore -> khong bi commit len git. Tuyet doi khong chia se key.

## 4. Chay backend (FastAPI)

```powershell
.\venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0`: cho phep ESP32 va may khac trong LAN truy cap (khong chi localhost).
- TV cho khach:  `http://<IP-PC>:8000/tv`
- Tai lieu API tu dong (Swagger):  `http://<IP-PC>:8000/docs`

Tim IP LAN cua PC:
```powershell
ipconfig    # xem dong IPv4 Address, vd 192.168.1.50
```

## 5. Chay quay thu ngan (Streamlit)

Mo cua so terminal thu hai:

```powershell
cd version1\server
.\venv\Scripts\activate
streamlit run cashier.py
```

Trinh duyet tu mo `http://localhost:8501`. Giao dien:
- Cot trai: chon mon tu menu (co san) hoac nhap so tien tu do -> bam **TAO DON & QR** -> hien QR.
- Cot phai: danh sach don, trang thai PAID/PENDING/CANCELLED, nut Huy cho don PENDING.

Menu mau (sua trong `cashier.py`, bien `MENU`):
```python
MENU = {
    "Ca phe den": 15000,
    "Ca phe sua": 20000,
    "Bac xiu": 25000,
    "Tra dao": 30000,
    "Tra sua tran chau": 35000,
    "Banh mi": 20000,
}
```

## 6. Cac file server

| File | Vai tro |
|------|---------|
| `app.py` | FastAPI: API tao/huy/list don, webhook PayOS, API cho ESP32, trang TV |
| `cashier.py` | Streamlit: quay thu ngan |
| `payos_client.py` | Goi PayOS REST (tao link, get status, cancel, verify webhook) |
| `store.py` | Luu don bang SQLite (`orders.db`) |
| `requirements.txt` | Danh sach thu vien |
| `.env` / `.env.example` | Cau hinh |

## 7. API Reference (backend)

Base URL: `http://<host>:8000`

### 7.1. Tao don
```
POST /api/orders
Header (neu dat API_TOKEN): x-api-token: <token>
Body JSON:
{
  "amount": 11000,
  "description": "Don Ca phe sua x1",
  "items": [{"name":"Ca phe sua","quantity":1,"price":11000}]
}
```
Response 200:
```json
{
  "order_code": 178188490811,
  "queue_no": 1,
  "amount": 11000,
  "description": "Don Ca phe sua x1",
  "items": [{"name":"Ca phe sua","quantity":1,"price":11000}],
  "qr_code": "00020101021238540010A0000007270124...",
  "checkout_url": "https://pay.payos.vn/web/....",
  "payment_link_id": "84c8036178774e4d8143328d9e9d4d69",
  "status": "PENDING",
  "created_at": 1750000000.0,
  "paid_at": null
}
```
Loi:
- `400` amount <= 0
- `401` sai API token (neu bat)
- `502` PayOS loi (vd sai key, het han)

### 7.2. Danh sach don
```
GET /api/orders
```
Tra ve mang cac don, moi nhat truoc.

### 7.3. Chi tiet 1 don
```
GET /api/orders/{order_code}
```
`404` neu khong tim thay.

### 7.4. Huy don
```
POST /api/orders/{order_code}/cancel
Header (neu dat): x-api-token
```
Goi PayOS huy link + set status=CANCELLED.

### 7.5. Webhook PayOS (PayOS goi vao, khong goi tay)
```
POST /api/payment/payos-webhook
Body: payload PayOS (co "data" + "signature")
```
- Backend verify chu ky bang checksum key.
- Chu ky sai -> `400`.
- Hop le va don ton tai -> mark_paid.
- Giao dich thu nghiem ("Ma giao dich thu nghiem"/"VQRIO123") -> bo qua, tra 200.

### 7.6. ESP32: don dang cho hien QR
```
GET /api/device/current
```
Khi co don PENDING:
```json
{"has_order": true, "order_code": 178..., "amount": 11000,
 "qr_code": "https://<PUBLIC_BASE_URL>/q/1", "queue_no": 1}
```
*Lưu ý: `qr_code` đã được đổi thành đường dẫn rút gọn của Backend để hỗ trợ hiển thị QR thưa hạt (Zoom x2) trên màn hình OLED.*

Khong co don:
```json
{"has_order": false}
```

### 7.6b. Redirect link rút gọn
```
GET /q/{queue_no}
GET /Q/{queue_no}
```
*Tự động chuyển hướng (HTTP 302 Redirect) điện thoại của khách hàng sang trang thanh toán thực tế của PayOS (checkout_url).*
*(Hỗ trợ cả ký tự thường /q/ và chữ hoa /Q/ do ESP32 tự động viết hoa toàn bộ chuỗi QR).*

### 7.7. ESP32: su kien vua thanh toan (tra 1 lan)
```
GET /api/device/paid-event
```
Co don vua PAID (lan dau goi sau khi PAID):
```json
{"paid": true, "order_code": 178..., "amount": 11000, "queue_no": 1}
```
Da lay roi / chua co:
```json
{"paid": false}
```
> Co che 1 lan: backend dung cot `paid_event_pending` trong SQLite. Sau khi tra ve thi
> reset co -> ESP32 khong bi doc loa lap lai.

### 7.8. Trang dieu huong sau thanh toan (PayOS redirect)
```
GET /paid        -> trang "Thanh toan thanh cong"
GET /cancelled   -> trang "Da huy"
```

### 7.9. Trang TV
```
GET /tv
```
Trang HTML tu refresh moi 2s, hien cac the don voi so thu tu + so tien + trang thai.

## 8. Luu tru don (SQLite)

- File `orders.db` tu tao trong thu muc `server/` (da gitignore).
- Bang `orders` gom: `order_code` (khoa chinh), `queue_no`, `amount`, `description`,
  `items` (JSON), `qr_code`, `checkout_url`, `payment_link_id`, `status`,
  `created_at`, `paid_at`, `paid_event_pending`.
- `queue_no` dem so don **trong ngay** (reset moi ngay).
- Du lieu **ben vung qua restart** backend.
- Doi vi tri DB: dat bien moi truong `ORDERS_DB=/duong/dan/khac.db`.

Xem nhanh DB bang Python:
```powershell
.\venv\Scripts\python.exe -c "import store; print(store.store.list())"
```

Xoa toan bo don (lam moi demo): dung backend, xoa file `orders.db`, chay lai.

## 9. Bao mat

- `.env` chua key PayOS - khong commit, khong chia se.
- Mac dinh `API_TOKEN` rong -> API tao/huy don **khong yeu cau xac thuc**. Chap nhan duoc
  khi backend chi mo trong LAN. Neu deploy cong khai (VPS), **hay dat `API_TOKEN`** va cau
  hinh `x-api-token` tuong ung ben Streamlit (qua `.env` `API_TOKEN`).
- Endpoint webhook `/api/payment/payos-webhook` luon verify chu ky -> ke gia mao khong the
  danh dau don PAID neu khong co checksum key.
- Khi cong khai, nen dat backend sau HTTPS (cloudflare tunnel / reverse proxy tren VPS).