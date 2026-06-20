#include <Arduino.h>
#include <WiFi.h>
#include "config.h"
#include "oled_ui.h"
#include "audio_vn.h"
#include "net_client.h"
#include "sync_state.h"

// Task thuc hien cac tac vu mang chay tren Core 0
void NetworkTask(void* parameter) {
  Serial.printf("[NET_TASK] started on Core %d\n", xPortGetCoreID());
  
  unsigned long last_current_poll = 0;
  unsigned long last_paid_poll = 0;
  unsigned long last_stack_log = 0;

  // Cho ket noi WiFi lan dau
  while (WiFi.status() != WL_CONNECTED) {
    g_wifi_connected = false;
    vTaskDelay(pdMS_TO_TICKS(500));
  }
  
  g_wifi_connected = true;
  Serial.printf("[NET_TASK] WiFi connected, IP=%s\n", WiFi.localIP().toString().c_str());

  while (true) {
    // 1. Kiem tra ket noi WiFi
    if (WiFi.status() != WL_CONNECTED) {
      g_wifi_connected = false;
      Serial.println("[NET_TASK] WiFi connection lost, reconnecting...");
      WiFi.reconnect();
      
      // Cho ket noi lai
      int retry = 0;
      while (WiFi.status() != WL_CONNECTED && retry < 20) {
        vTaskDelay(pdMS_TO_TICKS(500));
        retry++;
      }
      if (WiFi.status() == WL_CONNECTED) {
        g_wifi_connected = true;
        Serial.printf("[NET_TASK] WiFi reconnected, IP=%s\n", WiFi.localIP().toString().c_str());
      } else {
        continue;
      }
    }

    g_wifi_connected = true;
    unsigned long now = millis();

    // 2. Poll su kien da thanh toan (uu tien cao)
    if (now - last_paid_poll >= POLL_PAID_MS) {
      last_paid_poll = now;
      unsigned long amt; int q;
      if (net_get_paid_event(amt, q)) {
        Serial.printf("[NET_TASK] PAID event detected: #%d amount=%lu\n", q, amt);
        state_push_paid(amt, q);
      }
    }

    // 3. Poll don hang cho hien QR
    if (now - last_current_poll >= POLL_CURRENT_MS) {
      last_current_poll = now;
      String qr; unsigned long amt; int q;
      if (net_get_current(qr, amt, q)) {
        state_set_current(true, qr, amt, q);
      } else {
        state_set_current(false, "", 0, 0);
      }
    }

    // 4. In thong tin stack debug dinh ky (10s)
    if (now - last_stack_log >= 10000) {
      last_stack_log = now;
      Serial.printf("[NET_TASK] stack free: %u bytes\n", uxTaskGetStackHighWaterMark(NULL));
    }

    vTaskDelay(pdMS_TO_TICKS(50)); // Nhuong CPU cho cac task khac tren Core 0
  }
}

static String   cur_qr = "";
static unsigned long cur_amount = 0;
static int      cur_queue = 0;
static bool     showing_qr = false;

static bool     showing_paid = false;
static unsigned long paid_until = 0;
static bool     was_wifi_connected = false;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== SMART QR PAYMENT - ESP32 DUAL CORE ===");

  oled_init();
  oled_message("Smart QR", "Khoi dong...");

  audio_init();

  oled_message("Ket noi WiFi", "...");
  
  // Khoi tao dong bo
  sync_state_init();
  
  // Bat dau ket noi WiFi o net_client (background)
  net_init();

  // Tao NetworkTask tren Core 0
  xTaskCreatePinnedToCore(
      NetworkTask,
      "NetworkTask",
      NET_TASK_STACK,
      nullptr,
      1,
      nullptr,
      NET_TASK_CORE
  );
}

void loop() {
  audio_loop(); // Luon luon bom am thanh dau tien (dac biet quan trong de ko tre tieng)

  unsigned long now = millis();

  // 1. Uu tien dang hien thi man hinh thanh cong
  if (showing_paid) {
    if (now >= paid_until && !audio_is_playing()) {
      showing_paid = false;
      showing_qr = false; // ep refresh oled
      oled_message("San sang", "Cho don hang");
    }
    return;
  }

  // 2. Kiem tra su kien thanh toan moi tu Queue
  unsigned long amt; int q;
  if (state_pop_paid(amt, q)) {
    Serial.printf("[MAIN] Pop PAID event from Queue: #%d amount=%lu\n", q, amt);
    oled_show_paid(amt, q);
    audio_announce_amount(amt);
    showing_paid = true;
    paid_until = now + 4000; // Hien thi man hinh thanh cong trong it nhat 4s
    return;
  }

  // 3. Theo doi trang thai WiFi va cap nhat giao dien
  bool wifi_now = g_wifi_connected;
  if (wifi_now != was_wifi_connected) {
    was_wifi_connected = wifi_now;
    if (wifi_now) {
      oled_message("San sang", "Cho don hang");
      audio_announce_amount(999); // Phat loa test luc khoi dong xong WiFi
    } else {
      showing_qr = false;
      oled_message("Ket noi WiFi", "...");
    }
  }

  // 4. Neu WiFi dang ket noi, kiem tra va hien QR Code
  if (wifi_now) {
    String qr; unsigned long amt; int q;
    if (state_get_current(qr, amt, q)) {
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