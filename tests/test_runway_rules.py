import pytest

from src.runway import plan as P
from src.runway.classify import Rec
from src.runway.rules import overhead_groups, rules_context, year_revenue

W = sum(P.MONTH_WEIGHTS.values())


def rec(date, amt, section, sub="", label="x"):
    return Rec(date, amt, section, sub, label, True)


def test_overhead_groups_bucket_and_fix():
    recs = [rec("2026-05-01", 900, P.OVERHEAD, "Airlines", "United"),
            rec("2026-05-02", 100, P.OVERHEAD, "Restaurants", "Chipotle"),
            rec("2026-06-01", 400, P.OVERHEAD, "SaaS / Software", "Pipedrive"),
            rec("2026-06-02", 50, P.OVERHEAD, "Advertising", "Facebook Ads"),
            rec("2026-06-03", 20, P.OVERHEAD, "Shipping", "Fedex"),
            rec("2026-04-01", 999, P.OVERHEAD, "Airlines", "outside window"),
            rec("2026-05-01", 999, P.COGS, "", "not overhead")]
    g = {x["name"]: x for x in overhead_groups(recs)}
    assert g["Travel"]["avg"] == pytest.approx(900 / W) and not g["Travel"]["fixed"]
    assert g["Discretionary"]["avg"] == pytest.approx(100 / W)
    assert g["Marketing and ads"]["fixed"] and g[P.OVERHEAD_FIXED_GROUP]["fixed"]
    assert g[P.OVERHEAD_OTHER_GROUP]["avg"] == pytest.approx(20 / W)
    assert g["Travel"]["items"] == [("United", pytest.approx(900 / W))]
    assert [x["name"] for x in overhead_groups(recs)][0] == "Travel"


def test_year_revenue_tails_august_minus_one_off():
    rev = {"2026-07": 1000.0, "2026-08": 2000.0}
    tail = sum(P.PROJECTION_KNOBS["tail_factors"].values())
    assert year_revenue(rev, 500.0) == pytest.approx(3000 + 1500 * tail)


def _ctx():
    rows = [
        {"key": "harrison", "actual": 10000.0, "plan_total": 6500},
        {"key": "trent", "actual": 4000.0, "plan_total": 9125},
        {"key": "jordan", "actual": 3400.0, "plan_total": 2700},
        {"key": "edy", "actual": 0.0, "plan_total": 3250},
    ]
    return {
        "avgs": {P.REVENUE: 100000.0, P.COGS: 16000.0, P.PEOPLE_NONCORE: 14000.0, P.SALES_TAX: 5000.0, P.OVERHEAD: 16000.0},
        "overhead_split": {"fixed_avg": 1000.0, "variable_avg": 15000.0},
        "overhead_groups": [{"name": "Travel", "avg": 4000.0, "fixed": False, "items": []},
                            {"name": "Discretionary", "avg": 5500.0, "fixed": False, "items": []},
                            {"name": "Marketing and ads", "avg": 300.0, "fixed": True, "items": []}],
        "core": {"rows": rows, "actual_total": 17400.0, "plan_total": P.PLAN_TOTAL},
        "cash_after": 100000.0,
        "ar": {"total": 20000.0, "count": 4, "rows": [{"amount": 5000.0, "overdue": True}, {"amount": 15000.0, "overdue": False}]},
        "rev_months": {"2026-07": 50000.0, "2026-08": 100000.0},
    }


def test_rules_context_ratios_and_breakeven():
    r = rules_context(_ctx())
    assert r["var_pct"] == pytest.approx(0.50) and r["kept"] == pytest.approx(0.50)
    assert r["gross"] == pytest.approx(0.70) and r["cogs_all_pct"] == pytest.approx(0.30)
    assert r["nut_today"] == pytest.approx(18400.0) and r["nut_plan"] == pytest.approx(P.PLAN_TOTAL + 1000)
    assert r["breakeven_today"] == pytest.approx(36800.0)
    assert r["months_today"] == pytest.approx(100000 / 18400)
    assert r["months_ar_today"] == pytest.approx(120000 / 18400)
    assert r["ar_overdue"] == 5000.0 and r["ar_overdue_count"] == 1


def test_rules_context_owner_pay_at_plan():
    r = rules_context(_ctx())
    # harrison 6500 + jordan 2700 at plan, trent 4000 actual, edy 0
    assert r["core_norm"] == pytest.approx(13200.0)
    assert r["labor_today"] == pytest.approx((14000 + 13200) / 100000)
    assert r["margins"]["summer_today"] == pytest.approx((100000 * 0.5 - 14200) / 100000)
    assert r["margins"]["summer_today_after_tax"] == pytest.approx(r["margins"]["summer_today"] * (1 - P.PROJECTION_KNOBS["tax_pct"]))
    assert r["harrison_actual"] == 10000.0 and r["harrison_plan"] == 6500


def test_rules_context_tightened_variable():
    r = rules_context(_ctx())
    # drop travel 4000 and discretionary above the 2500 cap (3000)
    assert r["tight_var_pct"] == pytest.approx((50000 - 4000 - 3000) / 100000)
    assert r["tight_breakeven_plan"] == pytest.approx(r["nut_plan"] / r["tight_kept"])
