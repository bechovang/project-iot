#ifndef SYNC_STATE_H
#define SYNC_STATE_H

#include <Arduino.h>

struct CurrentState {
  bool          has_order;
  String        qr_code;
  unsigned long amount;
  int           queue_no;
};

struct PaidEvent {
  unsigned long amount;
  int           queue_no;
};

void sync_state_init();
void state_set_current(bool has, const String& qr, unsigned long amt, int q);
bool state_get_current(String& qr, unsigned long& amt, int& q);
void state_push_paid(unsigned long amt, int q);
bool state_pop_paid(unsigned long& amt, int& q);

extern volatile bool g_wifi_connected;

#endif // SYNC_STATE_H
