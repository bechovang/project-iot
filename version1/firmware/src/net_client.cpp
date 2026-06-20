#include "net_client.h"
#include "config.h"
#include <WiFi.h>
#include <HTTPClient.h>

// Parser JSON gon nhe (khong dung ArduinoJson de bot phu thuoc).
// Du lieu backend tra ve don gian, parse bang tay theo key.

static String json_str(const String& body, const char* key) {
  // tim "key":"value"
  String pat = String("\"") + key + "\":\"";
  int i = body.indexOf(pat);
  if (i < 0) return "";
  i += pat.length();
  int j = body.indexOf('"', i);
  if (j < 0) return "";
  return body.substring(i, j);
}

static long json_num(const String& body, const char* key) {
  // tim "key":number
  String pat = String("\"") + key + "\":";
  int i = body.indexOf(pat);
  if (i < 0) return -1;
  i += pat.length();
  // bo qua khoang trang
  while (i < (int)body.length() && body[i] == ' ') i++;
  int j = i;
  while (j < (int)body.length() && (isdigit(body[j]) || body[j] == '-')) j++;
  if (j == i) return -1;
  return body.substring(i, j).toInt();
}

static bool json_bool(const String& body, const char* key) {
  String pat = String("\"") + key + "\":";
  int i = body.indexOf(pat);
  if (i < 0) return false;
  i += pat.length();
  while (i < (int)body.length() && body[i] == ' ') i++;
  return body.substring(i, i + 4) == "true";
}

void net_init() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("[NET] connecting to %s", WIFI_SSID);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) {
    delay(400);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[NET] connected, IP=%s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[NET] WiFi connect FAILED (se thu lai trong loop)");
  }
}

bool net_connected() {
  return WiFi.status() == WL_CONNECTED;
}

static bool http_get(const char* path, String& out) {
  if (!net_connected()) return false;
  HTTPClient http;
  String url = String(SERVER_BASE_URL) + path;
  http.begin(url);
  http.setTimeout(4000);
  int code = http.GET();
  bool ok = false;
  if (code == 200) {
    out = http.getString();
    ok = true;
  }
  http.end();
  return ok;
}

bool net_get_current(String& out_qr, unsigned long& out_amount, int& out_queue) {
  String body;
  if (!http_get("/api/device/current", body)) return false;
  if (!json_bool(body, "has_order")) return false;
  out_qr = json_str(body, "qr_code");
  long a = json_num(body, "amount");
  long q = json_num(body, "queue_no");
  out_amount = a < 0 ? 0 : (unsigned long)a;
  out_queue = q < 0 ? 0 : (int)q;
  return out_qr.length() > 0;
}

bool net_get_paid_event(unsigned long& out_amount, int& out_queue) {
  String body;
  if (!http_get("/api/device/paid-event", body)) return false;
  if (!json_bool(body, "paid")) return false;
  long a = json_num(body, "amount");
  long q = json_num(body, "queue_no");
  out_amount = a < 0 ? 0 : (unsigned long)a;
  out_queue = q < 0 ? 0 : (int)q;
  return true;
}