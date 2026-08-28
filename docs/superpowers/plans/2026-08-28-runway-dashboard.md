# Runway Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `docs/runway_dashboard.html`, a self contained page showing cash, AR, expenses, people (non core and core vs plan), a roles appendix, and an editable cash projection, from the data already pulled into `data/raw/` and `data/coconuts.db`.

**Architecture:** Pure Python classification and aggregation modules (no I/O) fed by a thin loader, rendered into one HTML string with the projection math in inlined JS. Spec: `docs/superpowers/specs/2026-08-28-runway-dashboard-design.md`.

**Tech Stack:** Python 3 stdlib + openpyxl + sqlite3 (already in `.venv`), pytest. No new dependencies. Not a git repo: no commit steps.

---

## File structure

| File | Responsibility |
|---|---|
| `src/runway/__init__.py` | empty |
| `src/runway/plan.py` | constants: core people map, plan comp, roles list from the doc, merchant lists, window dates |
| `src/runway/classify.py` | `tag_card`, `tag_wallet`, `tag_db_row`, `tag_adp_row` each return a `Rec(date, amount, section, sub, label)` or None |
| `src/runway/loaders.py` | read raw json/xlsx/sqlite into plain dicts; the only file with I/O besides build |
| `src/runway/aggregate.py` | monthly sums, averages, AR summary, core table, projection defaults |
| `src/runway/projection.py` | Python reference of the JS projection (for tests) |
| `src/runway/render.py` | HTML/CSS/JS template functions returning strings |
| `src/runway/build.py` | `main()`: load, classify, aggregate, render, write `docs/runway_dashboard.html` |
| `tests/test_runway_classify.py`, `tests/test_runway_aggregate.py`, `tests/test_runway_projection.py`, `tests/test_runway_build.py` | tests |

Sections (strings in plan.py): `EXCLUDED, REVENUE, SALES_TAX, COGS, OVERHEAD, PEOPLE_NONCORE, PEOPLE_CORE`. Core `sub` = person key (`harrison, trent, juniper, jordan`). Non core `sub` ∈ `adp_hourly, venmo, contractor`.

### Task 1: plan.py constants
- [ ] Write `src/runway/plan.py` with: `WINDOW_START="2026-05-01"`, `WINDOW_END="2026-08-28"`, `RAW_CUTOVER="2026-06-19"`, `MONTHS=["2026-05","2026-06","2026-07","2026-08"]`, `MONTH_WEIGHTS={"2026-08":28/31}` (others 1.0), section names, `CORE_PEOPLE` list of dicts (key, role, person, status, plan_gross, plan_total, adp_name or None), `PLAN_TOTAL=28400`, `ADP_CORE_NAMES={"Goldfarb, Harrison L":"harrison","Livolsi, Trent":"trent","Judd, Juniper":"juniper"}`, `COGS_MERCHANTS`, `NONCORE_CONTRACTORS={"Indico Thread","Nathan Zini","Josh Escalante"}`, `ROLES` (nine areas from the docx, each with responsibilities and owner/status), `GAPS` list.
- [ ] No test; it is data. Verify `python -c "import src.runway.plan"`.

### Task 2: classify.py (TDD)
- [ ] Test file `tests/test_runway_classify.py` covering: card Sun Hing → COGS; card Uber → OVERHEAD; card Nathan Zini → PEOPLE_NONCORE/contractor; card DECLINED → None; wallet Square deposit → EXCLUDED; wallet Currency Cloud deposit → REVENUE; wallet Bitter Herb deposit → EXCLUDED; wallet ADP WAGE PAY → EXCLUDED; wallet ADP PAYROLL FEES → OVERHEAD; wallet STATEMENT_PAYMENT → EXCLUDED; wallet CA DEPT TAX → SALES_TAX; wallet VENMO → PEOPLE_NONCORE/venmo; wallet TOTAL CHECKING 8371 → PEOPLE_CORE/harrison; wallet Adv Plus 4201 → PEOPLE_CORE/jordan; wallet CAPITAL ONE AUTO → PEOPLE_CORE/jordan; wallet REIMBURSEMENT → OVERHEAD; wallet ERROR status → None; wallet BILLPAY memo "Bill #IL3 - SUN HING FOODS" → COGS; billpay Josh Escalante → PEOPLE_NONCORE; db row bucket Excluded counterparty "CA DEPT TAX FEE" → SALES_TAX (rule beats bucket); db row ADP WAGE PAY → EXCLUDED; db Square Inc inflow → EXCLUDED; db Datafold revenue → REVENUE; db Chase 8371 flag Harrison → PEOPLE_CORE/harrison; db BofA 4201 on 2026-06-01 amount -3400 → two recs (jordan 2000, harrison 1400); db date >= RAW_CUTOVER → None; adp row Harrison → PEOPLE_CORE/harrison amount = Total Expenses; adp row Grace → PEOPLE_NONCORE/adp_hourly; adp check date 04/30/2026 → None.
- [ ] Run, expect ImportError.
- [ ] Implement `src/runway/classify.py` (< 250 lines) with a merchant matcher `_match(name, keys)` (case insensitive substring) and the four functions. Amounts returned positive for outflows and for revenue (section tells direction).
- [ ] Run tests, all pass.

### Task 3: loaders.py
- [ ] Implement readers: `load_card(path)`, `load_wallet(path)`, `load_db_rows(db_path, start, end)` returning dicts with date, counterparty, description, category, bucket, flag, amount, `load_adp(xlsx)` returning rows (check_date iso, name, total_expenses), `load_invoices(paths)`, `load_balance`, `load_statement`. Smoke test in `tests/test_runway_build.py` that each loads the real files and returns > 0 rows.

### Task 4: aggregate.py (TDD)
- [ ] Tests: `monthly_by_section(recs)` → `{section: {month: total}}`; `average(month_totals)` divides by `sum(weights)=3+28/31`; `ar_summary(invoices)` returns total 60003.70 and count 37 on real data and correct open amounts on a fixture with PARTIALLY_PAID; `core_table(recs)` gives per person actual avg, plan, diff and totals; `projection_defaults(section_avgs, revenue_by_month_2026)` returns cogs_pct, noncore_pct, overhead_fixed, baseline curve for 12 months.
- [ ] Implement, run, pass.

### Task 5: projection.py + projection.js (TDD)
- [ ] Python `project(knobs) -> list of {month, revenue, burn, cash}` for Sep 2026 to Aug 2027. Tests: with zero revenue and no hire, cash falls by fixed burn each month; wholesale adds only in season and resets; hire month switches core cost; lowest cash callout correct.
- [ ] Write `src/runway/projection.js` implementing the same function on the same knob names; `render.py` inlines it. Test that the JS file contains every knob key string from the Python knobs dict (cheap parity check).

### Task 6: render.py
- [ ] Functions: `page(ctx) -> str` assembling head (CSS with light/dark tokens), tabs, tiles, tables, projection section, review block. Use `html.escape` on all data strings. No dashes as pauses in labels. Test: output contains "Money in the bank", "$127,455", "TBD", "Roles from the doc", and no "—" or " - " inside `<h` or `<th` tags.

### Task 7: build.py + run
- [ ] `main()` wires everything, writes `docs/runway_dashboard.html`, prints section averages and unknown merchant count. Test runs `main()` to a tmp path and checks file size > 20kB.
- [ ] Run `.venv/bin/pytest`, all green. Run build. Open the HTML, eyeball. Publish as artifact.
