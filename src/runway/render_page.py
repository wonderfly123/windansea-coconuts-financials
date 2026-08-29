"""HTML for the dashboard tab and the roles tab. Strings in, string out.

ctx keys (built in build.py): as_of, cash, card_owed, cash_after, ar, months,
avgs, tops, noncore_subs, core, sales_tax, unknown, rev_months.
"""

from html import escape as e

from src.runway import plan as P

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600'
         '&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')

CSS = """
:root{--bg:#f4efe6;--panel:#fffdf8;--panel2:#f0e9db;--ink:#1c2a2e;--muted:#5d7176;--line:#dcd3c2;
--sea:#1f8f6a;--sea-soft:#d8efe4;--husk:#a6742f;--husk-soft:#f1e4cf;--bad:#c2452e;--bad-soft:#f6dcd5;--focus:#1f8f6a;}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0e191d;--panel:#152329;--panel2:#1c2d34;--ink:#e6eeef;--muted:#8ea5aa;--line:#26383f;
--sea:#3fcf9c;--sea-soft:#153a30;--husk:#d8a65b;--husk-soft:#3a2d18;--bad:#f0735a;--bad-soft:#3f1f19;--focus:#3fcf9c;}}
:root[data-theme="dark"]{--bg:#0e191d;--panel:#152329;--panel2:#1c2d34;--ink:#e6eeef;--muted:#8ea5aa;--line:#26383f;
--sea:#3fcf9c;--sea-soft:#153a30;--husk:#d8a65b;--husk-soft:#3a2d18;--bad:#f0735a;--bad-soft:#3f1f19;--focus:#3fcf9c;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans",-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.45}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:34px;margin:0;letter-spacing:-.01em;text-wrap:balance}
h2{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:22px;margin:36px 0 12px}
h3{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 6px}
.sub{color:var(--muted);margin:4px 0 0}
.tabs{display:flex;gap:6px;margin:22px 0 4px;border-bottom:1px solid var(--line)}
.tabs button{background:none;border:0;border-bottom:2px solid transparent;color:var(--muted);font:inherit;font-weight:500;padding:10px 14px;cursor:pointer}
.tabs button.on{color:var(--ink);border-bottom-color:var(--sea)}
.tabs button:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.tab{display:none}.tab.on{display:block}
.grid{display:grid;gap:14px}.g3{grid-template-columns:repeat(3,1fr)}.g2{grid-template-columns:repeat(2,1fr)}
@media(max-width:820px){.g3,.g2{grid-template-columns:1fr}}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;position:relative}
.tile.good{border-color:var(--sea);background:linear-gradient(180deg,var(--sea-soft),var(--panel) 70%)}
.tile.plan{border-color:var(--husk)}
.big{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:38px;line-height:1.1;font-variant-numeric:tabular-nums;margin:2px 0 4px}
.big.tbd{color:var(--muted);font-weight:500}
.note{color:var(--muted);font-size:13px}
.tip{position:absolute;top:14px;right:14px;width:20px;height:20px;border-radius:50%;border:1px solid var(--line);color:var(--muted);font-size:12px;display:flex;align-items:center;justify-content:center;cursor:help}
.tip:hover+.tipbox,.tip:focus+.tipbox{display:block}
.tipbox{display:none;position:absolute;right:14px;top:40px;z-index:5;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:13px;max-width:320px;box-shadow:0 8px 24px rgba(0,0,0,.18)}
.tipbox ul{margin:6px 0 0;padding-left:16px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
td.num,th.num{text-align:right}
tr.total td{font-weight:600;border-top:2px solid var(--ink);border-bottom:0}
tr.neg td{color:var(--bad)}
.tscroll{overflow-x:auto}
.pill{display:inline-block;font-size:12px;padding:2px 8px;border-radius:999px;font-weight:500;white-space:nowrap}
td.status{white-space:nowrap;width:1%}
.pill.filled{background:var(--sea-soft);color:var(--sea)}.pill.nothired{background:var(--husk-soft);color:var(--husk)}.pill.noowner{background:var(--bad-soft);color:var(--bad)}
.pill.overdue{background:var(--bad-soft);color:var(--bad)}
details summary{cursor:pointer;color:var(--sea);font-weight:500;margin-top:8px}
.bars{display:flex;gap:6px;align-items:flex-end;height:104px;margin-top:18px}
.bar{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;font-size:11px;color:var(--muted)}
.bar i{display:block;width:100%;background:var(--sea);border-radius:3px 3px 0 0;min-height:2px;max-height:60px}
.bar.husk i{background:var(--husk)}.bar.muted i{background:var(--muted)}
.bar b{font-weight:500;color:var(--ink);font-size:11px}
.strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:8px}
@media(max-width:820px){.strip{grid-template-columns:repeat(2,1fr)}}
.strip div{background:var(--panel2);border-radius:8px;padding:10px 12px;font-size:13px}
.strip strong{display:block;font-size:18px;font-variant-numeric:tabular-nums}
.knobs{display:grid;grid-template-columns:repeat(4,1fr);gap:10px 14px;margin:10px 0}
@media(max-width:820px){.knobs{grid-template-columns:repeat(2,1fr)}}
.knobs label{font-size:12px;color:var(--muted);display:flex;flex-direction:column;gap:4px}
.knobs input,.knobs textarea{font:inherit;font-size:14px;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);width:100%}
.knobs textarea{min-height:60px;font-family:"IBM Plex Mono",monospace;font-size:12px}
.presets{display:flex;gap:8px;margin:12px 0 4px;flex-wrap:wrap}
.presets button{font:inherit;font-size:13px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
.presets button.on{background:var(--sea);border-color:var(--sea);color:#fff}
.scenario{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:12px 0 4px}
@media(max-width:820px){.scenario{grid-template-columns:repeat(2,1fr)}}
.scenario div{background:var(--panel2);border-radius:8px;padding:10px 12px;font-size:12px;color:var(--muted)}
.scenario strong{display:block;color:var(--ink);font-size:17px;font-variant-numeric:tabular-nums;margin-top:2px}
.scenario .what{grid-column:1 / -1}.scenario .what strong{font-size:14px;font-weight:500}
.people{grid-template-columns:1fr 1.4fr}@media(max-width:820px){.people{grid-template-columns:1fr}}
.gtm{border-top:4px solid var(--line)}.gtm.sea{border-top-color:var(--sea)}.gtm.husk{border-top-color:var(--husk)}.gtm.muted{border-top-color:var(--muted)}
.gtm p{margin:8px 0;font-size:14px}.gtm .owner{font-size:14px;margin:2px 0 6px}
.assume{margin:8px 0 4px;font-size:15px;max-width:70ch}
.assume li{margin:6px 0}
#projection details summary{margin:18px 0 6px}
.baseline{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:8px 0}
@media(max-width:820px){.baseline{grid-template-columns:repeat(3,1fr)}}
.baseline label{font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:2px}
.baseline input{font:inherit;font-size:13px;padding:4px 6px;border:1px solid var(--line);border-radius:5px;background:var(--panel);color:var(--ink);width:100%}
#proj-chart{position:relative}#proj-chart svg{width:100%;height:auto;display:block;margin-top:8px;cursor:crosshair;touch-action:none}
#proj-chart .scrub{stroke:var(--ink);stroke-width:1;opacity:.5}#proj-chart .scrubdot{fill:var(--ink);stroke:var(--panel);stroke-width:2}
.scrubbox{display:none;position:absolute;top:12px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px;pointer-events:none;font-variant-numeric:tabular-nums;box-shadow:0 6px 18px rgba(0,0,0,.15)}
#proj-chart .grid{stroke:var(--line);stroke-width:1}#proj-chart .zero{stroke:var(--bad);stroke-width:2}
#proj-chart .below{fill:var(--bad);opacity:.10}#proj-chart .zerolabel{fill:var(--bad);font-size:11px;font-weight:600;font-family:"IBM Plex Sans",sans-serif}
#proj-chart .startlabel{fill:var(--ink);font-size:11px;font-weight:600;font-family:"IBM Plex Sans",sans-serif}
#proj-chart .tick{fill:var(--muted);font-size:11px;font-family:"IBM Plex Sans",sans-serif}
#proj-chart .line{fill:none;stroke:var(--sea);stroke-width:2}#proj-chart .area{fill:var(--sea);opacity:.12}
#proj-chart .dot{fill:var(--sea);stroke:var(--panel);stroke-width:2}#proj-chart .dot.bad{fill:var(--bad)}
.callout{margin:10px 0;font-size:16px}.callout .bad{color:var(--bad);font-weight:600}.callout .good{color:var(--sea);font-weight:600}
.small{font-size:13px;color:var(--muted)}
.review td{font-size:13px}
@media (prefers-reduced-motion: no-preference){.tile{transition:border-color .15s}}
"""


