import sqlite3
from src import store
from src.dashboard import serve
from src import constants as k


def _seed_basic(db_path):
    conn = sqlite3.connect(str(db_path))
    store.init_db(conn)
    store.upsert_transaction(conn, {"id": "1", "source": "Mercury", "account": "a",
        "date": "2026-01-10", "counterparty": "Square Inc", "description": "SQ",
        "category": "Revenue", "amount": 1000.0, "bucket": k.BUCKET_REVENUE, "flag": None,
        "review": None, "raw_json": "{}"})
    store.upsert_balance(conn, "a", "Operating", 5000.0, "2026-06-19")
    conn.commit()
    conn.close()


def test_summary_endpoint_returns_squares(tmp_path):
    db = tmp_path / "t.db"
    _seed_basic(db)
    app = serve.create_app(str(db))
    client = app.test_client()
    r = client.get("/api/summary?start=2026-01&end=2026-05")
    j = r.get_json()
    assert "current_cash" in j and "revenue_avg" in j and "net_avg" in j
    assert j["cash_on_the_way"] == "TBD"


def test_summary_shape_full(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    store.init_db(conn)
    store.upsert_transaction(conn, {"id": "1", "source": "Mercury", "account": "a",
        "date": "2026-01-10", "counterparty": "Square Inc", "description": "SQ",
        "category": "Revenue", "amount": 1000.0, "bucket": k.BUCKET_REVENUE, "flag": None,
        "review": None, "raw_json": "{}"})
    store.upsert_transaction(conn, {"id": "2", "source": "Ramp", "account": "r",
        "date": "2026-01-12", "counterparty": "Adobe", "description": "Software",
        "category": "Software", "amount": -200.0, "bucket": k.BUCKET_OPERATING, "flag": None,
        "review": None, "raw_json": "{}"})
    store.upsert_transaction(conn, {"id": "3", "source": "Mercury", "account": "a",
        "date": "2026-06-05", "counterparty": "Square Inc", "description": "SQ",
        "category": "Revenue", "amount": 50.0, "bucket": k.BUCKET_REVENUE, "flag": None,
        "review": None, "raw_json": "{}"})
    store.upsert_balance(conn, "a", "Operating", 5000.0, "2026-06-19")
    conn.commit()
    conn.close()
    app = serve.create_app(str(db))
    client = app.test_client()
    j = client.get("/api/summary?start=2026-01&end=2026-05").get_json()
    # monthly present and ordered, June flagged partial
    months = [m["month"] for m in j["monthly"]]
    assert months == sorted(months)
    june = [m for m in j["monthly"] if m["month"] == "2026-06"][0]
    assert june["is_partial"] is True
    jan = [m for m in j["monthly"] if m["month"] == "2026-01"][0]
    assert jan["is_partial"] is False
    # categories present, abs amounts
    assert any(c["category"] == "Software" and c["amount"] == 200.0 for c in j["categories"])
    # ytd / owner_comp keys
    assert "revenue" in j["ytd"]
    assert "jordan" in j["owner_comp"] and "harrison" in j["owner_comp"]
    # takeaways are 3 to 5 sentences with no dashes
    assert 3 <= len(j["takeaways"]) <= 5
    for t in j["takeaways"]:
        assert "-" not in t


def test_index_renders(tmp_path):
    db = tmp_path / "t.db"
    _seed_basic(db)
    app = serve.create_app(str(db))
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert b"Windansea Coconuts" in r.data


def test_transactions_filter(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    store.init_db(conn)
    store.upsert_transaction(conn, {"id": "1", "source": "Mercury", "account": "a",
        "date": "2026-01-10", "counterparty": "Square Inc", "description": "deposit",
        "category": "Revenue", "amount": 1000.0, "bucket": k.BUCKET_REVENUE, "flag": None,
        "review": None, "raw_json": "{}"})
    store.upsert_transaction(conn, {"id": "2", "source": "Ramp", "account": "r",
        "date": "2026-01-12", "counterparty": "Adobe", "description": "software sub",
        "category": "Software", "amount": -200.0, "bucket": k.BUCKET_OPERATING, "flag": None,
        "review": None, "raw_json": "{}"})
    store.upsert_transaction(conn, {"id": "3", "source": "Ramp", "account": "r",
        "date": "2026-02-12", "counterparty": "AWS", "description": "cloud",
        "category": "Software", "amount": -300.0, "bucket": k.BUCKET_OPERATING, "flag": None,
        "review": None, "raw_json": "{}"})
    conn.commit()
    conn.close()
    app = serve.create_app(str(db))
    client = app.test_client()

    all_rows = client.get("/api/transactions").get_json()
    assert len(all_rows) == 3

    q_rows = client.get("/api/transactions?q=adobe").get_json()
    assert len(q_rows) == 1 and q_rows[0]["counterparty"] == "Adobe"

    bucket_rows = client.get("/api/transactions?bucket=%s" % k.BUCKET_OPERATING).get_json()
    assert len(bucket_rows) == 2
    assert all(r["bucket"] == k.BUCKET_OPERATING for r in bucket_rows)

    combo = client.get("/api/transactions?q=cloud&bucket=%s" % k.BUCKET_OPERATING).get_json()
    assert len(combo) == 1 and combo[0]["counterparty"] == "AWS"


def test_questions_save_list_delete(tmp_path):
    import sqlite3
    from src import store
    db = tmp_path / "q.db"
    conn = sqlite3.connect(str(db)); store.init_db(conn); conn.close()
    app = serve.create_app(str(db))
    client = app.test_client()
    assert client.post("/api/questions", json={"text": "   "}).status_code == 400
    assert client.post("/api/questions", json={"text": "why is May high?"}).get_json()["ok"]
    items = client.get("/api/questions").get_json()
    assert len(items) == 1 and items[0]["text"] == "why is May high?"
    client.delete("/api/questions/%d" % items[0]["id"])
    assert client.get("/api/questions").get_json() == []
