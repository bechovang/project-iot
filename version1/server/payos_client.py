"""
payos_client.py - Goi PayOS REST API truc tiep.

LY DO khong dung wrapper createPaymentLink() cua SDK 0.1.4:
  PayOS production hien tra them field moi (vd expiredAt) khien dataclass
  CreatePaymentResult/WebhookData cua SDK 0.1.4 vo ("unexpected keyword argument").
  -> Ta goi REST truc tiep va CHI tai dung 2 ham ky chu ky chuan tu payos.utils
     (thuat toan HMAC_SHA256 dung) nen mien nhiem khi PayOS them field.

Tham chieu: https://api-merchant.payos.vn
"""
import os
import random
import time
import requests
from dotenv import load_dotenv

# Tai dung thuat toan ky chu ky chuan tu SDK (khong phu thuoc dataclass)
from payos.utils import createSignatureFromObj, createSignatureOfPaymentRequest

load_dotenv()

PAYOS_BASE_URL = "https://api-merchant.payos.vn"
CLIENT_ID = os.environ.get("PAYOS_CLIENT_ID", "")
API_KEY = os.environ.get("PAYOS_API_KEY", "")
CHECKSUM_KEY = os.environ.get("PAYOS_CHECKSUM_KEY", "")
PUBLIC_BASE_URL = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")


def _headers():
    return {
        "Content-Type": "application/json",
        "x-client-id": CLIENT_ID,
        "x-api-key": API_KEY,
    }


def gen_order_code() -> int:
    # orderCode phai la so nguyen duy nhat (Int). timestamp giay * 100 + random.
    return int(time.time()) * 100 + random.randint(0, 99)


def _verify_data_signature(data: dict, signature: str) -> bool:
    if data is None or signature is None:
        return False
    return createSignatureFromObj(data, CHECKSUM_KEY) == signature


def create_payment(amount: int, description: str, items: list) -> dict:
    """Tao payment link. Tra ve dict gon de luu vao store."""
    order_code = gen_order_code()
    desc = (description or "Thanh toan")[:25]  # PayOS gioi han 25 ky tu

    return_url = f"{PUBLIC_BASE_URL}/paid" if PUBLIC_BASE_URL else "http://localhost:8000/paid"
    cancel_url = f"{PUBLIC_BASE_URL}/cancelled" if PUBLIC_BASE_URL else "http://localhost:8000/cancelled"

    body = {
        "orderCode": order_code,
        "amount": int(amount),
        "description": desc,
        "cancelUrl": cancel_url,
        "returnUrl": return_url,
        "items": [
            {"name": i["name"], "quantity": int(i.get("quantity", 1)), "price": int(i["price"])}
            for i in (items or [])
        ] or [{"name": desc, "quantity": 1, "price": int(amount)}],
    }

    # Chu ky: amount&cancelUrl&description&orderCode&returnUrl (sort alphabet)
    sig_str = (f"amount={body['amount']}&cancelUrl={cancel_url}"
               f"&description={desc}&orderCode={order_code}&returnUrl={return_url}")
    import hashlib, hmac
    body["signature"] = hmac.new(CHECKSUM_KEY.encode(), sig_str.encode(),
                                 hashlib.sha256).hexdigest()

    r = requests.post(f"{PAYOS_BASE_URL}/v2/payment-requests",
                      json=body, headers=_headers(), timeout=20)
    r.raise_for_status()
    res = r.json()
    if res.get("code") != "00":
        raise RuntimeError(f"PayOS {res.get('code')}: {res.get('desc')}")

    data = res["data"]
    # (tuy chon) kiem tra chu ky response
    if res.get("signature") and not _verify_data_signature(data, res["signature"]):
        raise RuntimeError("PayOS response signature mismatch")

    return {
        "order_code": int(data.get("orderCode", order_code)),
        "amount": int(data.get("amount", amount)),
        "description": data.get("description", desc),
        "qr_code": data.get("qrCode", ""),
        "checkout_url": data.get("checkoutUrl", ""),
        "payment_link_id": data.get("paymentLinkId", ""),
    }


def get_status(order_code: int) -> str:
    r = requests.get(f"{PAYOS_BASE_URL}/v2/payment-requests/{order_code}",
                     headers=_headers(), timeout=15)
    if r.status_code != 200:
        return "UNKNOWN"
    res = r.json()
    if res.get("code") != "00" or res.get("data") is None:
        return "UNKNOWN"
    return res["data"].get("status", "UNKNOWN")


def cancel(order_code: int, reason: str = "Huy boi thu ngan"):
    r = requests.post(f"{PAYOS_BASE_URL}/v2/payment-requests/{order_code}/cancel",
                      json={"cancellationReason": reason}, headers=_headers(), timeout=15)
    return r.json()


def verify_webhook(body: dict) -> dict:
    """
    Verify chu ky webhook. Tra ve dict 'data' neu hop le, raise neu sai.
    body = {"code","desc","success","data":{...},"signature":"..."}
    """
    data = body.get("data")
    signature = body.get("signature")
    if data is None:
        raise ValueError("webhook: no data")
    if signature is None:
        raise ValueError("webhook: no signature")
    if not _verify_data_signature(data, signature):
        raise ValueError("webhook: signature mismatch")
    return data