def money(v, cents=False) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}" if cents else f"{sign}${abs(v):,.0f}"


def tip(text, items=None) -> str:
    lis = "".join(f"<li>{e(i)}</li>" for i in (items or []))
    return (f'<span class="tip" tabindex="0" aria-label="Source">i</span>'
            f'<div class="tipbox">{e(text)}{("<ul>" + lis + "</ul>") if lis else ""}</div>')


def bars(months: dict, cls="") -> str:
    mx = max([abs(v) for v in months.values()] + [1])
    out = []
    for m in P.MONTHS:
        v = months.get(m, 0.0)
        h = max(2, round(56 * abs(v) / mx))
        out.append(f'<div class="bar {cls}"><b>{money(v)}</b><i style="height:{h}px"></i><span>{e(P.MONTH_LABELS[m].split(" ")[0])}</span></div>')
    return f'<div class="bars">{"".join(out)}</div>'


def _tile_cash(c) -> str:
    return (f'<div class="tile good">{tip("Ramp checking available balance on " + c["as_of"] + ". Card charges since the Aug 8 statement are still to be paid from this balance.")}'
            f'<h3>Money in the bank</h3><div class="big">{money(c["cash"])}</div>'
            f'<div class="note">Ramp card charges not yet paid {money(c["card_owed"])}. Available after paying: <strong>{money(c["cash_after"])}</strong>.</div></div>')


