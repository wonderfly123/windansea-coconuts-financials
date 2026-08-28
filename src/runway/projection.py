"""Python reference for the in page projection (mirrors projection.js).

Knobs (all required):
  start_cash, hire_month ("YYYY-MM"), season_months [ints], new_accounts_per_month,
  value_per_account, events_multiplier, baseline {month: revenue}, one_offs
  [{"month": "YYYY-MM", "amount": x}], cogs_pct, noncore_pct, sales_tax_pct, overhead_pct, overhead_fixed,
  core_actual, core_plan, tax_pct, owner_draws.
  cash is after an income tax reserve of tax_pct times cumulative profit
  (profit adds back owner draws, which are not deductible).
"""

MONTHS = ["2026-09", "2026-10", "2026-11", "2026-12", "2027-01", "2027-02",
          "2027-03", "2027-04", "2027-05", "2027-06", "2027-07", "2027-08"]


def project(k: dict) -> list:
    cash = float(k["start_cash"])
    accounts = 0
    cum_profit = 0.0
    reserve = 0.0
    out = []
    for m in MONTHS:
        mnum = int(m[5:7])
        in_season = mnum in k["season_months"]
        accounts = accounts + k["new_accounts_per_month"] if in_season else 0
        wholesale = accounts * k["value_per_account"] if in_season else 0.0
        events = k["baseline"].get(m, 0.0) * k["events_multiplier"]
        one_off = sum(o["amount"] for o in k.get("one_offs", []) if o["month"] == m)
        revenue = wholesale + events + one_off
        core = k["core_plan"] if m >= k["hire_month"] else k["core_actual"]
        burn = (revenue * (k["cogs_pct"] + k["noncore_pct"] + k.get("sales_tax_pct", 0.0) + k.get("overhead_pct", 0.0))
                + k["overhead_fixed"] + core)
        cum_profit += revenue - burn + k.get("owner_draws", 0.0)
        new_reserve = max(0.0, cum_profit) * k.get("tax_pct", 0.0)
        tax = new_reserve - reserve
        reserve = new_reserve
        cash = cash + revenue - burn - tax
        out.append({"month": m, "wholesale": wholesale, "events": events, "one_off": one_off,
                    "revenue": revenue, "burn": burn, "tax": tax, "reserve": reserve, "cash": cash})
    return out


def summary(rows: list) -> dict:
    low = min(rows, key=lambda r: r["cash"])
    first_neg = next((r["month"] for r in rows if r["cash"] < 0), None)
    return {"lowest_cash": low["cash"], "lowest_month": low["month"], "runs_out": first_neg}
