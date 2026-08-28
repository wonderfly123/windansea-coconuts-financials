from pathlib import Path

import pytest

from src.runway.projection import project, summary, MONTHS


def knobs(**over):
    k = {"start_cash": 100000, "hire_month": "2027-01", "season_months": [5, 6, 7, 8, 9],
         "new_accounts_per_month": 0, "value_per_account": 1000, "events_multiplier": 1.0,
         "baseline": {m: 0.0 for m in MONTHS}, "one_offs": [], "cogs_pct": 0.2, "noncore_pct": 0.1, "sales_tax_pct": 0.05, "overhead_pct": 0.0,
         "overhead_fixed": 10000, "core_actual": 5000, "core_plan": 28400}
    k.update(over)
    return k


def test_zero_revenue_falls_by_fixed_burn():
    rows = project(knobs())
    assert rows[0]["cash"] == 100000 - 15000
    assert rows[3]["cash"] == 100000 - 4 * 15000  # Dec, still pre hire
    assert rows[4]["burn"] == 10000 + 28400  # Jan hire month


def test_wholesale_only_in_season_and_resets():
    rows = project(knobs(new_accounts_per_month=2, value_per_account=1000))
    by = {r["month"]: r["wholesale"] for r in rows}
    assert by["2026-09"] == 2000  # season starts counting from Sep with 2 accounts
    assert by["2026-10"] == 0 and by["2027-04"] == 0
    assert by["2027-05"] == 2000 and by["2027-06"] == 4000 and by["2027-09" if False else "2027-08"] == 8000


def test_events_multiplier_and_one_off():
    rows = project(knobs(baseline={**{m: 0.0 for m in MONTHS}, "2026-10": 10000}, events_multiplier=1.5,
                         one_offs=[{"month": "2026-10", "amount": 5000}]))
    oct_ = rows[1]
    assert oct_["revenue"] == 20000 and oct_["burn"] == pytest.approx(20000 * 0.35 + 10000 + 5000)


def test_summary_lowest_and_runs_out():
    rows = project(knobs(start_cash=50000))
    s = summary(rows)
    assert s["runs_out"] == "2026-12" and s["lowest_month"] == "2027-08"


def test_js_has_every_knob_key():
    js = Path("src/runway/projection.js").read_text()
    for key in knobs():
        assert key in js, key
