#ifndef NET_CLIENT_H
#define NET_CLIENT_H

#include <Arduino.h>

void net_init();                 // ket noi WiFi
bool net_connected();

// Lay don dang cho hien QR. Tra ve true neu co don.
// out_qr, out_amount, out_queue duoc dien khi co don.
bool net_get_current(String& out_qr, unsigned long& out_amount, int& out_queue);

// Hoi su kien vua thanh toan. Tra ve true neu co don vua PAID.
bool net_get_paid_event(unsigned long& out_amount, int& out_queue);

#endif // NET_CLIENT_H