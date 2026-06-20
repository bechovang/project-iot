#include "audio_vn.h"
#include "config.h"
#include "Audio.h"
#include <LittleFS.h>

// =============================================================
//  Doc so tien tieng Viet bang cach ghep file MP3 tren LittleFS
//
//  File co san (data/): mot hai ba bon nam sau bay tam chin
//                       muoi_10 (so 10 "muoi"), muoi (hang chuc "muoi")
//                       tram, nghin_dong (ghep "nghin dong"), da_nhan_duoc
//
//  File TUY CHON (neu them vao data/ se tu dong dung de doc chuan hon):
//     lam.mp3   -> "lam"  (5 o hang don vi sau hang chuc: 25 = hai muoi LAM)
//     mot2.mp3  -> "mot"/"mot" bien am thanh "MOT" (1 sau hang chuc: 21 = hai muoi MOT)
//     le.mp3    -> "le"   (105 = mot tram LE nam)
//     nghin.mp3 -> "nghin" rieng (de doc so co phan le duoi 1000)
//     trieu.mp3 -> "trieu"
//     khong.mp3 -> "khong"
// =============================================================

#define MAX_QUEUE 40

Audio audio;

static const char* g_queue[MAX_QUEUE];
static int  g_queue_len = 0;
static int  g_queue_idx = 0;
static bool g_playing = false;

static volatile bool g_eof_flag = false;

// --- digit -> ten file (1..9) ---
static const char* digit_file(int d) {
  switch (d) {
    case 1: return "/mot.mp3";
    case 2: return "/hai.mp3";
    case 3: return "/ba.mp3";
    case 4: return "/bon.mp3";
    case 5: return "/nam.mp3";
    case 6: return "/sau.mp3";
    case 7: return "/bay.mp3";
    case 8: return "/tam.mp3";
    case 9: return "/chin.mp3";
  }
  return nullptr;
}

static bool fs_has(const char* path) {
  return LittleFS.exists(path);
}

static void q_push(const char* path) {
  if (path && g_queue_len < MAX_QUEUE) {
    g_queue[g_queue_len++] = path;
  }
}

// Doc so nguyen N trong khoang 1..999 -> day file vao queue
static void read_below_1000(int n) {
  if (n <= 0 || n > 999) return;
  int tram = n / 100;
  int chuc = (n % 100) / 10;
  int dv   = n % 10;

  if (tram > 0) {
    q_push(digit_file(tram));
    q_push("/tram.mp3");
    if (chuc == 0 && dv > 0) {
      if (fs_has("/le.mp3")) q_push("/le.mp3");  // "mot tram le nam"
    }
  }

  if (chuc == 0) {
    if (dv > 0) q_push(digit_file(dv));
  } else if (chuc == 1) {
    q_push("/muoi_10.mp3");                       // "muoi"
    if (dv == 5) {
      q_push(fs_has("/lam.mp3") ? "/lam.mp3" : "/nam.mp3");
    } else if (dv > 0) {
      q_push(digit_file(dv));
    }
  } else {
    q_push(digit_file(chuc));
    q_push("/muoi.mp3");                          // "muoi" (hang chuc)
    if (dv == 1) {
      q_push(fs_has("/mot2.mp3") ? "/mot2.mp3" : "/mot.mp3");  // "mot"
    } else if (dv == 5) {
      q_push(fs_has("/lam.mp3") ? "/lam.mp3" : "/nam.mp3");
    } else if (dv > 0) {
      q_push(digit_file(dv));
    }
  }
}

static void play_current() {
  if (g_queue_idx < g_queue_len) {
    const char* f = g_queue[g_queue_idx];
    Serial.printf("[AUDIO] play: %s\n", f);
    audio.connecttoFS(LittleFS, f);
    g_playing = true;
  } else {
    g_playing = false;
  }
}

void audio_init() {
  if (!LittleFS.begin(true)) {
    Serial.println("[AUDIO] LittleFS mount FAILED");
  } else {
    Serial.println("[AUDIO] LittleFS OK");
  }
  audio.setPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
  audio.setVolume(AUDIO_VOLUME);
  Serial.println("[AUDIO] I2S ready");
}

void audio_announce_amount(unsigned long amount_vnd) {
  g_queue_len = 0;
  g_queue_idx = 0;

  q_push("/da_nhan_duoc.mp3");

  unsigned long trieu   = amount_vnd / 1000000UL;
  unsigned long nghin   = (amount_vnd % 1000000UL) / 1000UL;
  unsigned long le      = amount_vnd % 1000UL;     // phan le < 1000 (thuong = 0)

  if (trieu > 0) {
    read_below_1000((int)trieu);
    if (fs_has("/trieu.mp3")) q_push("/trieu.mp3");
  }

  if (nghin > 0) {
    read_below_1000((int)nghin);
    // Neu co phan le -> can "nghin" rieng; neu khong -> dung "nghin_dong" gop
    if (le == 0) {
      q_push("/nghin_dong.mp3");
    } else {
      if (fs_has("/nghin.mp3")) q_push("/nghin.mp3");
      else q_push("/nghin_dong.mp3");  // doc gan dung
    }
  }

  if (le > 0) {
    read_below_1000((int)le);
    // khong co file "dong" rieng -> bo qua (da co "dong" trong nghin_dong neu nghin>0)
  }

  // Neu amount = 0 hoac qua nho: chi phat "da nhan duoc"
  g_eof_flag = false;
  play_current();
}

void audio_loop() {
  audio.loop();
  if (g_eof_flag) {
    g_eof_flag = false;
    g_queue_idx++;
    if (g_queue_idx < g_queue_len) {
      play_current();
    } else {
      g_playing = false;
      Serial.println("[AUDIO] done");
    }
  }
}

bool audio_is_playing() {
  return g_playing;
}

// ---- callbacks cua thu vien Audio ----
void audio_info(const char* info) {}
void audio_id3data(const char* info) {}
void audio_eof_mp3(const char* info) {
  g_eof_flag = true;
}