def _tile_ar(c) -> str:
    ar = c["ar"]
    overdue_pill = '<span class="pill overdue">overdue</span>'
    rows = "".join(
        f'<tr><td>{e(r["customer"])}</td><td>{e(r["title"][:48])}</td><td class="num">{money(r["amount"], True)}</td>'
        f'<td>{e(r["due"])} {overdue_pill if r["overdue"] else ""}</td></tr>' for r in ar["rows"])
    overdue = sum(r["amount"] for r in ar["rows"] if r["overdue"])
    return (f'<div class="tile">{tip("Open Square invoices (UNPAID, PARTIALLY PAID or SCHEDULED) as of " + c["as_of"] + ". Jordan confirmed Square status is kept current when customers pay by check or ACH.")}'
            f'<h3>Money owed to us</h3><div class="big">{money(ar["total"])}</div>'
            f'<div class="note">{ar["count"]} open invoices, {money(overdue)} past due.</div>'
            f'<details><summary>Show invoices</summary><div class="tscroll"><table><thead><tr><th>Customer</th><th>Invoice</th><th class="num">Open</th><th>Due</th></tr></thead><tbody>{rows}</tbody></table></div></details></div>')


def _tile_hopeful() -> str:
    return ('<div class="tile"><h3>Hopeful money</h3><div class="big tbd">TBD</div>'
            '<div class="note">Deals being worked and their total value. No pipeline source yet.</div></div>')


