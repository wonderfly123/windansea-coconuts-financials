"""Numbers for the Operating rules tab. Pure functions over the build context.

overhead_groups(recs) buckets overhead by the groups in plan.OVERHEAD_GROUPS.
rules_context(ctx) turns the build context into every figure the tab shows:
cost ratios, cents kept per dollar, fixed nut, break even, runway months, the
year estimate, margins with owners at plan pay, and the BLUF health figures.
"""

from collections import defaultdict

from src.runway import plan as P
from src.runway.aggregate import average, is_fixed_overhead, norm_label


def _group(r) -> str:
    sub = (r.sub or "").lower()
    for name, subs in P.OVERHEAD_GROUPS:
        if sub in subs:
            return name
    return P.OVERHEAD_FIXED_GROUP if is_fixed_overhead(r) else P.OVERHEAD_OTHER_GROUP


def overhead_groups(recs, n=6) -> list:
    """[{name, avg, fixed, items: [(label, avg)]}] for overhead in the window, in display order."""
    months = defaultdict(lambda: {m: 0.0 for m in P.MONTHS})
    items = defaultdict(lambda: defaultdict(float))
    for r in recs:
        if r.section != P.OVERHEAD or r.date[:7] not in P.MONTH_WEIGHTS:
            continue
        g = _group(r)
        months[g][r.date[:7]] += r.amount
        items[g][norm_label(r.label)] += r.amount
    w = sum(P.MONTH_WEIGHTS.values())
    order = [name for name, _ in P.OVERHEAD_GROUPS] + [P.OVERHEAD_OTHER_GROUP, P.OVERHEAD_FIXED_GROUP]
    out = []
    for g in order:
        if g not in months:
            continue
        top = sorted(items[g].items(), key=lambda kv: -kv[1])[:n]
        out.append({"name": g, "avg": average(months[g]), "fixed": g in P.FIXED_GROUPS,
                    "items": [(label, v / w) for label, v in top]})
    return out


def group_avg(groups, name) -> float:
    return next((g["avg"] for g in groups if g["name"] == name), 0.0)


def year_revenue(rev_months: dict, one_off_aug: float) -> float:
    """Actual Jan to Aug plus Sep to Dec tailed off August (minus the one off)."""
    actual = sum(v for m, v in rev_months.items() if m <= "2026-08")
    aug = rev_months.get("2026-08", 0.0) - one_off_aug
    return actual + sum(aug * f for f in P.PROJECTION_KNOBS["tail_factors"].values())


def rules_context(c: dict) -> dict:
    rev = c["avgs"][P.REVENUE]
    a = c["avgs"]
    oh = c["overhead_split"]
    groups = c["overhead_groups"]
    product, staff, tax = a[P.COGS], a[P.PEOPLE_NONCORE], a[P.SALES_TAX]
    var_oh = oh["variable_avg"]
    fixed_oh = oh["fixed_avg"]
    var_total = product + staff + tax + var_oh
    kept = 1 - var_total / rev

    core = c["core"]
    core_norm = sum(r["plan_total"] if r["key"] in P.OWNER_KEYS else r["actual"] for r in core["rows"])
    nut_today = core["actual_total"] + fixed_oh
    nut_plan = P.PLAN_TOTAL + fixed_oh
    fixed_norm = core_norm + fixed_oh
    cash = c["cash_after"]
    ar = c["ar"]
    ar_overdue = sum(r["amount"] for r in ar["rows"] if r["overdue"])
    ar_overdue_count = sum(1 for r in ar["rows"] if r["overdue"])

    ytd = sum(v for m, v in c["rev_months"].items() if m <= "2026-08")
    year = year_revenue(c["rev_months"], P.ONE_OFF_AUG)
    tax_pct = P.PROJECTION_KNOBS["tax_pct"]

    def op_margin(revenue, fixed, months):
        return (revenue * kept - fixed * months) / revenue if revenue else 0.0

    margins = {
        "summer_today": op_margin(rev, fixed_norm, 1), "summer_plan": op_margin(rev, nut_plan, 1),
        "year_today": op_margin(year, fixed_norm, 12), "year_plan": op_margin(year, nut_plan, 12),
    }
    margins.update({f"{k}_after_tax": v * (1 - tax_pct) for k, v in list(margins.items())})

    travel = group_avg(groups, "Travel")
    disc = group_avg(groups, "Discretionary")
    marketing = group_avg(groups, "Marketing and ads")
    tight_var = var_total - travel - max(0.0, disc - P.RULE_TARGETS["discretionary_cap"])
    tight_kept = 1 - tight_var / rev
    harrison = next(r for r in core["rows"] if r["key"] == "harrison")
    edy = next(r for r in core["rows"] if r["key"] == "edy")

    return {
        "rev": rev, "product": product, "staff": staff, "tax": tax, "var_oh": var_oh, "fixed_oh": fixed_oh,
        "cogs_all": product + staff, "var_total": var_total, "kept": kept,
        "product_pct": product / rev, "staff_pct": staff / rev, "tax_pct": tax / rev, "var_oh_pct": var_oh / rev,
        "cogs_all_pct": (product + staff) / rev, "var_pct": var_total / rev,
        "gross": 1 - (product + staff) / rev,
        "labor_today": (staff + core_norm) / rev, "labor_plan": (staff + P.PLAN_TOTAL) / rev,
        "core_pct": core["actual_total"] / rev, "marketing_pct": marketing / rev,
        "overhead_of_gp": a[P.OVERHEAD] / (rev - product - staff),
        "core_norm": core_norm, "nut_today": nut_today, "nut_plan": nut_plan,
        "breakeven_today": nut_today / kept, "breakeven_plan": nut_plan / kept,
        "months_today": cash / nut_today, "months_plan": cash / nut_plan,
        "months_ar_today": (cash + ar["total"]) / nut_today, "months_ar_plan": (cash + ar["total"]) / nut_plan,
        "cash": cash, "ar_total": ar["total"], "ar_count": ar["count"],
        "ar_overdue": ar_overdue, "ar_overdue_count": ar_overdue_count,
        "ytd": ytd, "year": year, "concentration": P.ONE_OFF_AUG / ytd if ytd else 0.0,
        "margins": margins, "income_tax_pct": tax_pct,
        "travel": travel, "discretionary": disc, "marketing": marketing,
        "tight_kept": tight_kept, "tight_var_pct": tight_var / rev, "tight_breakeven_plan": nut_plan / tight_kept,
        "harrison_actual": harrison["actual"], "harrison_plan": harrison["plan_total"],
        "edy_plan": edy["plan_total"], "edy_pct": edy["plan_total"] / rev,
    }
