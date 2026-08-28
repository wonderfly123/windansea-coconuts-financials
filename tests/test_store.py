import sqlite3
from src import store

def test_init_creates_tables():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"transactions", "balances", "meta"} <= names

def test_upsert_transaction_dedups_by_id():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    row = {"id": "t1", "source": "Mercury", "account": "a", "date": "2026-01-05",
           "counterparty": "Square Inc", "description": "Square Inc; SQ123",
           "category": "Revenue", "amount": 100.0, "bucket": "Revenue",
           "flag": None, "review": None, "raw_json": "{}"}
    store.upsert_transaction(conn, row)
    store.upsert_transaction(conn, {**row, "amount": 100.0})  # same id again
    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 1

def test_set_and_get_meta():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    store.set_meta(conn, "last_refresh", "2026-06-19")
    assert store.get_meta(conn, "last_refresh") == "2026-06-19"
