"""Sums, averages and tables for the runway dashboard. Pure functions."""

from collections import defaultdict

from src.runway import plan as P


def flatten(tagged) -> list:
    """Taggers return Rec, list[Rec] or None; make a flat list of Recs."""
    out = []
    for t in tagged:
        if t is None:
            continue
        out.extend(t if isinstance(t, list) else [t])
    return out


def monthly_by_section(recs) -> dict:
    """{section: {month: total}} over the window months, zero filled."""
    out = {s: {m: 0.0 for m in P.MONTHS} for s in P.SECTIONS}
    for r in recs:
        m = r.date[:7]
        if m in out[r.section]:
            out[r.section][m] += r.amount
    return out


def monthly_by_sub(recs, section) -> dict:
    """{sub: {month: total}} for one section."""
    out = defaultdict(lambda: {m: 0.0 for m in P.MONTHS})
    for r in recs:
        if r.section == section and r.date[:7] in P.MONTH_WEIGHTS:
            out[r.sub][r.date[:7]] += r.amount
    return dict(out)


def average(month_totals: dict) -> float:
    """Monthly average with August prorated: sum / (3 + 28/31)."""
    weight = sum(P.MONTH_WEIGHTS.values())
    return sum(month_totals.get(m, 0.0) for m in P.MONTHS) / weight


def norm_label(label: str) -> str:
    """Merge 'SUN HING FOODS, INC.' / 'SUN HING FOODS, INC' / 'Sun Hing Foods'."""
    s = (label or "").strip().rstrip(".")
    for suffix in (", inc", " inc", ", llc", " llc"):
        if s.lower().endswith(suffix):
            s = s[: -len(suffix)].rstrip(",. ")
    return s.title() if s.isupper() else s


def top_labels(recs, section, n=8) -> list:
    """[(label, total)] largest first for the section within the window."""
    tot = defaultdict(float)
    for r in recs:
        if r.section == section and r.date[:7] in P.MONTH_WEIGHTS:
            tot[norm_label(r.label)] += r.amount
    return sorted(tot.items(), key=lambda kv: -kv[1])[:n]


def unknown_merchants(recs, n=25) -> list:
    """Overhead rows that matched no rule, grouped, largest first."""
    tot = defaultdict(lambda: [0.0, 0])
    for r in recs:
        if not r.known and r.date[:7] in P.MONTH_WEIGHTS:
            tot[r.label][0] += r.amount
            tot[r.label][1] += 1
    rows = [(k, v[0], v[1]) for k, v in tot.items()]
    return sorted(rows, key=lambda x: -x[1])[:n]


OPEN_STATUSES = {"UNPAID", "PARTIALLY_PAID", "SCHEDULED"}


def ar_summary(invoices, as_of: str) -> dict:
    """Open Square invoices: total, count and rows sorted by due date."""
    rows = []
    for inv in invoices:
        if inv.get("status") not in OPEN_STATUSES:
            continue
        prs = inv.get("payment_requests") or []
        due = sum(int(p.get("computed_amount_money", {}).get("amount", 0)) for p in prs)
        paid = sum(int(p.get("total_completed_amount_money", {}).get("amount", 0)) for p in prs)
        open_amt = (due - paid) / 100
        if open_amt <= 0:
            continue
        due_date = prs[0].get("due_date", "") if prs else ""
        rec = inv.get("primary_recipient") or {}
        customer = rec.get("company_name") or " ".join(
            x for x in [rec.get("given_name"), rec.get("family_name")] if x) or "Unknown"
        rows.append({"customer": customer, "title": inv.get("title") or inv.get("invoice_number") or "",
                     "amount": open_amt, "due": due_date, "overdue": bool(due_date) and due_date < as_of})
    rows.sort(key=lambda r: r["due"])
    return {"total": sum(r["amount"] for r in rows), "count": len(rows), "rows": rows}


def card_owed(statement: dict, card_recs) -> float:
    """Unpaid card balance: statement remainder + card spend after the statement period."""
    end = statement.get("statement_period_end", "")
    since = sum(r.amount for r in card_recs if r.date > end)
    return float(statement.get("curr_balance", 0)) + since


def core_table(recs) -> dict:
    """Per core person: actual monthly average, plan, difference; plus totals."""
    by = monthly_by_sub(recs, P.PEOPLE_CORE)
    rows = []
    for p in P.CORE_PEOPLE:
        months = by.get(p["key"], {m: 0.0 for m in P.MONTHS})
        actual = average(months)
        rows.append({**p, "months": months, "actual": actual, "diff": p["plan_total"] - actual})
    return {"rows": rows, "actual_total": sum(r["actual"] for r in rows),
            "plan_total": P.PLAN_TOTAL, "diff_total": P.PLAN_TOTAL - sum(r["actual"] for r in rows)}


def is_fixed_overhead(r) -> bool:
    return (r.sub or "").lower() in P.FIXED_OVERHEAD_SUBS or any(k in (r.label or "").lower() for k in P.FIXED_OVERHEAD_LABELS)


def overhead_split(recs) -> dict:
    """Monthly average of overhead that does not move with events vs the rest."""
    fixed = {m: 0.0 for m in P.MONTHS}
    var = {m: 0.0 for m in P.MONTHS}
    for r in recs:
        if r.section != P.OVERHEAD or r.date[:7] not in fixed:
            continue
        (fixed if is_fixed_overhead(r) else var)[r.date[:7]] += r.amount
    return {"fixed_avg": average(fixed), "variable_avg": average(var)}


def projection_defaults(section_avgs: dict, rev_2026: dict, one_off_aug: float, overhead=None) -> dict:
    """Derived knobs: cost ratios and the 12 month baseline revenue curve.

    rev_2026: {"2026-01": x, ... "2026-08": y} actual revenue, August full
    month (already prorated up). one_off_aug is subtracted from August before
    it is used as the tail anchor and as the Aug 2027 baseline.
    """
    rev_avg = section_avgs[P.REVENUE]
    oh = overhead or {"fixed_avg": section_avgs[P.OVERHEAD], "variable_avg": 0.0}
    aug = rev_2026.get("2026-08", 0.0) - one_off_aug
    baseline = {}
    for m, f in P.PROJECTION_KNOBS["tail_factors"].items():
        baseline[m] = aug * f
    for i in range(1, 9):
        baseline[f"2027-{i:02d}"] = (aug if i == 8 else rev_2026.get(f"2026-{i:02d}", 0.0))
    return {
        "cogs_pct": section_avgs[P.COGS] / rev_avg if rev_avg else 0.0,
        "noncore_pct": section_avgs[P.PEOPLE_NONCORE] / rev_avg if rev_avg else 0.0,
        "sales_tax_pct": section_avgs[P.SALES_TAX] / rev_avg if rev_avg else 0.0,
        "overhead_fixed": oh["fixed_avg"],
        "overhead_pct": oh["variable_avg"] / rev_avg if rev_avg else 0.0,
        "core_actual": section_avgs[P.PEOPLE_CORE],
        "core_plan": P.PLAN_TOTAL,
        "baseline": baseline,
    }
