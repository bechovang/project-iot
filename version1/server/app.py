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


@app.get("/q/{queue_no}")
async def redirect_short_link(queue_no: int):
    """Chuyen huong tu link rut gon tren ESP32 sang trang thanh toan PayOS thuc te."""
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
    # PUBLIC_BASE_URL contains the ngrok endpoint
    short_url = f"{PUBLIC_BASE_URL}/q/{o['queue_no']}" if PUBLIC_BASE_URL else f"http://127.0.0.1:8000/q/{o['queue_no']}"
    
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
<title>Hang doi don - Smart QR</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, Arial, sans-serif; background:#0f172a; color:#e2e8f0;
         padding: 28px; }
  h1 { font-size: 34px; margin-bottom: 6px; }
  .sub { color:#94a3b8; margin-bottom: 22px; }
  .grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr));
          gap:16px; }
  .card { border-radius:16px; padding:18px 20px; background:#1e293b;
          border:2px solid #334155; }
  .card.paid { background:#064e3b; border-color:#10b981; }
  .card.pending { background:#1e293b; border-color:#f59e0b; }
  .no { font-size:42px; font-weight:800; }
  .amt { font-size:22px; margin-top:4px; }
  .st { margin-top:10px; font-size:16px; font-weight:700; letter-spacing:1px; }
  .st.pending { color:#fbbf24; }
  .st.paid { color:#34d399; }
  .empty { color:#64748b; font-size:20px; margin-top:40px; }
</style>
</head>
<body>
  <h1>Smart QR Payment</h1>
  <div class="sub">Danh sach don hom nay - cap nhat tu dong</div>
  <div id="grid" class="grid"></div>
  <div id="empty" class="empty" style="display:none">Chua co don nao.</div>
<script>
function fmt(n){ return n.toLocaleString('vi-VN'); }
async function refresh(){
  try {
    const r = await fetch('/api/orders');
    const data = await r.json();
    const grid = document.getElementById('grid');
    const empty = document.getElementById('empty');
    const list = data.filter(o => o.status !== 'CANCELLED');
    if(list.length === 0){ grid.innerHTML=''; empty.style.display='block'; return; }
    empty.style.display='none';
    grid.innerHTML = list.map(o => {
      const paid = o.status === 'PAID';
      return `<div class="card ${paid?'paid':'pending'}">
        <div class="no">#${o.queue_no}</div>
        <div class="amt">${fmt(o.amount)} d</div>
        <div class="st ${paid?'paid':'pending'}">${paid?'DA THANH TOAN':'CHO THANH TOAN'}</div>
      </div>`;
    }).join('');
  } catch(e){ console.error(e); }
}
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
