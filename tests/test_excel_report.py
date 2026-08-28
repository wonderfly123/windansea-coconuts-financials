import sqlite3, openpyxl
from src import store, excel_report
from src import constants as k


def seed(conn, rows):
    for r in rows:
        store.upsert_transaction(conn, {"flag": None, "review": None,
            "raw_json": "{}", "category": "", "counterparty": "",
            "description": "", **r})


def test_workbook_has_tabs_and_formula_cells(tmp_path):
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    store.upsert_transaction(conn, {"id":"1","source":"Mercury","account":"a",
        "date":"2026-01-10","counterparty":"Square Inc","description":"Square Inc; SQ1",
        "category":"Revenue","amount":1000.0,"bucket":k.BUCKET_REVENUE,"flag":None,
        "review":None,"raw_json":"{}"})
    out = tmp_path / "out.xlsx"
    excel_report.build(conn, str(out))
    wb = openpyxl.load_workbook(out)
    assert {"Transactions", "Monthly Summary"} <= set(wb.sheetnames)
    ms = wb["Monthly Summary"]
    formulas = [c.value for row in ms.iter_rows() for c in row
                if isinstance(c.value, str) and c.value.startswith("=")]
    assert formulas, "Monthly Summary must use formulas"


def test_formula_strings_and_txn_row_count(tmp_path):
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    store.set_meta(conn, k.META_HARRISON_W2_GROSS, "42000.0")
    rows = [
        {"id":"1","source":"Mercury","account":"a","date":"2026-01-10",
         "amount":1000.0,"bucket":k.BUCKET_REVENUE},
        {"id":"2","source":"Ramp","account":"r","date":"2026-01-12",
         "amount":-400.0,"bucket":k.BUCKET_OPERATING},
        {"id":"3","source":"ADP","account":"a","date":"2026-02-15",
         "amount":-800.0,"bucket":k.BUCKET_PAYROLL},
        {"id":"4","source":"s","account":"a","date":"2026-02-20",
         "amount":-500.0,"bucket":k.BUCKET_OWNER_PAY,"flag":k.FLAG_HARRISON_DIRECT},
        {"id":"5","source":"s","account":"a","date":"2026-03-05",
         "amount":-600.0,"bucket":k.BUCKET_OWNER_DRAW,"flag":k.FLAG_OWNER_CAR},
        {"id":"6","source":"s","account":"a","date":"2026-03-06",
         "amount":-2000.0,"bucket":k.BUCKET_OWNER_DRAW,"flag":k.FLAG_OWNER_DRAW_BOFA},
        {"id":"7","source":"s","account":"a","date":"2026-04-01",
         "amount":-9999.0,"bucket":k.BUCKET_EXCLUDED},
    ]
    seed(conn, rows)
    out = tmp_path / "out.xlsx"
    excel_report.build(conn, str(out))
    wb = openpyxl.load_workbook(out)

    # Transactions tab: one data row per seeded transaction (plus header).
    txns = wb["Transactions"]
    assert txns.max_row == len(rows) + 1

    # Collect every formula across the workbook.
    all_formulas = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    all_formulas.append(c.value)
    blob = "\n".join(all_formulas)
    assert "=SUMIFS" in blob
    assert "SUMPRODUCT" in blob
    # No dashes used as pauses anywhere in formula text criteria.
    # (formulas themselves may contain "<>" and "-" for negation; just sanity
    # check the bucket criteria strings are present)
    assert '"Revenue"' in blob
    assert '"Operating Expense"' in blob
    assert '"<>Excluded"' in blob
