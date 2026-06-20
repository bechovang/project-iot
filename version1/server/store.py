"""
store.py - Luu tru don hang bang SQLite (ben vung qua restart).

Giu nguyen interface nhu ban in-memory truoc day:
  create / get / list / mark_paid / set_status / latest_pending / pop_paid_event
Tat ca tra ve dict (hoac None) voi cung bo key nhu cu.

DB file: orders.db (cung thu muc server). Co the doi qua bien moi truong ORDERS_DB.
"""
import os
import json
import time
import sqlite3
import threading
from typing import Optional

DB_PATH = os.environ.get("ORDERS_DB", os.path.join(os.path.dirname(__file__), "orders.db"))


class OrderStore:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.RLock()
        # check_same_thread=False vi FastAPI/uvicorn co the goi tu nhieu thread;
        # moi truy cap deu boc trong self._lock nen an toan.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_code      INTEGER PRIMARY KEY,
                    queue_no        INTEGER,
                    amount          INTEGER NOT NULL,
                    description     TEXT,
                    items           TEXT,            -- JSON
                    qr_code         TEXT,
                    checkout_url    TEXT,
                    payment_link_id TEXT,
                    status          TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING|PAID|CANCELLED
                    created_at      REAL NOT NULL,
                    paid_at         REAL,
                    paid_event_pending INTEGER NOT NULL DEFAULT 0     -- co bao ESP32 chua "nhan"
                )
            """)
            self._conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        if row is None:
            return None
        return {
            "order_code": row["order_code"],
            "queue_no": row["queue_no"],
            "amount": row["amount"],
            "description": row["description"],
            "items": json.loads(row["items"]) if row["items"] else [],
            "qr_code": row["qr_code"],
            "checkout_url": row["checkout_url"],
            "payment_link_id": row["payment_link_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "paid_at": row["paid_at"],
        }

    def _next_queue_no(self) -> int:
        # So thu tu don trong NGAY hom nay (reset moi ngay) - hop ly cho quan.
        start_of_day = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
        cur = self._conn.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE created_at >= ?", (start_of_day,))
        return int(cur.fetchone()["c"]) + 1

    def create(self, order_code: int, amount: int, description: str,
               items: list, qr_code: str, checkout_url: str,
               payment_link_id: str) -> dict:
        with self._lock:
            queue_no = self._next_queue_no()
            created_at = time.time()
            self._conn.execute("""
                INSERT INTO orders (order_code, queue_no, amount, description, items,
                                    qr_code, checkout_url, payment_link_id, status,
                                    created_at, paid_at, paid_event_pending)
                VALUES (?,?,?,?,?,?,?,?, 'PENDING', ?, NULL, 0)
            """, (order_code, queue_no, int(amount), description,
                  json.dumps(items or [], ensure_ascii=False),
                  qr_code, checkout_url, payment_link_id, created_at))
            self._conn.commit()
            return self.get(order_code)

    def get(self, order_code: int) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM orders WHERE order_code = ?", (order_code,))
            return self._row_to_dict(cur.fetchone())

    def list(self) -> list:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM orders ORDER BY created_at DESC")
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def mark_paid(self, order_code: int) -> Optional[dict]:
        with self._lock:
            o = self.get(order_code)
            if not o:
                return None
            if o["status"] != "PAID":
                self._conn.execute("""
                    UPDATE orders SET status='PAID', paid_at=?, paid_event_pending=1
                    WHERE order_code=?
                """, (time.time(), order_code))
                self._conn.commit()
            return self.get(order_code)

    def set_status(self, order_code: int, status: str) -> Optional[dict]:
        with self._lock:
            self._conn.execute(
                "UPDATE orders SET status=? WHERE order_code=?", (status, order_code))
            self._conn.commit()
            return self.get(order_code)

    def latest_pending(self) -> Optional[dict]:
        """Don PENDING moi nhat - de thiet bi hien QR."""
        with self._lock:
            cur = self._conn.execute("""
                SELECT * FROM orders WHERE status='PENDING'
                ORDER BY created_at DESC LIMIT 1
            """)
            return self._row_to_dict(cur.fetchone())

    def pop_paid_event(self) -> Optional[dict]:
        """
        Tra ve don vua PAID (1 lan duy nhat) de ESP32 phat loa.
        Dung cot paid_event_pending lam co -> ben vung qua restart.
        """
        with self._lock:
            cur = self._conn.execute("""
                SELECT * FROM orders WHERE paid_event_pending=1
                ORDER BY paid_at ASC LIMIT 1
            """)
            row = cur.fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE orders SET paid_event_pending=0 WHERE order_code=?",
                (row["order_code"],))
            self._conn.commit()
            return self._row_to_dict(row)


store = OrderStore()