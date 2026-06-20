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

static bool is_str_alphanumeric(const char* text) {
  size_t len = strlen(text);
  for (size_t i = 0; i < len; i++) {
    char c = text[i];
    if (c >= '0' && c <= '9') continue;
    if (c >= 'A' && c <= 'Z') continue;
    if (c == ' ' || c == '$' || c == '%' || c == '*' || c == '+' || c == '-' || c == '.' || c == '/' || c == ':') continue;
    return false;
  }
  return true;
}

void oled_show_qr(const char* qr_payload, unsigned long amount, int queue_no) {
  // Convert payload to uppercase to unlock high-efficiency Alphanumeric mode
  String payload_upper = String(qr_payload);
  payload_upper.toUpperCase();
  const char* final_payload = payload_upper.c_str();

  // If converting to uppercase doesn't yield an alphanumeric string (e.g. contains custom URL symbols),
  // fallback to the original payload to preserve case-sensitive URLs
  bool is_alpha = is_str_alphanumeric(final_payload);
  if (!is_alpha) {
    final_payload = qr_payload;
  }

  size_t len = strlen(final_payload);
  uint8_t version = 1;

  // Select safe minimum version depending on encoding mode to prevent stack overflow in qrcode library
  if (is_alpha) {
    if (len <= 25) version = 1;
    else if (len <= 47) version = 2;
    else if (len <= 77) version = 3;
    else if (len <= 114) version = 4;
    else if (len <= 154) version = 5;
    else if (len <= 195) version = 6;
    else if (len <= 224) version = 7;
    else if (len <= 279) version = 8;
    else version = 9;
  } else {
    if (len <= 17) version = 1;
    else if (len <= 32) version = 2;
    else if (len <= 53) version = 3;
    else if (len <= 78) version = 4;
    else if (len <= 106) version = 5;
    else if (len <= 134) version = 6;
    else if (len <= 154) version = 7;
    else if (len <= 192) version = 8;
    else if (len <= 230) version = 9;
    else if (len <= 271) version = 10;
    else version = 11;
  }

  QRCode qrcode;
  uint8_t qrData[qrcode_getBufferSize(11)];   // buffer du cho version cao nhat
  // Thu init, neu fail (chuoi dai hon du tinh) thi tang version dan
  while (qrcode_initText(&qrcode, qrData, version, ECC_LOW, final_payload) != 0 && version < 11) {
    version++;
  }

  u8g2.clearBuffer();

  // QR ben trai, ve voi ti le phu hop voi chieu cao OLED 64px
  int qsize = qrcode.size;        // so module 1 chieu
  if (qsize <= 0) qsize = 1;      // Prevent division by zero
  int scale = 64 / qsize;
  if (scale < 1) scale = 1;
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