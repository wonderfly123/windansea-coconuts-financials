"""HTML for the Operating rules tab. Follows docs/operating_rules.md section by section."""

from html import escape as e

from src.runway import plan as P
from src.runway.render_page import money


def pct(v, digits=0) -> str:
    return f"{v * 100:.{digits}f}%"


def _table(head, rows, cls="") -> str:
    th = "".join(f'<th class="{"num" if i else ""}">{e(h)}</th>' for i, h in enumerate(head))
    body = "".join(rows)
    return f'<div class="tile {cls}"><div class="tscroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div></div>'


def _tr(cells, cls="") -> str:
    tds = "".join(f'<td class="{"num" if i else ""}">{c}</td>' for i, c in enumerate(cells))
    return f'<tr class="{cls}">{tds}</tr>'


def _bench_analysis(r) -> str:
    m = r["margins"]
    return (
        '<ul class="assume">'
        f'<li><strong>Gross margin {pct(r["gross"])}.</strong> Above the agency range, double the wholesale range. A branded coconut at an event is priced like an activation, not like produce.</li>'
        f'<li><strong>Labor {pct(r["labor_today"])}.</strong> Agencies run 50 to 70%. The business delivers with people but is not people heavy.</li>'
        f'<li><strong>Operating margin {pct(m["summer_today"])} in summer, {pct(m["year_today"])} for the year.</strong> The summer month beats every peer. Spread over a full year with a quiet winter it is ordinary for an agency and good for a wholesaler.</li>'
        f'<li><strong>Marketing {pct(r["marketing_pct"], 1)}.</strong> Agencies spend 8 to 14%. The clearest gap.</li>'
        '<li>The summer margin says the product is right. The year margin says the business is not yet buying enough winter revenue to use it.</li>'
        '</ul>'
    )

