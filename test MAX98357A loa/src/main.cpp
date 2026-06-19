#include <Arduino.h>
#include "Audio.h"
#include <LittleFS.h>

#define I2S_BCLK  26
#define I2S_LRC   27
#define I2S_DOUT  25
#define VOLUME    21     // Âm lượng to hết cỡ (từ 0..21)

Audio audio;

// Danh sách các file phát lần lượt để tạo thành câu: "đã nhận được mười một nghìn đồng"
const char* playlist[] = {
  "/da_nhan_duoc.mp3",
  "/muoi_10.mp3",
  "/mot.mp3",
  "/nghin_dong.mp3"
};
const int playlistSize = sizeof(playlist) / sizeof(playlist[0]);
int currentTrackIndex = 0;

volatile bool nextTrackFlag = false;
unsigned long playlistDelayTimer = 0;
bool waitingForNextLoop = false;

void playNextTrack() {
  if (currentTrackIndex < playlistSize) {
    Serial.printf("Phat file: %s\n", playlist[currentTrackIndex]);
    audio.connecttoFS(LittleFS, playlist[currentTrackIndex]);
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("====================================");
  Serial.println("  MAX98357A - MP3 ghep am thanh");
  Serial.println("  DIN=25  BCLK=26  LRC=27  (D4/D5/D6)");
  Serial.println("====================================");

  // Mount LittleFS
  if (!LittleFS.begin(true)) {
    Serial.println("LOI: khong mount duoc LittleFS!");
    while (true) { delay(1000); }
  }
  Serial.println("LittleFS mount OK.");

  // Cấu hình chân I2S và âm lượng
  audio.setPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
  audio.setVolume(VOLUME);

  // Bắt đầu phát từ file đầu tiên
  currentTrackIndex = 0;
  playNextTrack();
}

void loop() {
  audio.loop();

  // Nếu file trước đó phát xong, chuyển sang file kế tiếp
  if (nextTrackFlag) {
    nextTrackFlag = false;
    currentTrackIndex++;
    if (currentTrackIndex < playlistSize) {
      playNextTrack();
    } else {
      Serial.println("--- Phat het cau! Cho 3 giay de lap lai ---");
      playlistDelayTimer = millis();
      waitingForNextLoop = true;
    }
  }

  // Lặp lại toàn bộ câu sau mỗi 3 giây
  if (waitingForNextLoop && (millis() - playlistDelayTimer >= 3000)) {
    waitingForNextLoop = false;
    currentTrackIndex = 0;
    playNextTrack();
  }
}

// ================= Callbacks của thư viện Audio =================
void audio_info(const char *info) {
  // Tắt bớt log debug rác để Serial Monitor sạch hơn
}

void audio_id3data(const char *info) {
}

// Được gọi tự động khi file MP3 hiện tại phát xong
void audio_eof_mp3(const char *info) {
  Serial.printf("Xong file: %s\n", info);
  nextTrackFlag = true;
}
