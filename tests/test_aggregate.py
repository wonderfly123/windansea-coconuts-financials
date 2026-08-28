import sqlite3
from src import store, aggregate
from src import constants as k


def seed(conn, rows):
    for r in rows:
        store.upsert_transaction(conn, {"flag": None, "review": None,
            "raw_json": "{}", "category": "", "counterparty": "", "description": "", **r})


def test_monthly_revenue_and_expense_split():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"Mercury","account":"a","date":"2026-01-10","amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"Ramp","account":"r","date":"2026-01-12","amount":-400.0,"bucket":k.BUCKET_OPERATING},
        {"id":"3","source":"Mercury","account":"a","date":"2026-02-10","amount":2000.0,"bucket":k.BUCKET_REVENUE},
    ])
    m = aggregate.monthly(conn)
    assert m["2026-01"]["revenue"] == 1000.0
    assert m["2026-01"]["expense"] == 400.0
    assert m["2026-01"]["net"] == 600.0


def test_average_excludes_partial_june_by_default():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"Mercury","account":"a","date":"2026-01-10","amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"Mercury","account":"a","date":"2026-06-05","amount":50.0,"bucket":k.BUCKET_REVENUE},
    ])
    avg = aggregate.averages(conn, start="2026-01", end="2026-05")
    assert avg["revenue_avg"] == 1000.0


def test_monthly_all_buckets_positive_and_net():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-03-01","amount":5000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"s","account":"a","date":"2026-03-02","amount":-1000.0,"bucket":k.BUCKET_OPERATING},
        {"id":"3","source":"s","account":"a","date":"2026-03-03","amount":-800.0,"bucket":k.BUCKET_PAYROLL},
        {"id":"4","source":"s","account":"a","date":"2026-03-04","amount":-500.0,"bucket":k.BUCKET_OWNER_PAY},
        {"id":"5","source":"s","account":"a","date":"2026-03-05","amount":-200.0,"bucket":k.BUCKET_OWNER_DRAW},
    ])
    m = aggregate.monthly(conn)["2026-03"]
    assert m["revenue"] == 5000.0
    assert m["expense"] == 1000.0
    assert m["payroll"] == 800.0
    assert m["owner_pay"] == 500.0
    assert m["owner_draw"] == 200.0
    # net = 5000 - (1000 + 800 + 500 + 200) = 2500
    assert m["net"] == 2500.0


def test_excluded_rows_never_counted():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-04-01","amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"s","account":"a","date":"2026-04-02","amount":-9999.0,"bucket":k.BUCKET_EXCLUDED},
        {"id":"3","source":"s","account":"a","date":"2026-04-03","amount":5555.0,"bucket":k.BUCKET_EXCLUDED},
    ])
    m = aggregate.monthly(conn)["2026-04"]
    assert m["revenue"] == 1000.0
    assert m["expense"] == 0.0
    assert m["net"] == 1000.0


def test_excluded_only_month_still_omitted_from_totals():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-05-01","amount":-100.0,"bucket":k.BUCKET_EXCLUDED},
    ])
    m = aggregate.monthly(conn)
    # month has no non-excluded transaction -> not included
    assert "2026-05" not in m


def test_ytd_cumulative_includes_partial_june():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-01-10","amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"s","account":"a","date":"2026-01-11","amount":-300.0,"bucket":k.BUCKET_OPERATING},
        {"id":"3","source":"s","account":"a","date":"2026-06-05","amount":500.0,"bucket":k.BUCKET_REVENUE},
        {"id":"4","source":"s","account":"a","date":"2026-06-06","amount":-100.0,"bucket":k.BUCKET_PAYROLL},
        {"id":"5","source":"s","account":"a","date":"2026-06-07","amount":-9999.0,"bucket":k.BUCKET_EXCLUDED},
    ])
    y = aggregate.ytd(conn)
    assert y["revenue"] == 1500.0
    assert y["expense"] == 300.0
    assert y["payroll"] == 100.0
    assert y["owner_pay"] == 0.0
    assert y["owner_draw"] == 0.0
    # net = 1500 - (300 + 100 + 0 + 0) = 1100
    assert y["net"] == 1100.0