def _bluf(r) -> str:
    m = r["margins"]
    win = {
        "gross": pct(r["gross"]),
        "labor": f'{pct(r["labor_today"])} today, {pct(r["labor_plan"])} with the full plan team',
        "operating": (f'{pct(m["summer_today"])} summer, {pct(m["year_today"])} for the year. With the full plan team: '
                      f'{pct(m["summer_plan"])} summer, {pct(abs(m["year_plan"]))} {"loss" if m["year_plan"] < 0 else "profit"} for the year'),
        "after_tax": f'{pct(m["summer_today_after_tax"])} summer, {pct(m["year_today_after_tax"])} for the year',
        "marketing": pct(r["marketing_pct"], 1),
    }
    rows = [_tr([f'<strong>{e(b["metric"])}.</strong> <span class="small">{e(b["what"])}</span>', win[b["key"]], e(b["agency"]), e(b["wholesale"])])
            for b in P.BENCHMARKS]
    year_math = _table(["", "Amount"], [
        _tr(["2026 revenue estimate", money(r["year"])]),
        _tr([f'Kept after variable costs at {r["kept"] * 100:.0f} cents per dollar', money(r["year"] * r["kept"])]),
        _tr([f'Fixed monthly costs for 12 months, owners at plan pay ({money(r["core_norm"] + r["fixed_oh"])} a month)', money((r["core_norm"] + r["fixed_oh"]) * 12)]),
        _tr(["Operating profit for the year", f'{money(r["year"] * r["kept"] - (r["core_norm"] + r["fixed_oh"]) * 12)}, {pct(m["year_today"])} of revenue'], "total"),
    ])
    bullets = [
        ('What this is', 'Spending rules for a business whose revenue swings ten to one between winter and summer. Each cost that moves with sales gets a target share of revenue. '
                         'Each cost that does not gets a dollar cap. Built from May to Aug 2026 actuals.'),
        ('May to Aug 2026 average', f'Revenue {money(r["rev"])} a month. Costs {money(r["var_total"] + r["nut_today"])} a month, everything included.'),
        ('Cash', f'{money(r["cash"])} after the card balance.'),
        ('Months of operating if nothing else comes in', f'{r["months_today"]:.1f} months today, {r["months_plan"]:.1f} with the full plan team. '
                                                        f'{r["months_ar_today"]:.1f} and {r["months_ar_plan"]:.1f} if the {money(r["ar_total"])} customers owe is collected. '
                                                        'This assumes no more events are executed. Booked events and revenue for Oct, Nov and Dec still need to be added.'),
        ('Break even', f'{money(r["breakeven_today"])} of revenue a month today, {money(r["breakeven_plan"])} with the full plan team.'),
        ('Each revenue dollar', f'{pct(r["cogs_all_pct"])} goes to coconuts, supplies and event staff, {pct(r["var_pct"] - r["cogs_all_pct"])} to sales tax and event overhead, '
                                f'and {r["kept"] * 100:.0f} cents is left for fixed costs and profit.'),
        ('Fixed monthly costs', f'{money(r["nut_today"])} today, {money(r["nut_plan"])} with the full plan team. The core team is {pct(r["core_pct"])} of a summer month.'),
        ('Against peers', f'Gross margin {pct(r["gross"])} beats activation agencies (50 to 60%) and specialty wholesalers (20 to 35%). '
                          f'Operating margin {pct(m["summer_today"])} in a summer month, {pct(m["year_today"])} for the year. '
                          f'Marketing at {pct(r["marketing_pct"], 1)} is far below the 8 to 14% agencies spend.'),
        ('Golden rule', f'If the month has less than {money(r["breakeven_today"])} of events booked, about {r["golden_events"]} events at the typical '
                        f'{money(r["invoice_avg"])}, the core team works the events themselves and no hourly staff is called. Above that, hourly staff '
                        f'is hired inside the {pct(P.RULE_TARGETS["staff_pct"])} cap and the core team runs operations. '
                        'The number is a guide, not a switch. In a thin month use common sense about who works what. The one constant: Harrison stays as free as possible to sell.'),
    ]
    li = "".join(f'<li><strong>{e(h)}.</strong> {t}</li>' for h, t in bullets)
    return (
        '<h2>BLUF</h2>'
        f'<div class="tile good"><ul class="assume bluf">{li}</ul></div>'
        '<details><summary>How we compare to peers</summary>'
        f'<p class="small">Each row is a share of revenue. Windansea is the May to Aug 2026 average, {money(r["rev"])} a month. '
        'Peer figures are cited in the appendix at the bottom.</p>'
        + _table(["What is measured", "Windansea", "Brand activation agencies", "Specialty food wholesale"], rows, "bench")
        + _bench_analysis(r)
        + '<details><summary>Where the year number comes from</summary>' + year_math + '</details>'
        '<details><summary>Assumptions</summary><ul class="assume">' + "".join(f"<li>{e(x)}</li>" for x in P.ASSUMPTIONS) + '</ul></details>'
        '</details>'
    )

