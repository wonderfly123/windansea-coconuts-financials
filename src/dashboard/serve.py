"""Flask dashboard for the Windansea Coconuts financial State of the Union.

Reads live from the reconciled SQLite DB and serves a CFO State of the Union.
Every total comes from src.aggregate; this module never reinvents the math.

A fresh sqlite connection is opened per request because sqlite connections are
not safe to share across threads.
"""

import sqlite3

from flask import Flask, jsonify, render_template, request

from src import aggregate
from src import store
from src import constants as k

# Default average window starts in March, when real revenue began. The end is
# the last complete month, derived from the data so it auto-advances each refresh
# (the partial month is the month of the pull date and is excluded from averages).
DEFAULT_START = "2026-04"
PARTIAL_MONTH = "2026-06"

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _month_label(key):
    """Turn '2026-01' into 'January 2026' so no dash appears in prose."""
    try:
        year, month = key.split("-")
        return "%s %s" % (_MONTH_NAMES[int(month) - 1], year)
    except (ValueError, IndexError):
        return key


def _connect(db_path):
    """Open a new sqlite connection for the current request."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _fmt_money(value):
    """Whole dollars with thousands commas, no dash for negatives (uses parentheses)."""
    rounded = round(value)
    if rounded < 0:
        return "($%s)" % format(abs(rounded), ",")
    return "$%s" % format(rounded, ",")


def _categories(conn):
    """Operating expense by category, absolute amounts, descending."""
    rows = conn.execute(
        "SELECT category, SUM(ABS(amount)) AS amount FROM transactions "
        "WHERE bucket = ? GROUP BY category ORDER BY amount DESC",
        [k.BUCKET_OPERATING],
    ).fetchall()
    return [
        {"category": r["category"] or "Uncategorized", "amount": r["amount"] or 0.0}
        for r in rows
    ]


def _partial_month(conn):
    """The current, incomplete month, derived from the pull/refresh date."""
    raw = (store.get_meta(conn, k.META_WINDOW_END)
           or store.get_meta(conn, k.META_LAST_REFRESH))
    return (raw or PARTIAL_MONTH)[:7]


def _default_window(conn):
    """(start, end) default average window: March through the latest month.

    The end is the most recent month present (including the partial current month,
    per the owner's choice to include June). Derived from the data so it
    auto-advances on each refresh.
    """
    months = sorted(aggregate.monthly(conn).keys())
    if not months:
        return DEFAULT_START, DEFAULT_START
    end = months[-1]
    start = DEFAULT_START if (DEFAULT_START in months and DEFAULT_START <= end) else months[0]
    return start, end


def _harrison_direct_by_month(conn):
    """Harrison's owner distributions per month. He operates the business, so the
    owner counts his pay as a running cost (folded into expenses), unlike Jordan's
    owner pay/draws which stay in the Owner Comp panel only."""
    rows = conn.execute(
        "SELECT substr(date,1,7), COALESCE(SUM(ABS(amount)),0) FROM transactions "
        "WHERE flag = ? GROUP BY substr(date,1,7)", [k.FLAG_HARRISON_DIRECT]).fetchall()
    return {m: v for m, v in rows}


def _build_monthly(conn):
    """Months with revenue and full operating cost for the chart and Expenses avg.

    Expenses = operating + payroll + Harrison's distributions. Harrison's W-2 is
    already inside payroll; his direct distributions are added because he runs the
    business. Jordan's owner pay/draws are NOT included (they live in Owner Comp).
    """
    m = aggregate.monthly(conn)
    partial = _partial_month(conn)
    hd = _harrison_direct_by_month(conn)
    out = []
    for month in sorted(m):
        expense = m[month]["expense"] + m[month]["payroll"] + hd.get(month, 0.0)
        out.append({
            "month": month,
            "revenue": m[month]["revenue"],
            "expense": expense,
            "is_partial": month == partial,
        })
    return out


def _build_takeaways(start, end, revenue_avg, expense_avg, owner):
    """Plain english sentences built from real numbers. No dash characters."""
    owner_total = owner["jordan"]["total"] + owner["harrison"]["total"]
    return [
        "Revenue averaged %s per month from %s through %s." % (
            _fmt_money(revenue_avg), _month_label(start), _month_label(end)),
        "Expenses averaged %s over that window, including payroll and Harrison's pay."
        % _fmt_money(expense_avg),
        "Owners took %s year to date, Jordan %s and Harrison %s, including W2 pay, "
        "distributions, and draws." % (
            _fmt_money(owner_total),
            _fmt_money(owner["jordan"]["total"]),
            _fmt_money(owner["harrison"]["total"])),
    ]


def create_app(db_path):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/summary")
    def summary():
        conn = _connect(db_path)
        try:
            d_start, d_end = _default_window(conn)
            start = request.args.get("start") or d_start
            end = request.args.get("end") or d_end
            ytd = aggregate.ytd(conn)
            cash = aggregate.current_cash(conn)
            owner = aggregate.owner_comp(conn)
            monthly = _build_monthly(conn)
            in_window = [x for x in monthly if start <= x["month"] <= end]
            n = len(in_window) or 1
            revenue_avg = sum(x["revenue"] for x in in_window) / n
            expense_avg = sum(x["expense"] for x in in_window) / n
            payload = {
                "start": start,
                "end": end,
                "current_cash": cash,
                "cash_on_the_way": "TBD",
                "revenue_avg": revenue_avg,
                "expense_avg": expense_avg,
                "net_avg": revenue_avg - expense_avg,
                "margin": ((revenue_avg - expense_avg) / revenue_avg) if revenue_avg else 0,
                "ytd": ytd,
                "monthly": monthly,
                "owner_comp": owner,
                "categories": _categories(conn),
                "takeaways": _build_takeaways(
                    start, end, revenue_avg, expense_avg, owner),
            }
            return jsonify(payload)
        finally:
            conn.close()

    @app.route("/api/transactions")
    def transactions():
        q = request.args.get("q", "").strip()
        bucket = request.args.get("bucket", "").strip()
        sql = (
            "SELECT date, source, counterparty, category, amount, bucket, flag, review "
            "FROM transactions WHERE 1=1"
        )
        params = []
        if q:
            sql += " AND (counterparty LIKE ? OR description LIKE ? OR category LIKE ?)"
            like = "%%%s%%" % q
            params.extend([like, like, like])
        if bucket:
            sql += " AND bucket = ?"
            params.append(bucket)
        sql += " ORDER BY date"
        conn = _connect(db_path)
        try:
            rows = conn.execute(sql, params).fetchall()
            return jsonify([dict(r) for r in rows])
        finally:
            conn.close()

    @app.route("/api/questions", methods=["GET"])
    def get_questions():
        conn = _connect(db_path)
        try:
            rows = store.list_questions(conn)
            return jsonify([
                {"id": r[0], "text": r[1], "created_at": r[2]} for r in rows])
        finally:
            conn.close()

    @app.route("/api/questions", methods=["POST"])
    def post_question():
        text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
        if not text:
            return jsonify({"error": "empty"}), 400
        conn = _connect(db_path)
        try:
            store.add_question(conn, text)
            return jsonify({"ok": True})
        finally:
            conn.close()

    @app.route("/api/questions/<int:qid>", methods=["DELETE"])
    def remove_question(qid):
        conn = _connect(db_path)
        try:
            store.delete_question(conn, qid)
            return jsonify({"ok": True})
        finally:
            conn.close()

    return app


if __name__ == "__main__":
    create_app("data/coconuts.db").run(port=8000, debug=False)
