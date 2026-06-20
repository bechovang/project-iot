"""
cashier.py - Console thu ngan (Streamlit).

Chay:  streamlit run cashier.py
Goi vao backend FastAPI (BACKEND_URL trong .env, mac dinh http://127.0.0.1:8000)

Chuc nang:
  - Menu mon co san + so luong -> tinh tong tien
  - Hoac nhap so tien tu do
  - Tao don -> backend goi PayOS -> hien QR + checkout link
  - Xem danh sach don, trang thai PAID/PENDING (auto refresh)
"""
import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = (os.environ.get("BACKEND_URL") or "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.environ.get("API_TOKEN", "").strip()

HEADERS = {"Content-Type": "application/json"}
if API_TOKEN:
    HEADERS["x-api-token"] = API_TOKEN

# Menu mau kieu quan cafe
MENU = {
    "Ca phe den":     15000,
    "Ca phe sua":     20000,
    "Bac xiu":        25000,
    "Tra dao":        30000,
    "Tra sua tran chau": 35000,
    "Banh mi":        20000,
}

st.set_page_config(page_title="Cashier - Smart QR", page_icon="*", layout="wide")
st.title("Smart QR Payment - Quay thu ngan")
st.caption(f"Backend: {BACKEND_URL}")

col_left, col_right = st.columns([1, 1])

# --------------------------------------------------------------------------
#  COT TRAI: tao don
# --------------------------------------------------------------------------
with col_left:
    st.subheader("Tao don moi")

    mode = st.radio("Kieu nhap", ["Chon mon", "Nhap so tien tu do"], horizontal=True)

    items = []
    amount = 0

    if mode == "Chon mon":
        st.write("Chon so luong cho tung mon:")
        for name, price in MENU.items():
            qty = st.number_input(f"{name} ({price:,} d)", min_value=0,
                                  max_value=50, value=0, step=1, key=f"qty_{name}")
            if qty > 0:
                items.append({"name": name, "quantity": int(qty), "price": int(price)})
                amount += int(qty) * int(price)
        st.metric("Tong tien", f"{amount:,} d")
        description = "Don " + ", ".join(f"{i['name']}x{i['quantity']}" for i in items) if items else "Thanh toan"
    else:
        amount = st.number_input("So tien (VND)", min_value=1000, max_value=50_000_000,
                                 value=11000, step=1000)
        description = st.text_input("Mo ta (toi da 25 ky tu)", value="Thanh toan don")
        items = [{"name": description[:25] or "Thanh toan", "quantity": 1, "price": int(amount)}]

    if st.button("TAO DON & QR", type="primary", use_container_width=True):
        if amount <= 0:
            st.error("Vui long chon mon hoac nhap so tien.")
        else:
            try:
                payload = {"amount": int(amount), "description": description, "items": items}
                r = requests.post(f"{BACKEND_URL}/api/orders", json=payload,
                                  headers=HEADERS, timeout=20)
                if r.status_code == 200:
                    o = r.json()
                    st.session_state["last_order"] = o
                    st.success(f"Da tao don #{o['queue_no']} - {o['amount']:,} d")
                else:
                    st.error(f"Loi {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Khong goi duoc backend: {e}")

    # Hien QR don vua tao
    if "last_order" in st.session_state:
        o = st.session_state["last_order"]
        st.divider()
        st.write(f"**Don #{o['queue_no']}** - ma {o['order_code']}")
        st.write(f"So tien: **{o['amount']:,} d**")
        qr = o.get("qr_code", "")
        if qr:
            # Render QR tu chuoi EMVCo bang dich vu anh QR cong khai (chi de xem tren web cashier)
            qr_img = f"https://api.qrserver.com/v1/create-qr-code/?size=260x260&data={requests.utils.quote(qr)}"
            st.image(qr_img, caption="Quet de thanh toan (PayOS)", width=260)
        if o.get("checkout_url"):
            st.markdown(f"[Mo trang thanh toan PayOS]({o['checkout_url']})")

# --------------------------------------------------------------------------
#  COT PHAI: danh sach don
# --------------------------------------------------------------------------
with col_right:
    st.subheader("Danh sach don")
    if st.button("Lam moi", use_container_width=True):
        pass
    try:
        r = requests.get(f"{BACKEND_URL}/api/orders", timeout=10)
        orders = r.json() if r.status_code == 200 else []
    except Exception as e:
        orders = []
        st.error(f"Khong tai duoc danh sach: {e}")

    if not orders:
        st.info("Chua co don nao.")
    for o in orders:
        status = o["status"]
        icon = {"PAID": "[DA TT]", "PENDING": "[CHO]", "CANCELLED": "[HUY]"}.get(status, status)
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            c1.markdown(f"### #{o['queue_no']}")
            c2.write(f"{o['amount']:,} d")
            c2.caption(o.get("description", ""))
            c3.write(icon)
            if status == "PENDING":
                if c3.button("Huy", key=f"cancel_{o['order_code']}"):
                    try:
                        requests.post(f"{BACKEND_URL}/api/orders/{o['order_code']}/cancel",
                                      headers=HEADERS, timeout=10)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

st.divider()
st.caption("Trang TV cho khach: " + f"{BACKEND_URL}/tv")
