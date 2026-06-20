#include "oled_ui.h"
#include "config.h"
#include <U8g2lib.h>
#include <Wire.h>
#include "qrcode.h"

// SH1106 128x64 full frame buffer (ESP32 du RAM)
static U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

void oled_init() {
  Wire.begin(I2C_SDA, I2C_SCL);
  u8g2.begin();
  u8g2.setBitmapMode(1);
}

static void draw_center(int y, const char* s) {
  int w = u8g2.getStrWidth(s);
  u8g2.drawStr((128 - w) / 2, y, s);
}

void oled_message(const char* line1, const char* line2) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_7x13B_tr);
  if (line2) {
    draw_center(28, line1);
    draw_center(46, line2);
  } else {
    draw_center(38, line1);
  }
  u8g2.sendBuffer();
}

// Format tien co dau cham: 11000 -> "11.000d"
static String fmt_money(unsigned long amount) {
  String s = String(amount);
  String out = "";
  int cnt = 0;
  for (int i = s.length() - 1; i >= 0; i--) {
    out = s[i] + out;
    if (++cnt % 3 == 0 && i > 0) out = "." + out;
  }
  return out + "d";
}

void oled_show_qr(const char* qr_payload, unsigned long amount, int queue_no) {
  // PayOS QR ~120-180 ky tu (byte mode). Chon version nho nhat du chua,
  // toi da version 11 (61x61 module) van vua chieu cao OLED 64px.
  //   v8=49x49 (<=152B), v9=53x53, v10=57x57, v11=61x61 (<=287B) o ECC_LOW
  size_t len = strlen(qr_payload);
  uint8_t version = 8;
  if (len > 152) version = 9;
  if (len > 180) version = 10;
  if (len > 213) version = 11;

  QRCode qrcode;
  uint8_t qrData[qrcode_getBufferSize(11)];   // buffer du cho version cao nhat
  // Thu init, neu fail (chuoi dai hon du tinh) thi tang version dan
  while (qrcode_initText(&qrcode, qrData, version, ECC_LOW, qr_payload) != 0 && version < 11) {
    version++;
  }

  u8g2.clearBuffer();

  // QR ben trai, ve voi 1 pixel / module (49x49 < 64 -> vua chieu cao)
  int qsize = qrcode.size;        // so module 1 chieu
  int scale = 1;
  int qpx = qsize * scale;
  int ox = 2;
  int oy = (64 - qpx) / 2;
  if (oy < 0) oy = 0;

  // Nen trang sau QR de quet de hon
  u8g2.setDrawColor(1);
  for (int y = 0; y < qsize; y++) {
    for (int x = 0; x < qsize; x++) {
      if (qrcode_getModule(&qrcode, x, y)) {
        u8g2.drawPixel(ox + x * scale, oy + y * scale);
      }
    }
  }

  // Thong tin ben phai
  int tx = ox + qpx + 6;
  if (tx > 70) tx = 70;
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(tx, 12, "QUET QR");
  char buf[24];
  snprintf(buf, sizeof(buf), "#%d", queue_no);
  u8g2.drawStr(tx, 28, buf);
  u8g2.setFont(u8g2_font_6x12_tf);
  String m = fmt_money(amount);
  u8g2.drawStr(tx, 46, m.c_str());

  u8g2.sendBuffer();
}

void oled_show_paid(unsigned long amount, int queue_no) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_9x15B_tr);
  draw_center(22, "THANH CONG");
  u8g2.setFont(u8g2_font_7x13_tr);
  char buf[24];
  snprintf(buf, sizeof(buf), "Don #%d", queue_no);
  draw_center(42, buf);
  String m = fmt_money(amount);
  draw_center(60, m.c_str());
  u8g2.sendBuffer();
}