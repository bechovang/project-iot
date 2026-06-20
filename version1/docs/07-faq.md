# 07 - FAQ (Cau hoi thuong gap)

## A. Tong quat

**H: He thong co can Internet khong?**
T: Co. PayOS o ngoai Internet -> server can mang de tao QR va nhan webhook. ESP32 chi can
LAN de noi server (server moi can Internet). Mat mang -> khong tao duoc don moi.

**H: ESP32 co noi thang toi PayOS khong?**
T: Khong. ESP32 chi noi server trong LAN. Server lam viec voi PayOS. Tach vai tro nay giup
giu key PayOS an toan tren server, ESP32 khong giu bi mat gi.

**H: Co dung duoc nhieu quay / nhieu ESP32 khong?**
T: Ban v1 thiet ke cho 1 quay. Nhieu ESP32 cung goi `/api/device/paid-event` se tranh nhau
su kien (chi 1 con nhan duoc). Muon nhieu quay can them `device_id` - xem muc mo rong o
`06-van-hanh-su-co.md`.

## B. PayOS & thanh toan

**H: Tien chay vao dau?**
T: Vao tai khoan ngan hang ban da lien ket tren my.payos.vn. He thong chi tao QR + nhan
thong bao, khong giu tien.

**H: Vi sao khong dung ham createPaymentLink() cua SDK?**
T: SDK 0.1.4 parse response bang dataclass co dinh, PayOS them truong `expiredAt` lam no vo.
Ta goi REST truc tiep + tai dung ham ky chu ky. Chi tiet o `04-payos-webhook-deploy.md` muc 4.

**H: Webhook bao "invalid signature" / don khong chuyen PAID?**
T: Sai `PAYOS_CHECKSUM_KEY`. Doi chieu lai voi my.payos.vn. Chu ky webhook tinh tu checksum
key; sai key -> verify that bai -> tu choi (dung) nhung don khong PAID.

**H: URL trycloudflare doi moi lan chay, phai lam gi?**
T: Moi lan doi phai cap nhat `PUBLIC_BASE_URL` trong `.env`, restart backend, va dang ky lai
webhook url tren my.payos.vn. Muon co dinh -> dung VPS co domain (DigitalOcean).

**H: So tien toi thieu?**
T: PayOS thuong yeu cau >= 1.000d (tuy chinh sach). Mo ta (`description`) toi da 25 ky tu.

**H: Test ma khong mat tien that?**
T: PayOS co giao dich thu nghiem (description "Ma giao dich thu nghiem"/"VQRIO123") -> backend
da bo qua, khong tao don gia. Ngoai ra co the mo phong webhook bang script o `06` muc 5.

## C. Phan cung

**H: Loa khong keu?**
T: Theo thu tu: (1) da chay `pio run -t uploadfs` chua? (2) chan SD co bi noi GND khong (phai
de trong)? (3) dau day DIN/BCLK/LRC dung 25/26/27? (4) cap nguon du khoe? Xem `01` + `06`.

**H: OLED trang tron / khong hien?**
T: Quet I2C (sketch test) xem co dia chi 0x3C. Kiem tra SDA=21, SCL=22, nguon 3V3. Mot so
module dung dia chi 0x3D.

**H: Dien thoai kho quet QR tren OLED?**
T: QR ve 1px/module tren man 64px nen nho. Lai gan, tang sang, lau man. Hoac cho khach quet
QR hien tren man TV (`/tv` co the bo sung hien QR) hoac tren Streamlit.

**H: Board nap khong duoc / "Wrong boot mode"?**
T: Board CH340 thuong phai noi chan IO0/AR -> GND, nhan RESET, nap, roi thao day. Xem
`03-firmware.md` muc 8.

**H: Dung board ESP32 khac (chan ghi D4/D5/D6)?**
T: Doi chieu bang GPIO o `01-phan-cung.md` muc 6. Hoac doi so chan trong `config.h` cho khop.

## D. Server & du lieu

**H: Don co mat khi tat server khong?**
T: Khong. Da dung SQLite (`orders.db`). Restart van con. Muon xoa sach -> tat server, xoa file
`orders.db`, chay lai.

**H: So thu tu don (queue_no) co reset khong?**
T: Co, reset moi ngay (dem so don trong ngay). Hop voi mo hinh quan.

**H: Streamlit bao khong goi duoc backend?**
T: Kiem tra backend dang chay, `BACKEND_URL` trong `.env` dung (mac dinh
http://127.0.0.1:8000). Neu khac may, dung IP LAN + mo firewall port 8000.

**H: Lam sao xem cac don bang dong lenh?**
T: `\.venv\Scripts\python.exe -c "import store; print(store.store.list())"`

**H: Co can MySQL nhu demo Django goc khong?**
T: Khong. Demo Django dung MySQL; ban nay don gian hoa bang SQLite, khong can cai DB rieng.

## E. Tuy chinh

**H: Doi menu mon / gia?**
T: Sua bien `MENU` trong `cashier.py`.

**H: Doi am luong loa?**
T: `AUDIO_VOLUME` trong `config.h` (0..21).

**H: Doc so tien chuan hon (25, 21, 105 nghin)?**
T: Them file MP3 tuy chon (`lam.mp3`, `mot2.mp3`, `le.mp3`...) vao `firmware/data/` roi
`pio run -t uploadfs`. Xem `05-doc-so-tien.md`.

**H: Man "THANH CONG" hien lau hon?**
T: Sua `paid_until = now + 4000` (ms) trong `main.cpp`.

**H: Poll nhanh hon cho do tre thap?**
T: Giam `POLL_CURRENT_MS` / `POLL_PAID_MS` trong `config.h` (vd 800). Danh doi: nhieu request
hon. 1500ms la can bang tot.

## F. Bao mat

**H: Deploy len VPS co an toan khong?**
T: Can: (1) dat `API_TOKEN` de bao ve API tao/huy don; (2) chay sau HTTPS; (3) khong commit
`.env`. Webhook luon verify chu ky nen khong gia mao PAID duoc. Xem `02` muc 9 + `04` muc 7.

**H: Lo key PayOS thi sao?**
T: Vao my.payos.vn thu hoi / tao lai key, cap nhat `.env`. Vi `.env` da gitignore nen khong
bi day len git, nhung van phai giu may chu/VPS an toan.