def _tile_avg(title, key, c, cls, tipline) -> str:
    items = [f"{n}: {money(v)}" for n, v in c["tops"][key]]
    return (f'<div class="tile">{tip(tipline, items)}<h3>{e(title)}</h3><div class="big">{money(c["avgs"][key])}</div>'
            f'<div class="note">per month, May to Aug 2026 (Aug to the 28th, prorated)</div>{bars(c["months"][key], cls)}</div>')


def _tile_sales_tax(c) -> str:
    return (f'<div class="tile">{tip("CDTFA / CA DEPT TAX remittances. Pass through, not in any average or in the projection.")}'
            f'<h3>Sales tax remitted</h3><div class="big">{money(sum(c["months"][P.SALES_TAX].values()))}</div>'
            f'<div class="note">May to Aug total, kept out of every average</div>{bars(c["months"][P.SALES_TAX], "muted")}</div>')


def _tile_noncore(c) -> str:
    subs = c["noncore_subs"]
    names = {P.SUB_ADP_HOURLY: "ADP hourly staff", P.SUB_VENMO: "Venmo / Tremendous event staff", P.SUB_CONTRACTOR: "Indico Thread, Nathan Zini, Josh Escalante"}
    items = [f"{names.get(k, k)}: {money(sum(v.values()) / sum(P.MONTH_WEIGHTS.values()))} avg" for k, v in subs.items()]
    return (f'<div class="tile">{tip("ADP employer total cost for everyone except Harrison, Trent and Juniper, plus Venmo and Tremendous payouts and the three named contractors. Varies with event volume.", items)}'
            f'<h3>Event staff and contractors</h3><div class="big">{money(c["avgs"][P.PEOPLE_NONCORE])}</div>'
            f'<div class="note">per month average; swings with the event calendar</div>{bars(c["months"][P.PEOPLE_NONCORE], "husk")}</div>')


def _core_table(c) -> str:
    t = c["core"]
    rows = []
    for r in t["rows"]:
        pill = {"filled": "filled", "not hired": "nothired"}[r["status"]]
        rows.append(f'<tr><td>{e(r["person"])}<div class="small">{e(r["role"])}</div></td>'
                    f'<td class="status"><span class="pill {pill}">{e(r["status"])}</span></td>'
                    f'<td class="num">{money(r["plan_total"])}</td></tr>')
    rows.append(f'<tr class="total"><td>Total per month</td><td></td><td class="num">{money(t["plan_total"])}</td></tr>')
    return ('<div class="tile plan"><h3>Core team, plan</h3><div class="tscroll"><table><thead><tr><th>Role</th><th>Status</th>'
            '<th class="num">Cost per month</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
            '<p class="small">Fully loaded monthly cost from the roles doc (25% payroll tax where it applies), plus Tim Kosmos for bookkeeping. '
            f'Today the filled roles cost about {money(t["actual_total"])} a month.</p></div>')


def _gtm() -> str:
    cards = []
    for g in P.GTM:
        cards.append(
            f'<div class="tile gtm {g["cls"]}"><h3>{e(g["lane"])}</h3>'
            f'<div class="owner">Owner: <strong>{e(g["owner"])}</strong></div>'
            f'<p>{e(g["what"])}</p><p><strong>How it sells.</strong> {e(g["how"])}</p>'
            f'<p><strong>When it pays.</strong> {e(g["season"])}</p></div>')
    return ('<h2>How we sell</h2>'
            '<div class="grid g3">' + "".join(cards) + '</div>')


def _review(c) -> str:
    if not c["unknown"]:
        return ""
    rows = "".join(f'<tr><td>{e(n)}</td><td class="num">{money(v)}</td><td class="num">{k}</td></tr>' for n, v, k in c["unknown"])
    return (f'<h2>Review</h2><p class="small">Overhead items with no category or a generic one. They are counted in overhead; tell Jordan if any belong elsewhere.</p>'
            f'<div class="tile review"><div class="tscroll"><table><thead><tr><th>Payee</th><th class="num">May to Aug</th><th class="num">Items</th></tr></thead><tbody>{rows}</tbody></table></div></div>')


