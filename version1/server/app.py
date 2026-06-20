"""
app.py - Backend FastAPI cho Smart QR Payment.

Vai tro:
  - Nhan lenh tao don tu Streamlit cashier  (POST /api/orders)
  - Goi PayOS tao payment link, luu vao store
  - Nhan webhook PayOS khi khach thanh toan  (POST /api/payment/payos-webhook)
  - Phuc vu ESP32 (LAN): lay don dang cho de hien QR  (GET /api/device/current)
                         lay su kien vua PAID de phat loa (GET /api/device/paid-event)
  - Trang TV cho khach xem hang doi don  (GET /tv)

Chay:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import os
import json
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import payos_client
from store import store

load_dotenv()

API_TOKEN = os.environ.get("API_TOKEN", "").strip()

app = FastAPI(title="Smart QR Payment Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _check_token(token: str):
    if API_TOKEN and token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")


# ----------------------------------------------------------------------------
#  CASHIER (Streamlit) -> tao don
# ----------------------------------------------------------------------------
@app.post("/api/orders")
async def create_order(req: Request, x_api_token: str = Header(default="")):
    _check_token(x_api_token)
    body = await req.json()

    amount = int(body.get("amount", 0))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    description = body.get("description", "Thanh toan")
    items = body.get("items", [])

    try:
        pay = payos_client.create_payment(amount, description, items)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PayOS error: {e}")

    order = store.create(
        order_code=pay["order_code"], amount=pay["amount"],
        description=pay["description"], items=items,
        qr_code=pay["qr_code"], checkout_url=pay["checkout_url"],
        payment_link_id=pay["payment_link_id"],
    )
    return order


@app.get("/api/orders")
async def list_orders():
    return store.list()


@app.get("/api/orders/{order_code}")
async def get_order(order_code: int):
    o = store.get(order_code)
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    return o


@app.post("/api/orders/{order_code}/cancel")
async def cancel_order(order_code: int, x_api_token: str = Header(default="")):
    _check_token(x_api_token)
    try:
        payos_client.cancel(order_code)
    except Exception as e:
        print("[cancel] PayOS:", e)
    store.set_status(order_code, "CANCELLED")
    return store.get(order_code)


# ----------------------------------------------------------------------------
#  WEBHOOK tu PayOS
# ----------------------------------------------------------------------------
@app.post("/api/payment/payos-webhook")
async def payos_webhook(req: Request):
    body = await req.json()
    # PayOS ban dau goi 1 lan voi du lieu mau de xac thuc URL -> tra 200 ngay.
    try:
        data = payos_client.verify_webhook(body)
    except Exception as e:
        # Chu ky sai -> tu choi
        print("[webhook] verify failed:", e)
        return JSONResponse({"error": -1, "message": "invalid signature"}, status_code=400)

    # data la dict da verify chu ky
    order_code = data.get("orderCode")
    desc = data.get("description", "") or ""

    # Bo qua giao dich thu nghiem cua PayOS
    if desc in ("Ma giao dich thu nghiem", "VQRIO123"):
        return {"error": 0, "message": "test webhook ok"}

    if order_code is not None:
        o = store.mark_paid(int(order_code))
        if o:
            print(f"[webhook] PAID order={order_code} amount={o['amount']}")

    return {"error": 0, "message": "ok"}


@app.get("/Q/{queue_no}")
@app.get("/q/{queue_no}")
async def redirect_short_link(queue_no: int):
    """Chuyen huong tu link rut gon tren ESP32 sang trang thanh toan PayOS thuc te (chap nhan ca chu hoa Q do ESP32 viet hoa)."""
    with store._lock:
        cur = store._conn.execute(
            "SELECT checkout_url FROM orders WHERE queue_no = ? AND status = 'PENDING' ORDER BY created_at DESC LIMIT 1",
            (queue_no,)
        )
        row = cur.fetchone()
        if not row:
            cur = store._conn.execute(
                "SELECT checkout_url FROM orders WHERE queue_no = ? ORDER BY created_at DESC LIMIT 1",
                (queue_no,)
            )
            row = cur.fetchone()
        
        if row and row["checkout_url"]:
            return RedirectResponse(url=row["checkout_url"])
    raise HTTPException(status_code=404, detail="Order not found")


# ----------------------------------------------------------------------------
#  THIET BI ESP32 (LAN polling)
# ----------------------------------------------------------------------------
@app.get("/api/device/current")
async def device_current():
    """Don PENDING moi nhat de ESP32 hien QR len OLED."""
    o = store.latest_pending()
    if not o:
        return {"has_order": False}
    
    # Generate public short URL for ESP32 QR display
    # PUBLIC_BASE_URL contains the ngrok endpoint from payos_client
    pub_url = payos_client.PUBLIC_BASE_URL
    short_url = f"{pub_url}/q/{o['queue_no']}" if pub_url else f"http://127.0.0.1:8000/q/{o['queue_no']}"
    
    return {
        "has_order": True,
        "order_code": o["order_code"],
        "amount": o["amount"],
        "qr_code": short_url,
        "queue_no": o["queue_no"],
    }


@app.get("/api/device/paid-event")
async def device_paid_event():
    """Tra ve don vua PAID 1 lan de ESP32 phat loa doc tien."""
    o = store.pop_paid_event()
    if not o:
        return {"paid": False}
    return {
        "paid": True,
        "order_code": o["order_code"],
        "amount": o["amount"],
        "queue_no": o["queue_no"],
    }


@app.post("/api/orders/{order_code}/status")
async def update_order_status(order_code: int, req: Request, x_api_token: str = Header(default="")):
    _check_token(x_api_token)
    body = await req.json()
    new_status = body.get("status")
    if new_status not in ["READY", "DONE", "PAID", "PENDING", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    o = store.set_status(order_code, new_status)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return o


# ----------------------------------------------------------------------------
#  Trang dieu huong sau thanh toan (returnUrl / cancelUrl)
# ----------------------------------------------------------------------------
@app.get("/paid", response_class=HTMLResponse)
async def paid_page():
    return "<h1>Thanh toan thanh cong!</h1><p>Cam on quy khach.</p>"


@app.get("/cancelled", response_class=HTMLResponse)
async def cancelled_page():
    return "<h1>Da huy thanh toan</h1>"


# ----------------------------------------------------------------------------
#  Trang TV cho khach xem hang doi
# ----------------------------------------------------------------------------
@app.get("/tv", response_class=HTMLResponse)
async def tv_page():
    html = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bảng Gọi Món - Premium TV Queue</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    font-family: 'Outfit', system-ui, -apple-system, sans-serif; 
    background: radial-gradient(circle at top right, #1e1b4b 0%, #0f172a 50%, #020617 100%);
    color: #f8fafc;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  /* Top Navigation / Header */
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24px 48px;
    background: rgba(15, 23, 42, 0.4);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .brand-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
    font-weight: 900;
    font-size: 20px;
    color: #fff;
  }
  .brand-text h1 {
    font-size: 24px;
    font-weight: 900;
    letter-spacing: -0.5px;
    background: linear-gradient(to right, #38bdf8, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .brand-text p {
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 600;
    margin-top: -2px;
  }
  .header-info {
    display: flex;
    align-items: center;
    gap: 32px;
  }
  .live-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 185, 129, 0.1);
    padding: 6px 16px;
    border-radius: 100px;
    border: 1px solid rgba(16, 185, 129, 0.2);
    font-size: 13px;
    font-weight: 600;
    color: #34d399;
  }
  .live-dot {
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    animation: pulse 1.6s infinite;
  }
  .clock {
    font-size: 28px;
    font-weight: 800;
    color: #e2e8f0;
    font-variant-numeric: tabular-nums;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
  }

  /* Dashboard Layout */
  .dashboard {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* Columns Setup */
  .col {
    display: flex;
    flex-direction: column;
    padding: 40px 48px;
    height: 100%;
    overflow: hidden;
  }
  
  /* READY COLUMN (70%) */
  .col-ready {
    width: 68%;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  /* PREPARING COLUMN (32%) */
  .col-preparing {
    width: 32%;
    background: rgba(15, 23, 42, 0.2);
  }

  /* Column Headers */
  .col-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
  }
  .col-title {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .col-title h2 {
    font-size: 28px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .col-ready h2 {
    color: #34d399;
    text-shadow: 0 0 20px rgba(52, 211, 153, 0.15);
  }
  .col-preparing h2 {
    color: #f59e0b;
    text-shadow: 0 0 20px rgba(245, 158, 11, 0.15);
  }
  .col-title p {
    font-size: 14px;
    color: #64748b;
    font-weight: 500;
  }
  .badge-count {
    background: rgba(255, 255, 255, 0.05);
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 800;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }
  .col-ready .badge-count {
    color: #34d399;
    background: rgba(52, 211, 153, 0.08);
    border-color: rgba(52, 211, 153, 0.15);
  }
  .col-preparing .badge-count {
    color: #fbbf24;
    background: rgba(251, 191, 36, 0.08);
    border-color: rgba(251, 191, 36, 0.15);
  }

  /* Grid Area */
  .grid {
    display: grid;
    gap: 24px;
    align-content: start;
    flex: 1;
    overflow-y: auto;
    padding-right: 8px;
  }
  .grid::-webkit-scrollbar {
    width: 6px;
  }
  .grid::-webkit-scrollbar-track {
    background: transparent;
  }
  .grid::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
  }
  
  .col-ready .grid {
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  }
  .col-preparing .grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  }

  /* Cards Design: Glassmorphism Pro Max */
  .card {
    position: relative;
    border-radius: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    user-select: none;
  }

  .col-ready .card {
    height: 180px;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(5, 150, 105, 0.02) 100%);
    border: 2px solid rgba(16, 185, 129, 0.25);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2), inset 0 0 12px rgba(16, 185, 129, 0.1);
    animation: readyPulse 2s infinite alternate, popIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }
  .col-ready .card-number {
    font-size: 80px;
    font-weight: 900;
    color: #34d399;
    letter-spacing: -2px;
    line-height: 1;
    text-shadow: 0 0 20px rgba(52, 211, 153, 0.3);
  }
  .col-ready .card-label {
    font-size: 13px;
    text-transform: uppercase;
    font-weight: 800;
    color: #6ee7b7;
    letter-spacing: 2px;
    margin-top: 6px;
    opacity: 0.8;
  }

  .col-preparing .card {
    height: 100px;
    background: rgba(30, 41, 59, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
    animation: popIn 0.4s ease-out both;
  }
  .col-preparing .card-number {
    font-size: 40px;
    font-weight: 800;
    color: #94a3b8;
    line-height: 1;
  }
  .col-preparing .card-label {
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 1px;
    margin-top: 4px;
  }

  /* Glow Overlay Effect on Hover */
  .card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0) 100%);
    z-index: 1;
    pointer-events: none;
  }

  /* Empty States */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #475569;
    gap: 16px;
    animation: fadeIn 0.8s ease-in-out;
  }
  .empty-icon {
    font-size: 48px;
    opacity: 0.3;
  }
  .empty-state p {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }

  /* Keyframe Animations */
  @keyframes pulse {
    0% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
    70% { transform: scale(1.1); opacity: 0.5; box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
    100% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
  }
  @keyframes readyPulse {
    0% {
      border-color: rgba(16, 185, 129, 0.25);
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2), 0 0 10px rgba(16, 185, 129, 0.1);
    }
    100% {
      border-color: rgba(52, 211, 153, 0.7);
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2), 0 0 25px rgba(52, 211, 153, 0.35);
      transform: translateY(-4px);
    }
  }
  @keyframes popIn {
    0% { transform: scale(0.85); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-logo">☕</div>
      <div class="brand-text">
        <h1>SMART UNDERRATED TV</h1>
        <p>Bảng Trả Món Tự Động</p>
      </div>
    </div>
    <div class="header-info">
      <div class="live-indicator">
        <div class="live-dot"></div>
        <span>KẾT NỐI LIVE</span>
      </div>
      <div class="clock" id="clock">00:00:00</div>
    </div>
  </header>

  <div class="dashboard">
    <!-- CỘT READY (Mời nhận món) -->
    <div class="col col-ready">
      <div class="col-header">
        <div class="col-title">
          <h2>Mời Nhận Món</h2>
          <p>Ready for Pickup</p>
        </div>
        <div class="badge-count" id="ready-count">0 MÓN</div>
      </div>
      <div id="ready-grid" class="grid"></div>
      <div id="ready-empty" class="empty-state" style="display:none;">
        <div class="empty-icon">🔔</div>
        <p>Tất cả đơn hàng đã được trả xong</p>
      </div>
    </div>

    <!-- CỘT PREPARING (Đang chế biến) -->
    <div class="col col-preparing">
      <div class="col-header">
        <div class="col-title">
          <h2>Đang Chế Biến</h2>
          <p>Preparing</p>
        </div>
        <div class="badge-count" id="prep-count">0 MÓN</div>
      </div>
      <div id="preparing-grid" class="grid"></div>
      <div id="preparing-empty" class="empty-state" style="display:none;">
        <div class="empty-icon">🍳</div>
        <p>Không có đơn đang pha chế</p>
      </div>
    </div>
  </div>

<script>
// Đồng hồ số
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  const s = String(now.getSeconds()).padStart(2, '0');
  document.getElementById('clock').textContent = `${h}:${m}:${s}`;
}
setInterval(updateClock, 1000);
updateClock();

// Set lưu trữ các queue_no đã ở cột ready từ lần refresh trước
let lastReadySet = new Set();

async function refresh(){
  try {
    const r = await fetch('/api/orders');
    if (!r.ok) return;
    const data = await r.json();
    
    const readyOrders = data.filter(o => o.status === 'READY');
    const preparingOrders = data.filter(o => o.status === 'PAID');
    
    // Cập nhật số lượng đếm
    document.getElementById('ready-count').textContent = `${readyOrders.length} MÓN`;
    document.getElementById('prep-count').textContent = `${preparingOrders.length} MÓN`;
    
    // Render cột READY
    const readyGrid = document.getElementById('ready-grid');
    const readyEmpty = document.getElementById('ready-empty');
    if (readyOrders.length === 0) {
      readyGrid.innerHTML = '';
      readyEmpty.style.display = 'flex';
    } else {
      readyEmpty.style.display = 'none';
      readyGrid.innerHTML = readyOrders.map(o => `
        <div class="card">
          <div class="card-number">#${o.queue_no}</div>
          <div class="card-label">Mời nhận món</div>
        </div>
      `).join('');
    }

    // Phát âm thanh khi có món mới chuyển sang READY
    let hasNewReady = false;
    const currentReadySet = new Set(readyOrders.map(o => o.queue_no));
    for (let q of currentReadySet) {
      if (!lastReadySet.has(q) && lastReadySet.size > 0) {
        hasNewReady = true;
      }
    }
    lastReadySet = currentReadySet;

    if (hasNewReady) {
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        
        // Tạo hợp âm dễ thương thông báo
        const playTone = (freq, startTime, duration) => {
          const osc = audioCtx.createOscillator();
          const gain = audioCtx.createGain();
          
          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, startTime);
          
          gain.gain.setValueAtTime(0.08, startTime);
          gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
          
          osc.connect(gain);
          gain.connect(audioCtx.destination);
          osc.start(startTime);
          osc.stop(startTime + duration);
        };
        
        // Hợp âm phát nhanh Arpeggio (Đô - Mi - Sol - Đô)
        const t = audioCtx.currentTime;
        playTone(523.25, t, 0.5);        // C5
        playTone(659.25, t + 0.1, 0.5);  // E5
        playTone(783.99, t + 0.2, 0.5);  // G5
        playTone(1046.50, t + 0.3, 0.6); // C6
      } catch (e) {
        console.log("Audio feedback error or interaction needed:", e);
      }
    }

    // Render cột PREPARING
    const prepGrid = document.getElementById('preparing-grid');
    const prepEmpty = document.getElementById('preparing-empty');
    if (preparingOrders.length === 0) {
      prepGrid.innerHTML = '';
      prepEmpty.style.display = 'flex';
    } else {
      prepEmpty.style.display = 'none';
      prepGrid.innerHTML = preparingOrders.map(o => `
        <div class="card">
          <div class="card-number">#${o.queue_no}</div>
          <div class="card-label">Đang chế biến</div>
        </div>
      `).join('');
    }
    
  } catch(e){
    console.error("Refresh loop error:", e);
  }
}

// Chạy lần đầu và thiết lập vòng lặp
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""
    return html


@app.get("/")
async def root():
    return {"service": "Smart QR Payment Backend", "tv": "/tv",
            "device_current": "/api/device/current"}
