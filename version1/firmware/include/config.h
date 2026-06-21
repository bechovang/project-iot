#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
//  SMART QR PAYMENT - Firmware config (ESP32 DevKit)
// ============================================================

// --- WiFi (STA - noi mang nha de ra Internet/LAN toi server) ---
#define WIFI_SSID       "DiepNguyen 5G"
#define WIFI_PASS       "0906808777"

// --- Server backend (FastAPI) tren LAN ---
//  Vi du PC chay server co IP 192.168.1.4 -> "http://192.168.1.4:8000"
#define SERVER_BASE_URL "http://bechovang.loca.lt"

// --- Chu ky poll ---
#define POLL_CURRENT_MS   1500   // hoi don dang cho de hien QR
#define POLL_PAID_MS      1500   // hoi su kien da thanh toan

// --- OLED SH1106 128x64 (I2C) ---
#define I2C_SDA         21
#define I2C_SCL         22

// --- I2S Audio MAX98357A (theo mach da dau: DIN=25 BCLK=26 LRC=27) ---
#define I2S_DOUT        25
#define I2S_BCLK        26
#define I2S_LRC         27
#define AUDIO_VOLUME    21       // 0..21

// --- Dual-core parameters ---
#define HTTP_TIMEOUT_MS   3000     // timeout goi HTTP (giam xuong 3s)
#define NET_TASK_STACK    10240    // stack size cho NetworkTask (10KB - đủ chạy HTTP thường)
#define NET_TASK_CORE     0        // Core gan cho NetworkTask (Core 0)

#endif // CONFIG_H