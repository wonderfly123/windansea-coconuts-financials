"""Shared aggregation math for the Windansea Coconuts financial dashboard.

This is the ONE place where every total is computed. Both the Excel report
generator and the Flask dashboard import these functions so they always show
identical numbers. All bucket/flag strings come from src.constants; never
hardcode them here.

Sign conventions (from the transactions table):
  - amount is REAL and signed: positive = money in, negative = money out.
  - Revenue rows are positive; expense/payroll/owner rows are negative.
Reported expense-style totals are absolute (positive) numbers.

The single net definition used everywhere (dashboard square, chart, Excel):
    net = revenue - (expense + payroll + owner_pay + owner_draw)
This is true cash net. BUCKET_EXCLUDED rows are never counted in any total.
"""

from src import store
from src import constants as k


def _month_key(date: str) -> str:
    """First 7 chars of an ISO date, e.g. '2026-01-10' -> '2026-01'."""
    return date[:7]


def monthly(conn) -> dict:
    """Per-month totals keyed by month string.

    Returns a dict like:
        {"2026-01": {"revenue":float,"expense":float,"payroll":float,
                     "owner_pay":float,"owner_draw":float,"net":float}, ...}
    Includes every month that has at least one non-excluded transaction.
    """
    # Sum signed amounts grouped by month + bucket, skipping excluded rows.
    rows = conn.execute(
        "SELECT substr(date,1,7) AS m, bucket, SUM(amount) AS total "
        "FROM transactions WHERE bucket != ? GROUP BY m, bucket",
        [k.BUCKET_EXCLUDED],
    ).fetchall()

    months: dict = {}
    for month, bucket, total in rows:
        if month is None:
            continue
        bucket_totals = months.setdefault(month, {})
        bucket_totals[bucket] = total or 0.0

    result: dict = {}
    for month, bucket_totals in months.items():
        revenue = bucket_totals.get(k.BUCKET_REVENUE, 0.0)
        expense = abs(bucket_totals.get(k.BUCKET_OPERATING, 0.0))
        payroll = abs(bucket_totals.get(k.BUCKET_PAYROLL, 0.0))
        owner_pay = abs(bucket_totals.get(k.BUCKET_OWNER_PAY, 0.0))
        owner_draw = abs(bucket_totals.get(k.BUCKET_OWNER_DRAW, 0.0))
        net = revenue - (expense + payroll + owner_pay + owner_draw)
        result[month] = {
            "revenue": revenue,
            "expense": expense,
            "payroll": payroll,
            "owner_pay": owner_pay,
            "owner_draw": owner_draw,
            "net": net,
        }
    return result


def averages(conn, start, end) -> dict:
    """Average revenue, expense, and net over the months in [start, end].

    start/end are inclusive month keys like "2026-01", "2026-05". Only months
    that actually appear in monthly() and fall in the (string-comparable) range
    are averaged. The caller's default window is 2026-01..2026-05, excluding
    the partial June.
    """
    m = monthly(conn)
    keys = [month for month in m if start <= month <= end]
    n = len(keys)
    if n == 0:
        return {"revenue_avg": 0.0, "expense_avg": 0.0, "net_avg": 0.0}
    revenue_sum = sum(m[month]["revenue"] for month in keys)
    expense_sum = sum(m[month]["expense"] for month in keys)
    net_sum = sum(m[month]["net"] for month in keys)
    return {
        "revenue_avg": revenue_sum / n,
        "expense_avg": expense_sum / n,
        "net_avg": net_sum / n,
    }


def ytd(conn) -> dict:
    """Cumulative totals over ALL months (running total includes partial June)."""
    m = monthly(conn)
    totals = {
        "revenue": 0.0,
        "expense": 0.0,
        "net": 0.0,
        "payroll": 0.0,
        "owner_pay": 0.0,
        "owner_draw": 0.0,
    }
    for month_data in m.values():
        for key in totals:
            totals[key] += month_data[key]
    return totals


def current_cash(conn) -> float:
    """Sum of every balance row in the balances table."""
    row = conn.execute("SELECT SUM(balance) FROM balances").fetchone()
    return row[0] if row and row[0] is not None else 0.0


def runway(conn, current_cash, start, end) -> dict:
    """Cash runway based on averages(...).net_avg over [start, end].

    Burning (net_avg < 0): months of runway = current_cash / abs(net_avg).
    Profitable (net_avg >= 0): cash is growing, no finite runway.

    Label text uses plain words, commas, and periods only. NO dash characters.
    """
    net_avg = averages(conn, start, end)["net_avg"]
    if net_avg < 0:
        months = current_cash / abs(net_avg)
        return {
            "is_burning": True,
            "months": months,
            "monthly_change": net_avg,
            "label": f"{round(months, 1)} months of runway",
        }
    return {
        "is_burning": False,
        "months": None,
        "monthly_change": net_avg,
        "label": f"cash growing ${net_avg:,.0f} per month",
    }


def owner_comp(conn) -> dict:
    """Owner compensation breakdown for Jordan and Harrison.

    Jordan's figures come from flagged transaction rows. Harrison's W-2 gross
    comes from the meta key META_HARRISON_W2_GROSS (the Mercury ADP debits are
    aggregate with no per-employee detail), and his direct transfers come from
    flagged rows.
    """
    def _abs_sum_for_flag(flag: str) -> float:
        row = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE flag = ?", [flag]
        ).fetchone()
        return abs(row[0]) if row and row[0] is not None else 0.0

    capital_one = _abs_sum_for_flag(k.FLAG_OWNER_CAR)
    bofa_draw = _abs_sum_for_flag(k.FLAG_OWNER_DRAW_BOFA)

    raw_w2 = store.get_meta(conn, k.META_HARRISON_W2_GROSS)
    adp_w2 = float(raw_w2) if raw_w2 is not None else 0.0
    direct = _abs_sum_for_flag(k.FLAG_HARRISON_DIRECT)

    return {
        "jordan": {
            "capital_one": capital_one,
            "bofa_draw": bofa_draw,
            "total": capital_one + bofa_draw,
        },
        "harrison": {
            "adp_w2": adp_w2,
            "direct": direct,
            "total": adp_w2 + direct,
        },
    }
