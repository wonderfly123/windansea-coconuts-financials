import os
import sqlite3

from src import reconcile, store
from src import constants as k

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
MERCURY = os.path.join(FIX, "mercury_sample.json")
RAMP = os.path.join(FIX, "ramp_sample.json")
SQUARE = os.path.join(FIX, "square_sample.json")
ADP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "PayrollSummary.xlsx")

MERCURY_BALANCES = [
    {"account": "acct-checking", "name": "SoCal Checking", "balance": 10643.07, "as_of": "2026-06-19"},
]
RAMP_BALANCE = {"balance": 28288.41, "as_of": "2026-06-19"}


def _run():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    reconcile.run(conn, MERCURY, RAMP, ADP, MERCURY_BALANCES, RAMP_BALANCE,
                  square_path=SQUARE)
    return conn


def test_square_payout_ingested_as_revenue():
    conn = _run()
    row = conn.execute(
        "SELECT source, bucket, amount FROM transactions WHERE id='square:po-sample-1'"
    ).fetchone()
    assert row == ("Square", k.BUCKET_REVENUE, 2500.0)


def test_mercury_square_deposit_is_excluded_not_double_counted():
    conn = _run()
    # the Square deposit in the Mercury fixture must be Excluded (counted via Square)
    b = conn.execute(
        "SELECT bucket FROM transactions WHERE id='m-square-1'"
    ).fetchone()
    assert b is not None and b[0] == k.BUCKET_EXCLUDED


def test_mercury_deduped_by_id():
    conn = _run()
    rows = conn.execute("SELECT description FROM transactions WHERE id='m-dup-1'").fetchall()
    assert len(rows) == 1
    # last one wins
    assert "SECOND COPY WINS" in rows[0][0]


def test_failed_rows_dropped():
    conn = _run()
    rows = conn.execute("SELECT * FROM transactions WHERE id='m-failed-1'").fetchall()
    assert rows == []


def test_excluded_rows_are_stored_not_deleted():
    conn = _run()
    n = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE bucket=?", [k.BUCKET_EXCLUDED]
    ).fetchone()[0]
    assert n >= 1
    # the internal transfer specifically is stored as Excluded
    b = conn.execute(
        "SELECT bucket FROM transactions WHERE id='m-internal-1'"
    ).fetchone()[0]
    assert b == k.BUCKET_EXCLUDED


def test_revenue_total_positive():
    conn = _run()
    total = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE bucket=?", [k.BUCKET_REVENUE]
    ).fetchone()[0]
    assert total is not None and total > 0


def test_ramp_pending_carries_review_note():
    conn = _run()
    review = conn.execute(
        "SELECT review FROM transactions WHERE id='ramp:r-charge-1'"
    ).fetchone()[0]
    assert review == "Ramp PENDING, not yet cleared"
    # cleared ramp row should NOT carry the pending note
    cleared = conn.execute(
        "SELECT review FROM transactions WHERE id='ramp:r-refund-1'"
    ).fetchone()[0]
    assert cleared != "Ramp PENDING, not yet cleared"


def test_ramp_synthetic_id_namespaced():
    conn = _run()
    rows = conn.execute(
        "SELECT id, source FROM transactions WHERE source='Ramp'"
    ).fetchall()
    assert all(rid.startswith("ramp:") for rid, _ in rows)


def test_harrison_w2_meta_is_number():
    conn = _run()
    raw = store.get_meta(conn, k.META_HARRISON_W2_GROSS)
    assert raw is not None
    val = float(raw)
    assert val == 13000.0


def test_adp_variance_meta_exists():
    conn = _run()
    raw = store.get_meta(conn, k.META_ADP_VARIANCE)
    assert raw is not None
    float(raw)  # must parse as a number


def test_balances_upserted():
    conn = _run()
    n = conn.execute("SELECT COUNT(*) FROM balances").fetchone()[0]
    # one mercury + one ramp
    assert n == 2
    ramp = conn.execute("SELECT balance FROM balances WHERE account='ramp'").fetchone()
    assert ramp[0] == 28288.41


def test_window_meta_set():
    conn = _run()
    assert store.get_meta(conn, k.META_WINDOW_START) == "2026-01-01"
    assert store.get_meta(conn, k.META_WINDOW_END) is not None


def test_jun_adp_payroll_draft_from_ramp_is_payroll_not_excluded(tmp_path):
    import json, sqlite3
    from src import reconcile, store
    from src import constants as k
    # The June 15 ADP payroll run was drafted from the Ramp checking account on
    # 2026-06-13 (unlabeled outflow). It must land in Payroll, not be excluded as
    # a "card paydown". (Owner confirmed it is payroll; banking moved off Mercury.)
    wallet = [{"date": "2026-06-13", "amount": 6432.23,
               "source_account_name": "Checking Account", "memo": None}]
    rw = tmp_path / "rw.json"; rw.write_text(json.dumps(wallet))
    mp = tmp_path / "m.json"; mp.write_text("[]")
    rp = tmp_path / "r.json"; rp.write_text("[]")
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    reconcile.run(conn, str(mp), str(rp), "PayrollSummary.xlsx", [],
                  {"balance": 0}, ramp_wallet_path=str(rw))
    row = conn.execute(
        "SELECT amount, bucket FROM transactions WHERE id='rampw:2026-06-13:0'"
    ).fetchone()
    assert row == (-6432.23, k.BUCKET_PAYROLL)


def test_jun1_3400_transfer_is_split_2000_jordan_1400_harrison(tmp_path):
    import json, sqlite3
    from src import reconcile, store
    from src import constants as k
    merc = [{"id": "abc", "status": "sent", "amount": -3400.0, "kind": "externalTransfer",
             "postedAt": "2026-06-01T14:40:27Z",
             "bankDescription": "Transfer from Mercury to another bank account",
             "counterpartyName": "Bank of America - Checking ••4201", "account": "a"}]
    mp = tmp_path / "m.json"; mp.write_text(json.dumps(merc))
    rp = tmp_path / "r.json"; rp.write_text("[]")
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    reconcile.run(conn, str(mp), str(rp), "PayrollSummary.xlsx", [], {"balance": 0})
    got = {(r[0], r[1], r[2], r[3]) for r in
           conn.execute("SELECT id, amount, bucket, flag FROM transactions")}
    assert ("abc:car", -2000.0, k.BUCKET_OWNER_DRAW, k.FLAG_OWNER_DRAW_BOFA) in got
    assert ("abc:harrison", -1400.0, k.BUCKET_OWNER_PAY, k.FLAG_HARRISON_DIRECT) in got
    # the original $3,400 line is NOT stored (no double count)
    assert conn.execute("SELECT COUNT(*) FROM transactions WHERE amount=-3400").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2
