# Tai lieu chi tiet - Smart QR Payment

Bo tai lieu day du cho he thong thanh toan QR (ESP32 + OLED + Loa + PayOS).
Doc theo thu tu de hieu tu tong quan den chi tiet.

| # | Tai lieu | Noi dung |
|---|----------|----------|
| 00 | [00-tong-quan.md](00-tong-quan.md) | He thong lam gi, kien truc, luong hoat dong, cau truc thu muc |
| 01 | [01-phan-cung.md](01-phan-cung.md) | Linh kien, so do chan, dau day OLED + loa, kiem tra phan cung |
| 02 | [02-server.md](02-server.md) | Cai dat, chay backend + cashier, API reference, SQLite, bao mat |
| 03 | [03-firmware.md](03-firmware.md) | Cau hinh, build, nap ESP32, giai thich tung module code |
| 04 | [04-payos-webhook-deploy.md](04-payos-webhook-deploy.md) | PayOS, chu ky, webhook, deploy cloudflare/VPS |
| 05 | [05-doc-so-tien.md](05-doc-so-tien.md) | Engine doc so tien tieng Viet, them file MP3 |
| 06 | [06-van-hanh-su-co.md](06-van-hanh-su-co.md) | Van hanh hang ngay, checklist, xu ly su co |
| 07 | [07-faq.md](07-faq.md) | Cau hoi thuong gap (PayOS, phan cung, server, bao mat) |
| 08 | [08-dual-core-architecture.md](08-dual-core-architecture.md) | **(Thiet ke - lam sau)** Refactor firmware sang dual-core |

## Bat dau nhanh

1. Chay server: doc [02-server.md](02-server.md) muc 2-5.
2. Dau day phan cung: doc [01-phan-cung.md](01-phan-cung.md).
3. Nap ESP32: doc [03-firmware.md](03-firmware.md) muc 2-3.
4. Cau hinh PayOS + webhook: doc [04-payos-webhook-deploy.md](04-payos-webhook-deploy.md).

## So do

- Kien truc he thong: [img/architecture.svg](img/architecture.svg)
- So do dau day: [img/wiring.svg](img/wiring.svg)
- Dual-core (thiet ke): [img/dual-core.svg](img/dual-core.svg)

Quick start ngan gon nam o `../README.md`.