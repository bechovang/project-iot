"""
cashier.py - Console thu ngan (Streamlit) Pro Max.

Chay:  streamlit run cashier.py
Goi vao backend FastAPI (BACKEND_URL trong .env, mac dinh http://127.0.0.1:8000)
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
    "☕ Cà phê đen":     15000,
    "🥛 Cà phê sữa":     20000,
    "🧊 Bạc xỉu":        25000,
    "🍑 Trà đào":        30000,
    "🧋 Trà sữa trân châu": 35000,
    "🥖 Bánh mì":        20000,
}

st.set_page_config(page_title="Hệ Thống Thu Ngân & Trả Món - Underrated", page_icon="☕", layout="wide")

# CSS custom for Streamlit to look premium
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
    
    /* Global styles */
    .stApp {
        background-color: #0b0f19;
    }
    h1, h2, h3, h4, p, span, label {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Header Gradient styling */
    .main-title {
        background: linear-gradient(135deg, #6ee7b7 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 5px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 25px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Card Container design */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        background: rgba(30, 41, 59, 0.3) !important;
        border-radius: 18px !important;
        padding: 20px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">☕ SMART UNDERRATED MANAGER</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Hệ thống Thu Ngân & Điều Phối Món • Backend: {BACKEND_URL}</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1.1, 1])

# --------------------------------------------------------------------------
#  COT TRAI: tao don
# --------------------------------------------------------------------------
with col_left:
    st.subheader("📝 Lập Đơn Hàng Mới")

    mode = st.radio("Phương thức nhập đơn", ["Menu Chọn Món QuickSelect", "Nhập Số Tiền Tự Do"], horizontal=True)

    items = []
    amount = 0

    if mode == "Menu Chọn Món QuickSelect":
        st.write("Chọn số lượng:")
        # Render menu components in grids of 2 columns
        cols = st.columns(2)
        for i, (name, price) in enumerate(MENU.items()):
            with cols[i % 2]:
                qty = st.number_input(f"{name} ({price:,} đ)", min_value=0,
                                      max_value=50, value=0, step=1, key=f"qty_{name}")
                if qty > 0:
                    items.append({"name": name, "quantity": int(qty), "price": int(price)})
                    amount += int(qty) * int(price)
        st.divider()
        st.metric("TỔNG TIỀN THANH TOÁN", f"{amount:,} đ")
        description = "Đơn " + ", ".join(f"{i['name']}x{i['quantity']}" for i in items) if items else "Thanh toán"
    else:
        amount = st.number_input("Số tiền cần thu (VND)", min_value=1000, max_value=50_000_000,
                                 value=20000, step=5000)
        description = st.text_input("Ghi chú / Nội dung đơn", value="Thanh toan don")
        items = [{"name": description[:25] or "Thanh toán", "quantity": 1, "price": int(amount)}]

    if st.button("✨ TẠO ĐƠN & XUẤT QR THANH TOÁN", type="primary", use_container_width=True):
        if amount <= 0:
            st.error("Vui lòng chọn món hoặc nhập số tiền hợp lệ.")
        else:
            try:
                payload = {"amount": int(amount), "description": description, "items": items}
                r = requests.post(f"{BACKEND_URL}/api/orders", json=payload,
                                  headers=HEADERS, timeout=20)
                if r.status_code == 200:
                    o = r.json()
                    st.session_state["last_order"] = o
                    st.toast(f"Đã xuất hóa đơn #{o['queue_no']} thành công!", icon="✅")
                else:
                    st.error(f"Lỗi {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Không thể kết nối đến máy chủ: {e}")

    # Hien QR don vua tao
    if "last_order" in st.session_state:
        o = st.session_state["last_order"]
        st.divider()
        
        c_qr_info, c_qr_img = st.columns([1, 1])
        with c_qr_info:
            st.markdown(f"### Hóa Đơn **#{o['queue_no']}**")
            st.markdown(f"**Mã giao dịch:** `{o['order_code']}`")
            st.markdown(f"**Tổng thanh toán:** <span style='font-size:20px; font-weight:800; color:#10b981;'>{o['amount']:,} đ</span>", unsafe_allow_html=True)
            if o.get("checkout_url"):
                st.markdown(f"[🔗 Link thanh toán trực tiếp]({o['checkout_url']})")
        with c_qr_img:
            qr = o.get("qr_code", "")
            if qr:
                qr_img = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={requests.utils.quote(qr)}"
                st.image(qr_img, caption="QR chuyển khoản PayOS", width=180)

# --------------------------------------------------------------------------
#  COT PHAI: danh sach don
# --------------------------------------------------------------------------
with col_right:
    st.subheader("📋 Bảng Điều Phối Trạng Thái")
    if st.button("🔄 Làm mới danh sách", use_container_width=True):
        st.toast("Đang tải lại danh sách...", icon="🔄")
    try:
        r = requests.get(f"{BACKEND_URL}/api/orders", timeout=10)
        orders = r.json() if r.status_code == 200 else []
    except Exception as e:
        orders = []
        st.error(f"Không tải được danh sách: {e}")

    if not orders:
        st.info("Hiện tại chưa có đơn hàng nào trong ngày.")
    else:
        pending_orders = [o for o in orders if o["status"] == "PENDING"]
        preparing_orders = [o for o in orders if o["status"] == "PAID"]
        ready_orders = [o for o in orders if o["status"] == "READY"]

        # 1. ĐƠN CHỜ THANH TOÁN (PENDING)
        st.markdown("#### ⏳ Đang chờ khách thanh toán")
        if not pending_orders:
            st.caption("Không có đơn chờ.")
        for o in pending_orders:
            with st.container(border=True):
                c1, c2 = st.columns([2.5, 1.5])
                with c1:
                    st.markdown(f"<span style='font-size:26px; font-weight:800; color:#fbbf24;'>#{o['queue_no']}</span> <span style='font-size:18px; font-weight:600; margin-left:10px;'>{o['amount']:,} đ</span>", unsafe_allow_html=True)
                    st.caption(o.get("description", ""))
                with c2:
                    # Nút to dễ bấm hơn
                    if st.button("HỦY ĐƠN 🗑️", key=f"cancel_{o['order_code']}", use_container_width=True):
                        try:
                            requests.post(f"{BACKEND_URL}/api/orders/{o['order_code']}/cancel",
                                          headers=HEADERS, timeout=10)
                            st.toast(f"Đã hủy đơn #{o['queue_no']}", icon="🗑️")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        # 2. ĐANG CHẾ BIẾN (PAID)
        st.markdown("#### ☕ Đang chế biến (Pha chế)")
        if not preparing_orders:
            st.caption("Pha chế rảnh tay, không có đơn hàng cần làm.")
        for o in preparing_orders:
            with st.container(border=True):
                c1, c2 = st.columns([2.2, 1.8])
                with c1:
                    st.markdown(f"<span style='font-size:28px; font-weight:800; color:#38bdf8;'>#{o['queue_no']}</span> <span style='font-size:18px; font-weight:600; margin-left:10px;'>{o['amount']:,} đ</span>", unsafe_allow_html=True)
                    st.caption(o.get("description", ""))
                with c2:
                    # Nút siêu to, cao và bắt mắt
                    if st.button("🔔 TRẢ MÓN (READY)", key=f"ready_{o['order_code']}", type="primary", use_container_width=True):
                        try:
                            payload = {"status": "READY"}
                            r = requests.post(f"{BACKEND_URL}/api/orders/{o['order_code']}/status",
                                              json=payload, headers=HEADERS, timeout=10)
                            if r.status_code == 200:
                                st.toast(f"Đã gọi món #{o['queue_no']} ra nhận!", icon="🔔")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {r.text}")
                        except Exception as e:
                            st.error(str(e))

        # 3. MỜI NHẬN MÓN (READY)
        st.markdown("#### 🔔 Đang ở quầy chờ khách lấy")
        if not ready_orders:
            st.caption("Chưa có đồ cần trả.")
        for o in ready_orders:
            with st.container(border=True):
                c1, c2 = st.columns([2.2, 1.8])
                with c1:
                    st.markdown(f"<span style='font-size:28px; font-weight:800; color:#34d399;'>#{o['queue_no']}</span> <span style='font-size:18px; font-weight:600; margin-left:10px;'>{o['amount']:,} đ</span>", unsafe_allow_html=True)
                    st.caption(o.get("description", ""))
                with c2:
                    # Nút hoàn thành siêu to, màu nhấn
                    if st.button("✓ HOÀN THÀNH", key=f"done_{o['order_code']}", use_container_width=True):
                        try:
                            payload = {"status": "DONE"}
                            r = requests.post(f"{BACKEND_URL}/api/orders/{o['order_code']}/status",
                                              json=payload, headers=HEADERS, timeout=10)
                            if r.status_code == 200:
                                st.toast(f"Hoàn tất đơn #{o['queue_no']}", icon="✅")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {r.text}")
                        except Exception as e:
                            st.error(str(e))

st.divider()
st.caption("Màn hình hiển thị TV dành cho khách hàng: " + f"{BACKEND_URL}/tv")

