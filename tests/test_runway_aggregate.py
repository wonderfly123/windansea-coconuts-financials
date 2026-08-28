import pytest

from src.runway import plan as P
from src.runway.classify import Rec
from src.runway.aggregate import (flatten, monthly_by_section, average, top_labels, ar_summary,
                                  card_owed, core_table, projection_defaults, unknown_merchants)


def rec(date, amt, section, sub="", label="x", known=True):
    return Rec(date, amt, section, sub, label, known)


def test_flatten_handles_none_and_lists():
    a, b = rec("2026-05-01", 1, P.COGS), rec("2026-05-02", 2, P.COGS)
    assert flatten([None, a, [b]]) == [a, b]


def test_monthly_by_section_zero_filled_and_ignores_outside_window():
    recs = [rec("2026-05-03", 100, P.COGS), rec("2026-08-03", 50, P.COGS), rec("2026-04-30", 999, P.COGS)]
    m = monthly_by_section(recs)
    assert m[P.COGS] == {"2026-05": 100, "2026-06": 0, "2026-07": 0, "2026-08": 50}
    assert m[P.OVERHEAD]["2026-05"] == 0


def test_average_uses_prorated_august():
    assert average({"2026-05": 100, "2026-06": 100, "2026-07": 100, "2026-08": 100}) == pytest.approx(400 / (3 + 28 / 31))


def test_top_labels_merges_inc_variants():
    from src.runway.aggregate import norm_label
    assert norm_label("SUN HING FOODS, INC.") == norm_label("SUN HING FOODS, INC") == "Sun Hing Foods"


def test_top_labels_sorted():
    recs = [rec("2026-05-01", 5, P.COGS, label="a"), rec("2026-05-01", 9, P.COGS, label="b"), rec("2026-05-01", 1, P.OVERHEAD, label="c")]
    assert top_labels(recs, P.COGS) == [("b", 9), ("a", 5)]


def test_unknown_merchants_only_unknown():
    recs = [rec("2026-05-01", 5, P.OVERHEAD, label="Uber", known=False), rec("2026-05-01", 9, P.COGS, label="Sun Hing")]
    assert unknown_merchants(recs) == [("Uber", 5, 1)]


def inv(status, due, paid, due_date, customer="Acme"):
    return {"status": status, "title": "t", "primary_recipient": {"company_name": customer},
            "payment_requests": [{"due_date": due_date, "computed_amount_money": {"amount": due},
                                  "total_completed_amount_money": {"amount": paid}}]}


def test_ar_summary_open_amounts_and_overdue():
    s = ar_summary([inv("UNPAID", 100000, 0, "2026-09-01"), inv("PARTIALLY_PAID", 200000, 50000, "2026-08-01"),
                    inv("PAID", 5000, 5000, "2026-08-01"), inv("CANCELED", 5000, 0, "2026-08-01")], as_of="2026-08-28")
    assert s["total"] == 2500 and s["count"] == 2
    assert s["rows"][0]["overdue"] is True and s["rows"][1]["overdue"] is False


def test_card_owed_adds_spend_after_statement():
    st = {"statement_period_end": "2026-08-08", "curr_balance": 0}
    recs = [rec("2026-08-05", 100, P.OVERHEAD), rec("2026-08-10", 40, P.OVERHEAD), rec("2026-08-20", 60, P.COGS)]
    assert card_owed(st, recs) == 100


def test_core_table_totals():
    recs = [rec("2026-05-01", 1000, P.PEOPLE_CORE, "trent"), rec("2026-06-01", 1000, P.PEOPLE_CORE, "trent")]
    t = core_table(recs)
    trent = next(r for r in t["rows"] if r["key"] == "trent")
    assert trent["actual"] == pytest.approx(2000 / (3 + 28 / 31))
    assert t["plan_total"] == 28800 and t["diff_total"] == pytest.approx(28800 - trent["actual"])
    assert next(r for r in t["rows"] if r["key"] == "ops_mgr")["actual"] == 0


def test_projection_defaults():
    avgs = {P.REVENUE: 100000, P.COGS: 20000, P.PEOPLE_NONCORE: 10000, P.OVERHEAD: 15000, P.PEOPLE_CORE: 12000, P.SALES_TAX: 5000}
    rev = {f"2026-{i:02d}": 10000 * i for i in range(1, 9)}
    d = projection_defaults(avgs, rev, one_off_aug=30000)
    assert d["cogs_pct"] == 0.2 and d["noncore_pct"] == 0.1 and d["sales_tax_pct"] == 0.05 and d["overhead_fixed"] == 15000
    d2 = projection_defaults(avgs, rev, 0, {"fixed_avg": 2000, "variable_avg": 13000})
    assert d2["overhead_fixed"] == 2000 and d2["overhead_pct"] == 0.13
    assert d["baseline"]["2026-09"] == pytest.approx(50000 * 0.7)
    assert d["baseline"]["2027-03"] == 30000 and d["baseline"]["2027-08"] == 50000
    assert len(d["baseline"]) == 12


def test_overhead_split_by_category():
    from src.runway.aggregate import overhead_split
    recs = [rec("2026-05-01", 400, P.OVERHEAD, "SaaS / Software", "Pipedrive"), rec("2026-05-01", 900, P.OVERHEAD, "Airlines", "United"),
            rec("2026-06-01", 100, P.OVERHEAD, "bill pay", "Extra Space Storage")]
    o = overhead_split(recs)
    assert o["fixed_avg"] == pytest.approx(500 / (3 + 28 / 31)) and o["variable_avg"] == pytest.approx(900 / (3 + 28 / 31))
