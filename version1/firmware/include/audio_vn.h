#ifndef AUDIO_VN_H
#define AUDIO_VN_H

#include <Arduino.h>

// Khoi tao I2S + LittleFS cho loa MAX98357A
void audio_init();

// Goi lien tuc trong loop() de bom du lieu audio
void audio_loop();

// Phat cau "da nhan duoc <so tien> dong" cho so tien VND bat ky.
// Tu dong ghep cac file MP3 so tieng Viet tren LittleFS.
void audio_announce_amount(unsigned long amount_vnd);

// Co dang phat khong
bool audio_is_playing();

#endif // AUDIO_VN_H