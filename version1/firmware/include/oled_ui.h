#ifndef OLED_UI_H
#define OLED_UI_H

#include <Arduino.h>

void oled_init();

// Man hinh thong bao 1-2 dong (can giua)
void oled_message(const char* line1, const char* line2 = nullptr);

// Hien QR (chuoi EMVCo PayOS) + so tien + so thu tu don
void oled_show_qr(const char* qr_payload, unsigned long amount, int queue_no);

// Man hinh thanh toan thanh cong
void oled_show_paid(unsigned long amount, int queue_no);

#endif // OLED_UI_H