def dashboard_tab(c, projection_html) -> str:
    return (
        '<div class="grid g3">' + _tile_cash(c) + _tile_ar(c) + _tile_hopeful() + '</div>'
        '<h2>Monthly costs, no people</h2>'
        '<div class="grid g3">'
        + _tile_avg("Product and coconuts", P.COGS, c, "", "Sun Hing, Coy's Produce, Gearheart, Alibaba, carts, packaging and anything bucketed COGS.")
        + _tile_avg("Overhead", P.OVERHEAD, c, "muted", "Everything else that is not people: travel, software, insurance, rentals, meals, consultants and photographers, reimbursements, ADP fees.")
        + _tile_sales_tax(c)
        + '</div>'
        '<h2>Monthly costs, people</h2>'
        '<div class="grid g2 people">' + _tile_noncore(c) + _core_table(c) + '</div>'
        + projection_html
    )


def roles_tab() -> str:
    rows = []
    cls = {"filled": "filled", "not hired": "nothired", "no owner": "noowner"}
    for area, items in P.ROLES:
        for i, (resp, owner, status) in enumerate(items):
            first = f'<td rowspan="{len(items)}"><strong>{e(area)}</strong></td>' if i == 0 else ""
            rows.append(f'<tr>{first}<td>{e(resp)}</td><td>{e(owner)}</td><td class="status"><span class="pill {cls[status]}">{e(status)}</span></td></tr>')
    comp = "".join(f'<tr><td>{e(n)}</td><td class="num">{money(g)}</td><td class="num">{money(t)}</td><td class="num">{money(tot)}</td></tr>' for n, g, t, tot in P.PLAN_COMP)
    comp += f'<tr class="total"><td>Total monthly</td><td class="num">{money(sum(r[1] for r in P.PLAN_COMP))}</td><td class="num">{money(sum(r[2] for r in P.PLAN_COMP))}</td><td class="num">{money(P.PLAN_TOTAL)}</td></tr>'
    return ('<h2>Every role the business needs</h2>'
            '<div class="tile"><div class="tscroll"><table><thead><tr><th>Area</th><th>Responsibility</th><th>Owner</th><th>Status</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table></div></div>'
            '<h2>Monthly compensation in the plan</h2>'
            '<div class="tile plan"><div class="tscroll"><table><thead><tr><th>Role</th><th class="num">Gross</th><th class="num">Payroll tax (25%)</th><th class="num">Total cost</th></tr></thead><tbody>'
            + comp + '</tbody></table></div><p class="small">Harrison: $2,000 through payroll (taxed), $4,000 as an owner draw. Contractors carry no payroll tax. Tim Kosmos is added on top of the $28,400 in the doc.</p></div>')


def page(c, projection_html, projection_js) -> str:
    return (
        f'<title>Windansea Coconuts Runway</title>{FONTS}<style>{CSS}</style>'
        '<div class="wrap">'
        f'<h1>Windansea Coconuts, runway</h1><p class="sub">Data as of {e(c["as_of"])}. Ramp, Square and ADP.</p>'
        '<div class="tabs" role="tablist"><button class="on" data-tab="dash" role="tab">Dashboard</button><button data-tab="gtm" role="tab">How we sell</button><button data-tab="roles" role="tab">Company roles</button></div>'
        f'<section class="tab on" id="tab-dash">{dashboard_tab(c, projection_html)}</section>'
        f'<section class="tab" id="tab-gtm">{_gtm()}</section>'
        f'<section class="tab" id="tab-roles">{roles_tab()}</section>'
        '</div>'
        '<script>document.querySelectorAll(".tabs button").forEach(b=>b.addEventListener("click",()=>{'
        'document.querySelectorAll(".tabs button").forEach(x=>x.classList.toggle("on",x===b));'
        'document.querySelectorAll(".tab").forEach(s=>s.classList.toggle("on",s.id==="tab-"+b.dataset.tab));}));</script>'
        f'<script>{projection_js}</script>'
    )