def _scale(c, r) -> str:
    rows = [
        _tr(["<strong>COGS, all in</strong>", f'<strong>{money(r["cogs_all"])}</strong>', f'<strong>{pct(r["cogs_all_pct"], 1)}</strong>']),
        _tr(["Product (coconuts, supplies, packaging)", money(r["product"]), pct(r["product_pct"], 1)]),
        _tr(["Event staff", money(r["staff"]), pct(r["staff_pct"], 1)]),
        _tr(["Sales tax paid to the state", money(r["tax"]), pct(r["tax_pct"], 1)]),
        _tr(["Variable overhead (travel, meals, reimbursements)", money(r["var_oh"]), pct(r["var_oh_pct"], 1)]),
        _tr(["Total variable", money(r["var_total"]), pct(r["var_pct"])], "total"),
    ]
    w = sum(P.MONTH_WEIGHTS.values())
    month_heads = [P.MONTH_LABELS[m].split(" ")[0] for m in P.MONTHS]
    vendors = [_tr([e(n), money(sum(mo.values()) / w)] + [money(mo[m]) for m in P.MONTHS]) for n, mo in c["cogs_vendors"]]
    names = {P.SUB_ADP_HOURLY: "ADP hourly (W-2 event staff)", P.SUB_VENMO: "Venmo, Apple Cash, Tremendous",
             P.SUB_CONTRACTOR: "Contractors (Indico Thread, Nathan Zini, Josh Escalante)"}
    staff_rows = []
    for k in (P.SUB_ADP_HOURLY, P.SUB_VENMO, P.SUB_CONTRACTOR):
        mo = c["noncore_subs"].get(k, {m: 0.0 for m in P.MONTHS})
        avg = sum(mo.values()) / w
        staff_rows.append(_tr([names[k], money(avg), pct(avg / r["rev"], 1)] + [money(mo[m]) for m in P.MONTHS]))
    t = P.RULE_TARGETS
    return (
        '<h2>Costs that scale with revenue</h2>'
        + _table(["Line", "Avg per month", "% of revenue"], rows)
        + f'<p class="lead">After these costs, every revenue dollar has about {r["kept"] * 100:.0f} cents left to cover fixed costs.</p>'
        + '<h3 class="sect">Are these healthy?</h3><ul class="assume">'
        f'<li><strong>Product and event staff, {pct(r["cogs_all_pct"])} together.</strong> Very healthy. Caterers run 28 to 36% on food alone and 55 to 62% on food plus labor [6][7]. Windansea spends about half.</li>'
        f'<li><strong>Sales tax, {pct(r["tax_pct"], 1)}.</strong> Collected from customers and passed on. Not a cost to manage.</li>'
        f'<li><strong>Variable overhead, {pct(r["var_oh_pct"])}.</strong> The line to watch. Total overhead is {pct(r["overhead_of_gp"])} of gross profit, inside the 20 to 30% agencies run [1], '
        f'but {money(r["travel"])} of it is travel not priced into quotes and {money(r["discretionary"])} is meals, groceries and reimbursements.</li>'
        '<li>Fix those two and this table beats every peer group on every line.</li></ul>'
        +         f'<h3 class="sect">Product, {money(r["product"])} a month ({pct(r["product_pct"], 1)})</h3>'
        + _table(["Vendor", "Avg per month"] + month_heads, vendors)
        + f'<h3 class="sect">Event staff, {money(r["staff"])} a month ({pct(r["staff_pct"], 1)})</h3>'
        + _table(["Source", "Avg per month", "% of revenue"] + month_heads, staff_rows)
        + f'<p>Targets: product at or under {pct(t["product_pct"])}. Event staff at or under {pct(t["staff_pct"])}, quoted per event as '
        'staff hours times rate divided by coconut count before the event is booked.</p>'
    )


def _overhead(c, r) -> str:
    rows = []
    for g in c["overhead_groups"]:
        items = ", ".join(f'{e(l)} {money(v)}' for l, v in g["items"])
        note = P.OVERHEAD_GROUP_NOTES.get(g["name"], "")
        tag = ' <span class="pill nothired">fixed</span>' if g["fixed"] else ""
        rows.append(_tr([f'<strong>{e(g["name"])}</strong>{tag}' + (f'<div class="small">{e(note)}</div>' if note else ""), money(g["avg"]), f'<span class="small">{items}</span>']))
    return (
        f'<h2>Overhead, {money(r["var_oh"] + r["fixed_oh"])} a month</h2>'
        f'<p class="small">Variable overhead is {money(r["var_oh"])} ({pct(r["var_oh_pct"], 1)}). Most of it is not actually variable. '
        f'Rows marked fixed ({money(r["fixed_oh"])}) are in fixed monthly costs below.</p>'
        + _table(["Group", "Avg per month", "What is in it"], rows)
        + f'<p>With discretionary capped at {money(P.RULE_TARGETS["discretionary_cap"])} and travel passed through, variable cost drops to about '
        f'{pct(r["tight_var_pct"])}, every revenue dollar keeps about {r["tight_kept"] * 100:.0f} cents, and break even at full plan drops to about {money(r["tight_breakeven_plan"])}.</p>'
    )


