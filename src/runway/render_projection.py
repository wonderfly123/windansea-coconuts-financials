"""HTML for the runway and projection section. The math runs in projection.js."""

import json
from html import escape as e

from src.runway import plan as P
from src.runway.projection import MONTHS
from src.runway.render_page import money

NAMES = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
         "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}


def _mlabel(m):
    return f"{NAMES[m[5:7]]} {m[2:4]}"


def _knob(id_, label, value, step="1", kind="number"):
    return f'<label>{e(label)}<input id="{id_}" type="{kind}" value="{e(str(value))}" step="{step}"></label>'


def projection_section(defaults: dict, start_cash: float, core_actual: float) -> str:
    k = P.PROJECTION_KNOBS
    d = defaults
    baseline_inputs = "".join(
        f'<label>{_mlabel(m)}<input id="base-{m}" type="number" step="500" value="{round(d["baseline"].get(m, 0))}"></label>' for m in MONTHS)
    data = {"start_cash": round(start_cash, 2), "core_actual": round(core_actual, 2), "presets": P.PRESETS}
    return (
        '<h2 id="projection-h">Runway, the next twelve months</h2>'
        '<div class="tile" id="projection">'
        '<div class="presets"><span class="small">Scenario:</span>'
        '<button type="button" data-preset="status_quo">Status quo: repeat 2026</button>'
        '<button type="button" data-preset="plan">Plan: Harrison sells, ads on</button>'
        '<button type="button" data-preset="aggressive">Aggressive: more accounts, more ads</button></div>'
        '<p class="small">Click a scenario. The numbers, the chart and the assumptions below all change with it.</p>'
        '<div class="scenario" id="scenario"></div>'
        '<div class="callout" id="proj-callout"></div>'
        '<div id="proj-chart"></div>'
        '<ul class="assume" id="assume"></ul>'
        '<details><summary>Change assumptions and see the month by month table</summary>'
        '<div class="knobs">'
        + _knob("hire_month", "Full core plan starts (YYYY-MM)", k["hire_month"], kind="text")
        + _knob("core_plan", "Core team cost per month at plan", P.PLAN_TOTAL, "100")
        + _knob("season_months", "Wholesale season months (1 to 12)", ",".join(str(m) for m in k["season_months"]), kind="text")
        + _knob("new_accounts_per_month", "New wholesale accounts per month, in season", k["new_accounts_per_month"], "1")
        + _knob("value_per_account", "Revenue per account per month, in season", k["value_per_account"], "100")
        + _knob("events_multiplier", "Events multiplier from ads and organic", k["events_multiplier"], "0.05")
        + _knob("cogs_pct", "Product cost, % of revenue", round(d["cogs_pct"] * 100, 1), "0.5")
        + _knob("noncore_pct", "Event staff and contractors, % of revenue", round(d["noncore_pct"] * 100, 1), "0.5")
        + _knob("sales_tax_pct", "Sales tax remitted, % of revenue", round(d["sales_tax_pct"] * 100, 1), "0.5")
        + _knob("overhead_pct", "Event overhead, % of revenue", round(d["overhead_pct"] * 100, 1), "0.5")
        + _knob("overhead_fixed", "Fixed overhead per month", round(d["overhead_fixed"]), "100")
        + '<label>One off deals, one per line as YYYY-MM: amount<textarea id="one_offs" placeholder="2026-11: 25000"></textarea></label>'
        + '</div>'
        '<h3>Baseline revenue by month before growth</h3>'
        f'<div class="baseline">{baseline_inputs}</div>'
        '<div class="tscroll"><table><thead><tr><th>Month</th><th class="num">Wholesale</th><th class="num">Events and one offs</th><th class="num">Revenue</th><th class="num">Burn</th><th class="num">Cash at month end</th></tr></thead>'
        '<tbody id="proj-body"></tbody></table></div>'
        '<p class="small">Burn = revenue times (product % + staff % + event overhead % + sales tax %) plus fixed overhead plus core team.</p>'
        '</details></div>'
        f'<script>window.RUNWAY={json.dumps(data)};</script>'
    )
