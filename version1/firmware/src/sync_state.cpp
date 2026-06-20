#include "sync_state.h"

static CurrentState g_current;
static SemaphoreHandle_t g_current_mutex = nullptr;
static QueueHandle_t g_paid_queue = nullptr;

volatile bool g_wifi_connected = false;

void sync_state_init() {
  if (g_current_mutex == nullptr) {
    g_current_mutex = xSemaphoreCreateMutex();
  }
  if (g_paid_queue == nullptr) {
    g_paid_queue = xQueueCreate(8, sizeof(PaidEvent));
  }
  g_current.has_order = false;
  g_current.qr_code = "";
  g_current.amount = 0;
  g_current.queue_no = 0;
}

void state_set_current(bool has, const String& qr, unsigned long amt, int q) {
  if (g_current_mutex && xSemaphoreTake(g_current_mutex, portMAX_DELAY) == pdTRUE) {
    g_current.has_order = has;
    g_current.qr_code   = qr;
    g_current.amount    = amt;
    g_current.queue_no  = q;
    xSemaphoreGive(g_current_mutex);
  }
}

bool state_get_current(String& qr, unsigned long& amt, int& q) {
  bool has = false;
  if (g_current_mutex && xSemaphoreTake(g_current_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
    has = g_current.has_order;
    qr  = g_current.qr_code;
    amt = g_current.amount;
    q   = g_current.queue_no;
    xSemaphoreGive(g_current_mutex);
  }
  return has;
}

void state_push_paid(unsigned long amt, int q) {
  if (g_paid_queue) {
    PaidEvent e { amt, q };
    xQueueSend(g_paid_queue, &e, pdMS_TO_TICKS(10));
  }
}

bool state_pop_paid(unsigned long& amt, int& q) {
  if (g_paid_queue) {
    PaidEvent e;
    if (xQueueReceive(g_paid_queue, &e, 0) == pdTRUE) {
      amt = e.amount;
      q = e.queue_no;
      return true;
    }
  }
  return false;
}
