/*
  ====================================================================
   SMART QR PAYMENT - ESP32 firmware
   - OLED SH1106 (I2C 21/22): hien QR PayOS + trang thai
   - Loa MAX98357A (I2S 25/26/27): doc so tien khi thanh toan thanh cong
   - WiFi STA: poll backend FastAPI tren LAN
  ====================================================================

   Luong:
   1) Ket noi WiFi -> hien "San sang"
   2) Poll /api/device/current: co don PENDING -> ve QR len OLED
   3) Poll /api/device/paid-event: co don vua PAID ->
        - phat loa "da nhan duoc <so tien> dong"
        - hien "THANH CONG" vai giay
   4) Quay lai cho don tiep theo
*/
#include <Arduino.h>
#include "config.h"
#include "oled_ui.h"
#include "audio_vn.h"
#include "net_client.h"

static unsigned long last_current_poll = 0;
static unsigned long last_paid_poll = 0;

static String   cur_qr = "";
static unsigned long cur_amount = 0;
static int      cur_queue = 0;
static bool     showing_qr = false;

// trang thai hien "thanh cong"
static bool     showing_paid = false;
static unsigned long paid_until = 0;
static unsigned long paid_amount = 0;
static int      paid_queue = 0;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== SMART QR PAYMENT - ESP32 ===");

  oled_init();
  oled_message("Smart QR", "Khoi dong...");

  audio_init();

  oled_message("Ket noi WiFi", "...");
  net_init();

  if (net_connected()) {
    oled_message("San sang", "Cho don hang");
    audio_announce_amount(999); // Am thanh test loa luc khoi dong: "Da nhan duoc chin tram chin muoi chin dong"
  } else {
    oled_message("WiFi loi", "Kiem tra SSID");
  }
}

void loop() {
  audio_loop();   // luon bom du lieu audio

  unsigned long now = millis();

  // --- Uu tien: dang hien man hinh "thanh cong" ---
  if (showing_paid) {
    if (now >= paid_until && !audio_is_playing()) {
      showing_paid = false;
      showing_qr = false;       // ep ve QR/san sang o lan poll sau
      oled_message("San sang", "Cho don hang");
    }
    return;
  }

  // --- Poll su kien da thanh toan ---
  if (now - last_paid_poll >= POLL_PAID_MS) {
    last_paid_poll = now;
    unsigned long amt; int q;
    if (net_get_paid_event(amt, q)) {
      Serial.printf("[MAIN] PAID #%d amount=%lu\n", q, amt);
      paid_amount = amt; paid_queue = q;
      oled_show_paid(amt, q);
      audio_announce_amount(amt);
      showing_paid = true;
      paid_until = now + 4000;  // it nhat 4s
      return;
    }
  }

  // --- Poll don dang cho de hien QR ---
  if (now - last_current_poll >= POLL_CURRENT_MS) {
    last_current_poll = now;
    String qr; unsigned long amt; int q;
    if (net_get_current(qr, amt, q)) {
      if (!showing_qr || qr != cur_qr) {
        cur_qr = qr; cur_amount = amt; cur_queue = q;
        showing_qr = true;
        oled_show_qr(cur_qr.c_str(), cur_amount, cur_queue);
        Serial.printf("[MAIN] show QR #%d amount=%lu len=%d\n", q, amt, qr.length());
      }
    } else {
      if (showing_qr) {
        showing_qr = false;
        oled_message("San sang", "Cho don hang");
      }
    }
  }
}