"""Build docs/runway_dashboard.html. Run: .venv/bin/python -m src.runway.build"""

import sqlite3
from pathlib import Path

from src import aggregate as legacy
from src.runway import aggregate as A
from src.runway import loaders as L
from src.runway import plan as P
from src.runway.classify import tag_adp_row, tag_card, tag_db_row, tag_wallet
from src.runway.render_page import page
from src.runway.render_projection import projection_section

OUT = L.ROOT / "docs" / "runway_dashboard.html"
JS = Path(__file__).with_name("projection.js")
CURRENCY_CLOUD = 67226.0


def build_context() -> dict:
    card = [tag_card(t) for t in L.load_card()]
    recs = A.flatten(card + [tag_wallet(t) for t in L.load_wallet()]
                     + [tag_db_row(r) for r in L.load_db_rows()] + [tag_adp_row(r) for r in L.load_adp()])
    card_recs = A.flatten(card)
    months = A.monthly_by_section(recs)
    avgs = {s: A.average(months[s]) for s in P.SECTIONS}
    balance = L.load_balance()
    cash = float(balance["available_balance"])
    owed = A.card_owed(L.load_statement(), card_recs)

    # Jan to Apr revenue from the existing pipeline, May to Aug from this one.
    conn = sqlite3.connect(L.DB)
    rev_2026 = {m: v["revenue"] for m, v in legacy.monthly(conn).items() if m < "2026-05"}
    conn.close()
    rev_2026.update({m: months[P.REVENUE][m] / P.MONTH_WEIGHTS[m] for m in P.MONTHS})

    return {
        "as_of": balance.get("as_of", P.WINDOW_END),
        "cash": cash, "card_owed": owed, "cash_after": cash - owed,
        "ar": A.ar_summary(L.load_invoices(), P.WINDOW_END),
        "months": months, "avgs": avgs,
        "tops": {P.COGS: A.top_labels(recs, P.COGS), P.OVERHEAD: A.top_labels(recs, P.OVERHEAD, 10)},
        "noncore_subs": A.monthly_by_sub(recs, P.PEOPLE_NONCORE),
        "core": A.core_table(recs),
        "unknown": A.unknown_merchants(recs),
        "rev_months": rev_2026,
        "overhead_split": A.overhead_split(recs),
        "proj": A.projection_defaults(avgs, rev_2026, CURRENCY_CLOUD, A.overhead_split(recs)),
    }


def render(ctx: dict) -> str:
    proj_html = projection_section(ctx["proj"], ctx["cash_after"], ctx["avgs"][P.PEOPLE_CORE])
    return page(ctx, proj_html, JS.read_text())


def main(out: Path = OUT) -> Path:
    ctx = build_context()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(ctx))
    for s in P.SECTIONS:
        print(f"{s:15s} avg {ctx['avgs'][s]:>10,.0f}  " + "  ".join(f"{m[5:]}={ctx['months'][s][m]:,.0f}" for m in P.MONTHS))
    print(f"cash {ctx['cash']:,.2f} card owed {ctx['card_owed']:,.2f} AR {ctx['ar']['total']:,.2f} ({ctx['ar']['count']})")
    print(f"review items {len(ctx['unknown'])}; wrote {out} ({out.stat().st_size // 1024} kB)")
    return out


if __name__ == "__main__":
    main()
