# 05 - Engine doc so tien tieng Viet (loa)

## 1. Y tuong

Khong thu am tung so tien. Thay vao do thu am tung "tu" (mot, hai, ..., muoi, tram,
nghin dong...) thanh cac file MP3 ngan, roi **ghep** lai theo so tien can doc.

Vi du `11000`:
```
da_nhan_duoc + muoi_10 + mot + nghin_dong
=> "da nhan duoc muoi mot nghin dong"
```

Co che ghep nam o `firmware/src/audio_vn.cpp`, phat qua thu vien ESP32-audioI2S.

## 2. Cac file MP3 hien co (trong `firmware/data/`)

| File | Doc la | Dung cho |
|------|--------|----------|
| `da_nhan_duoc.mp3` | "da nhan duoc" | Cau mo dau |
| `mot.mp3` .. `chin.mp3` | 1..9 | Chu so |
| `muoi_10.mp3` | "muoi" (so 10) | Khi hang chuc = 1 (10..19) |
| `muoi.mp3` | "muoi" (hang chuc) | Khi hang chuc >= 2 (20, 30...) |
| `tram.mp3` | "tram" | Hang tram |
| `nghin_dong.mp3` | "nghin dong" | Ket cau "nghin dong" |

> Phan biet `muoi_10` va `muoi`: tieng Viet doc "MUOI mot" (10+1) nhung "hai MUOI"
> (2 chuc). Hai file giup phat am tu nhien hon.

## 3. Cach engine ghep cau

Ham `audio_announce_amount(amount)`:

1. Day `da_nhan_duoc.mp3` vao hang doi.
2. Tach so tien:
   - `trieu = amount / 1.000.000`
   - `nghin = (amount % 1.000.000) / 1.000`
   - `le    = amount % 1.000`  (phan duoi nghin, thuong = 0)
3. Doc phan trieu (neu co) + "trieu".
4. Doc phan nghin (neu co):
   - Neu khong co phan le -> dung `nghin_dong` (gop "nghin dong").
   - Neu co phan le -> can "nghin" rieng (file tuy chon `nghin.mp3`).
5. Doc phan le (neu co).
6. Phat lan luot: moi khi 1 file xong (`audio_eof_mp3`) thi phat file ke tiep.

Ham phu `read_below_1000(n)` doc so 1..999: tram / chuc / don vi, xu ly cac quy tac
"muoi", "lam", "mot" (xem muc 5).

## 4. Pham vi doc tot voi bo file hien tai

- **So tien la boi so 1.000, duoi 1 trieu** (vd 11.000, 35.000, 250.000, 999.000): doc tron tru.
- Vi mo hinh quan cafe gia tien deu dang nay nen bo file hien tai **du dung**.

## 5. Cac so "dac biet" trong tieng Viet & file tuy chon

Tieng Viet co bien am khi doc so. Engine da xu ly, nhung doc CHUAN can them vai file:

| Truong hop | Doc dung | File tuy chon can them |
|-----------|----------|------------------------|
| 5 o hang don vi sau hang chuc (>=20): 25 | "hai muoi **LAM**" (khong phai "nam") | `lam.mp3` |
| 1 o hang don vi sau hang chuc (>=20): 21 | "hai muoi **MOT**" (giong "mot" thuong) | `mot2.mp3` (tuy chon) |
| Hang chuc = 0 nhung co tram va don vi: 105 | "mot tram **LE** nam" | `le.mp3` |
| So co phan le duoi nghin: 105.500 | "...**nghin**..." (tach roi) | `nghin.mp3` |
| Hang trieu: 1.000.000 | "mot **trieu**" | `trieu.mp3` |
| So 0 (it dung) | "khong" | `khong.mp3` |

**Quan trong:** Neu KHONG co cac file tuy chon, engine tu fallback:
- Thieu `lam.mp3` -> doc `nam.mp3` ("hai muoi nam" - van hieu duoc).
- Thieu `mot2.mp3` -> doc `mot.mp3`.
- Thieu `nghin.mp3` -> doc `nghin_dong.mp3` (gan dung).

Tuc la **khong them gi van chay**, chi la mot so so doc chua chuan 100%.

## 6. Cach them file MP3 moi

1. Thu am / tao file MP3 cho tu can them. Goi y:
   - 16kHz, mono, bitrate thap (~64kbps) cho nhe, giong cac file co san.
   - Doc ro rang, cat khoang lang dau/cuoi.
2. Dat ten **khong dau, chu thuong** (vd `lam.mp3`, `le.mp3`, `trieu.mp3`).
3. Copy vao `firmware/data/`.
4. Nap lai LittleFS:
   ```powershell
   cd version1\firmware
   pio run -t uploadfs
   ```
5. Engine tu dong dung file moi (co kiem tra `LittleFS.exists()` truoc khi dung).

> Bo file goc tieng Viet (co dau) nam o `test MAX98357A loa/sound/`. Script
> `test MAX98357A loa/prepare_sounds.py` minh hoa cach doi ten co dau -> khong dau.

## 7. Tao MP3 tu dong bang Text-to-Speech (tuy chon)

Neu khong muon thu am tay, co the dung TTS (vd gTTS - Google) de sinh nhanh:
```python
# pip install gTTS
from gtts import gTTS
words = {"lam":"lăm", "le":"lẻ", "trieu":"triệu", "nghin":"nghìn", "khong":"không",
         "mot2":"mốt"}
for fname, text in words.items():
    gTTS(text=text, lang="vi").save(f"data/{fname}.mp3")
```
> Giong TTS se khac giong cac file thu san -> nghe co the khong dong nhat. Neu can dong bo,
> nen thu am lai toan bo bang cung mot giong.

## 8. Kiem tra nhanh am thanh (khong can server)

Co the tam sua `main.cpp` goi thu `audio_announce_amount(11000)` trong `setup()` de nghe
thu cau doc, hoac nap lai project `test MAX98357A loa` de test phan cung loa truoc.

## 9. Gioi han hien tai

- Chua doc duoc so > 999.999.999 (gan 1 ty) mot cach day du - du xa cho quan cafe.
- Khong co file "dong" doc rieng (chi co "nghin dong"). Voi so tron nghin thi luon dung;
  voi so co phan le duoi nghin se thieu chu "dong" o cuoi (hiem gap trong thuc te quan).