def _fixed(c, r) -> str:
    t = c["core"]
    nut = [
        _tr(["Core team", money(t["actual_total"]), money(t["plan_total"])]),
        _tr(["Software, insurance, ADP fees, storage, marketing", money(r["fixed_oh"]), money(r["fixed_oh"])]),
        _tr(["Monthly cost with no sales", money(r["nut_today"]), money(r["nut_plan"])], "total"),
    ]
    people = [_tr([e(p["person"]) + f'<div class="small">{e(p["role"])}</div>', money(p["actual"]), money(p["plan_total"])]) for p in t["rows"]]
    return ('<h2>Fixed monthly costs</h2>' + _table(["Line", "Today", "Full plan"], nut)
            + '<h3 class="sect">Core team, actual monthly average vs plan</h3>' + _table(["Person", "Actual", "Plan"], people, "plan"))


def _breakeven(r) -> str:
    rows = [
        _tr(["Break even revenue per month", money(r["breakeven_today"]), money(r["breakeven_plan"])]),
        _tr([f'Months of cash if nothing sells ({money(r["cash"])} after card balance)', f'{r["months_today"]:.1f}', f'{r["months_plan"]:.1f}']),
        _tr([f'Same, if the {money(r["ar_total"])} open AR collects', f'{r["months_ar_today"]:.1f}', f'{r["months_ar_plan"]:.1f}']),
    ]
    return ('<h2>Break even and runway</h2>'
            f'<p class="small">Break even revenue is fixed monthly costs divided by the {r["kept"] * 100:.0f} cents left per dollar.</p>'
            + _table(["", "Today", "Full plan"], rows)
            + '<p>Wholesale stops after September, so winter revenue is events only.</p>')


def _rules(r) -> str:
    t = P.RULE_TARGETS
    items = [
        f'Product COGS at or under {pct(t["product_pct"])} of revenue.',
        f'Event staff at or under {pct(t["staff_pct"])} of revenue, quoted per event before booking.',
        'Travel priced into the quote, not budgeted.',
        f'Discretionary spend capped at {money(t["discretionary_cap"])} a month.',
        'Marketing a flat monthly number, set once.',
        f'Under {money(r["breakeven_today"])} of events in the month (about {r["golden_events"]} events), the core team works them. Above it, hourly staff inside the {pct(t["staff_pct"])} cap. Use common sense in between. Harrison stays free to sell.',
        f'Fixed monthly costs {money(r["nut_today"])} today, {money(r["nut_plan"])} at full plan. Break even revenue {money(r["breakeven_today"])} a month today, {money(r["breakeven_plan"])} at plan.',
    ]
    return ('<h2>The rules on one line each</h2><div class="tile plan"><ol class="assume">' + "".join(f"<li>{i}</li>" for i in items) + '</ol></div>'
            '<h2>Open items / Questions</h2><ul class="assume">' + "".join(f"<li>{e(i)}</li>" for i in P.OPEN_ITEMS) + '</ul>')


def _appendix(c) -> str:
    src = "".join(f'<li>{e(t)} <a href="{e(u)}">{e(u)}</a></li>' for t, u in P.SOURCES)
    return ('<details class="appendix"><summary>Appendix: data basis and sources</summary>'
            f'<p class="small">Windansea figures: {e(P.WINDOW_START)} to {e(c["as_of"])} actuals from Ramp (card and checking), Square payouts and ADP. '
            'August prorated to a full month.</p><ol class="assume small">' + src + '</ol></details>')


def rules_tab(c: dict) -> str:
    r = c["rules"]
    return ('<div class="rules">' + _bluf(r)
            + '<h2>Why percentages and caps instead of a budget</h2><p>Revenue swings from $3k in January to $145k in August, so a fixed dollar budget is wrong in most months. Instead, every cost gets one of two rules:</p>'
            '<ol class="assume"><li><strong>Costs that rise and fall with sales</strong> (coconuts, event staff, sales tax, travel) get a target percentage of revenue.</li>'
            '<li><strong>Costs that are the same every month</strong> (salaried people, software, insurance) get a dollar cap.</li></ol>'
            + _scale(c, r) + _overhead(c, r) + _fixed(c, r) + _breakeven(r) + _rules(r) + _appendix(c) + '</div>')