def test_current_cash_sums_balances():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    store.upsert_balance(conn, "mercury-1", "Mercury Checking", 12000.0, "2026-06-19")
    store.upsert_balance(conn, "mercury-2", "Mercury Savings", 8000.0, "2026-06-19")
    store.upsert_balance(conn, "ramp-1", "Ramp", 500.0, "2026-06-19")
    assert aggregate.current_cash(conn) == 20500.0


def test_averages_revenue_expense_net():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-01-10","amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"s","account":"a","date":"2026-01-11","amount":-200.0,"bucket":k.BUCKET_OPERATING},
        {"id":"3","source":"s","account":"a","date":"2026-02-10","amount":3000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"4","source":"s","account":"a","date":"2026-02-11","amount":-800.0,"bucket":k.BUCKET_OPERATING},
    ])
    avg = aggregate.averages(conn, start="2026-01", end="2026-02")
    assert avg["revenue_avg"] == 2000.0
    assert avg["expense_avg"] == 500.0
    # net jan = 800, net feb = 2200 -> avg 1500
    assert avg["net_avg"] == 1500.0


def test_runway_burning_branch():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-01-10","amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"s","account":"a","date":"2026-01-11","amount":-3000.0,"bucket":k.BUCKET_OPERATING},
    ])
    # net_avg = 1000 - 3000 = -2000 (burning)
    r = aggregate.runway(conn, current_cash=10000.0, start="2026-01", end="2026-01")
    assert r["is_burning"] is True
    assert r["months"] == 5.0
    assert r["monthly_change"] == -2000.0
    assert "-" not in r["label"]
    assert "runway" in r["label"]


def test_runway_profitable_branch():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-01-10","amount":5000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"s","account":"a","date":"2026-01-11","amount":-1000.0,"bucket":k.BUCKET_OPERATING},
    ])
    # net_avg = 4000 (profitable)
    r = aggregate.runway(conn, current_cash=10000.0, start="2026-01", end="2026-01")
    assert r["is_burning"] is False
    assert r["months"] is None
    assert r["monthly_change"] == 4000.0
    assert "-" not in r["label"]
    assert "growing" in r["label"]


def test_owner_comp_reads_flags_and_meta():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    store.set_meta(conn, k.META_HARRISON_W2_GROSS, "42000.0")
    seed(conn, [
        {"id":"1","source":"s","account":"a","date":"2026-01-10","amount":-600.0,
         "bucket":k.BUCKET_OWNER_DRAW,"flag":k.FLAG_OWNER_CAR},
        {"id":"2","source":"s","account":"a","date":"2026-02-10","amount":-600.0,
         "bucket":k.BUCKET_OWNER_DRAW,"flag":k.FLAG_OWNER_CAR},
        {"id":"3","source":"s","account":"a","date":"2026-01-15","amount":-2000.0,
         "bucket":k.BUCKET_OWNER_DRAW,"flag":k.FLAG_OWNER_DRAW_BOFA},
        {"id":"4","source":"s","account":"a","date":"2026-01-20","amount":-1500.0,
         "bucket":k.BUCKET_OWNER_PAY,"flag":k.FLAG_HARRISON_DIRECT},
    ])
    oc = aggregate.owner_comp(conn)
    assert oc["jordan"]["capital_one"] == 1200.0
    assert oc["jordan"]["bofa_draw"] == 2000.0
    assert oc["jordan"]["total"] == 3200.0
    assert oc["harrison"]["adp_w2"] == 42000.0
    assert oc["harrison"]["direct"] == 1500.0
    assert oc["harrison"]["total"] == 43500.0


def test_owner_comp_missing_meta_defaults_zero():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    oc = aggregate.owner_comp(conn)
    assert oc["harrison"]["adp_w2"] == 0.0
    assert oc["harrison"]["direct"] == 0.0
    assert oc["harrison"]["total"] == 0.0
    assert oc["jordan"]["total"] == 0.0
