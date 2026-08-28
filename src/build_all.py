"""One command to rebuild everything from the raw pulls.

Reconciles the raw MCP data plus the ADP export into data/coconuts.db, then
generates the Excel workbook. The Flask dashboard reads the same DB live, so it
does not need regenerating, just restart the server.

Run:  .venv/bin/python -m src.build_all
"""

import os
import sqlite3

from src import reconcile, store, excel_report, aggregate

DB_PATH = "data/coconuts.db"
XLSX_PATH = "windansea_coconuts_financials.xlsx"


def main(db_path: str = DB_PATH, xlsx_path: str = XLSX_PATH) -> None:
    # Rebuild the reconciled data fresh, but PRESERVE the questions table so the
    # owner's typed questions survive a refresh. We clear only the financial
    # tables rather than deleting the whole DB file.
    conn = sqlite3.connect(db_path)
    store.init_db(conn)
    for table in ("transactions", "balances", "meta"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    reconcile.run_from_disk(conn)

    excel_report.build(conn, xlsx_path)

    # Console State of the Union.
    counts = dict(
        conn.execute(
            "SELECT bucket, COUNT(*) FROM transactions GROUP BY bucket"
        ).fetchall()
    )
    reviews = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE review IS NOT NULL"
    ).fetchone()[0]
    ytd = aggregate.ytd(conn)
    cash = aggregate.current_cash(conn)
    oc = aggregate.owner_comp(conn)

    print("=== Windansea Coconuts reconciliation ===")
    print(f"DB written:   {db_path}")
    print(f"Excel written: {xlsx_path}")
    print(f"Rows by bucket: {counts}")
    print(f"Rows needing review: {reviews}")
    print(f"Current cash: ${cash:,.2f}")
    print(
        f"YTD revenue ${ytd['revenue']:,.2f}, expenses ${ytd['expense']:,.2f}, "
        f"net ${ytd['net']:,.2f}"
    )
    print(f"ADP variance (meta): {store.get_meta(conn, 'adp_variance')}")
    print(f"Owner comp: {oc}")
    conn.close()


if __name__ == "__main__":
    main()
