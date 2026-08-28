# Runway Dashboard, design spec (2026-08-28)

## Purpose

A single HTML page Jordan can share with Harrison that answers, in order:
cash in the bank, money owed to us, hopeful money, what the business costs
per month excluding people, what non core people cost, and what the core
team costs (actual vs the plan in `Windansea_Roles_Responsibilities.docx`).
A second tab lists every role from the doc with its owner and status.

Motivation: Jordan was asked to build a budget. With no recurring revenue and
unproven winter months, the useful first step is "what do we absolutely need
to scale, and what is the runway".

## Sources (all pulled 2026-08-28)

| Data | Source | File |
|---|---|---|
| Cash | Ramp checking balance API | `data/raw/ramp_balance.json` |
| Unpaid card balance | Ramp `get_card_statement_balance` + card spend since statement end | `data/raw/ramp_card_statement.json` |
| Card spend Jun 19 to Aug 28 | Ramp `get_transactions` | `data/raw/ramp_card_jun19_aug28.json` |
| Checking activity Jun 19 to Aug 28 | Ramp `list_wallet_transfers` | `data/raw/ramp_wallet_jun19_aug28.json` |
| May 1 to Jun 18 transactions | existing SQLite `transactions` table (Mercury + Ramp) | `data/coconuts.db` |
| Open AR | Square invoices search | `data/raw/square_invoices.json`, `_p2.json` |
| Payroll by person | ADP Payroll Summary export | `PayrollSummary 4_30_26 to 8_28_26.xlsx` |
| Plan comp and roles | roles doc | `Windansea_Roles_Responsibilities.docx` (values transcribed into `src/runway/plan.py`) |

Mercury is sunset; nothing after Jun 19 comes from it.

## Window

May 1 to Aug 28, 2026. May and Jun 1 to 18 come from the DB, Jun 19 onward
from the raw Ramp pulls. Every average divides by exactly 3 + 28/31 months and August is labeled
partial. The ADP export starts at the 4/30 check date; that check is April
and is excluded.

## Classification rules

Owner confirmed in this session. They extend, not replace, the rules in
CLAUDE.md. Precedence: the section rules below apply first; the DB `bucket`
and `category` are used only as a fallback for rows matching no rule.

**No double counting of payroll.** Every ADP bank debit (WAGE PAY, ADP Tax,
PAY-BY-PAY, ADP PAYROLL FEES, "ADP Payroll") in the DB or Ramp wallet feed
is excluded. People costs come only from the ADP export's Total Expenses
column. ADP fees = the ADP PAYROLL FEES bank debits, counted in overhead
(they are not in the export).

**Excluded from everything:** Square deposits into Ramp (revenue is counted
from Square payouts directly), "The Bitter Herb" inflows (own money from the
Mercury close out), Ramp statement payments (card paydowns, already counted
as card spend), transfers to Mercury SoCal, interest, failed or errored
transfers.

**Revenue** (used only for the runway strip): Square payouts net of fees +
company ACH and cleared check deposits into Ramp. Currency Cloud $67,226 on
Aug 5 is a customer payment.

**Sales tax:** CA DEPT TAX / CDTFA outflows. Own section, in no average.

**Product / COGS:** Sun Hing Foods, Coy's Produce, Alibaba, Manila Oriental,
Vien Dong, Ematik Vending Carts, Packola, ULINE, ImprintNow, Gearheart
Industry, Wrap Caviar, and any transaction already bucketed COGS in the DB.

**Overhead:** every other non people outflow (never Jordan's draws, which
appear only in the core people table and the plan burn): travel, software, insurance,
restaurants, fuel, storage, marketing, accounting (Kosmos), consultants not
named as people (Coach Roach), photographers (Miguel Flores, Jenn Kham,
Lavish & Co), ADP fees, and reimbursements paid to anyone.

**People, non core:** ADP employer total expense for everyone except
Harrison, Trent, Juniper; Venmo, Tremendous and Apple Cash outflows; Indico
Thread Consulting; Nathan Zini (card and bill pay); Josh Escalante (bill pay,
his ADP lines are already in the ADP hourly total).

**People, core** (name, actual sources, plan monthly total cost from doc):

| Role | Person | Actual sources | Plan |
|---|---|---|---|
| Owner | Harrison Goldfarb | ADP + outflows to Chase 8371, JPMorgan Ext Trnsfr, Chase card and Amex paydowns | $2,500 payroll + $4,000 draw = $6,500 |
| GM / Ops Manager | Trent Livolsi | ADP | $9,125 |
| Executive Assistant | Juniper Judd | ADP | $1,200 |
| Systems & Advisor | Jordan Millhausen | BofA 4201 transfers + Capital One Auto | $2,700 |
| Assistant Ops Manager | not hired | none | $5,625 |
| Social Media | Edy, not hired | none | $3,250 |

The $3,400 BofA transfer on 2026-06-01 stays split per CLAUDE.md ($2,000
Jordan, $1,400 Harrison).

## Page layout (tab 1, "Dashboard")

1. **Header**: Windansea Coconuts, Runway, "data as of Aug 28, 2026".
2. **Row 1, three tiles**
   - Money in the bank (green): Ramp checking balance. Sub line: unpaid card
     balance since the last statement, and cash available after paying it.
   - Money owed to us (AR): Square open invoice total and count. Open =
     status UNPAID, PARTIALLY_PAID or SCHEDULED; amount open = requested
     amount minus completed amount; DRAFT and CANCELED excluded. Click
     expands a table: customer, invoice title, amount open, due date, overdue
     highlighted.
   - Hopeful money: "TBD".
3. **Row 2, monthly average expenses (not people)**: two tiles, Product /
   COGS and Overhead, each with a 4 bar mini chart May to Aug and a hover
   list of the top merchants.
4. **Row 3, sales tax**: one small tile, remitted by month, labeled pass
   through, not in any average.
5. **Row 4, people (non core)**: tile with monthly average, 4 bar chart,
   hover shows ADP hourly vs Venmo vs named contractors.
6. **Row 5, core people table**: rows per role above. Columns: person,
   status, actual avg per month May to Aug, plan per doc, difference.
   Totals row: actual vs $28,400. Footnote on Juniper (ADP ~$3.8k/mo vs
   doc $1,200) and Harrison (lumpy direct transfers).
7. **Bottom section, runway and projection**: a month by month cash
   projection Sep 2026 to Aug 2027, computed in page JavaScript from knobs
   the viewer can edit (defaults in parentheses, all derived from the data
   where possible):
   - Hire start month for the full $28,400 core plan (Oct 2026). Before it,
     core people = actual May to Aug average.
   - Baseline revenue curve: 2026 actuals Jan to Aug for the same months of
     2027; Sep to Dec 2026 = August (ex one off) times 0.7, 0.45, 0.2, 0.15,
     each editable.
   - Wholesale season months (May to Sep). Outside the season wholesale is
     zero; accounts die after summer (owner confirmed).
   - New wholesale accounts per month in season from Harrison selling full
     time (3), and in season value per account per month ($1,500). Adds
     cumulatively within a season, resets at season end.
   - Events multiplier from ads and organic (1.0), applied to the baseline.
   - One off deals: a free text list of (month, amount), empty by default.
   - COGS as % of revenue (derived May to Aug) and non core people as % of
     revenue (derived May to Aug); overhead fixed at its May to Aug average.
   - Sales tax remitted as % of revenue (derived May to Aug), because revenue
     is measured as collected with tax included.
   Output: table (month, revenue, burn, cash), a cash line chart, and a
   callout "lowest cash: $X in <month>" plus "cash positive through <month>"
   or "runs out in <month>". Starting cash = money in the bank tile.
   Three preset buttons load Status quo (0 new accounts, 1.0), Plan (3,
   1.25), Aggressive (5, 1.5).

Every tile has a hover tooltip stating its source and window. No dashes as
pauses in any label. Light and dark theme aware. Single self contained file.

## Tab 2, "Roles from the doc"

A table of all nine functional areas and their responsibilities from the
doc, with columns: area, responsibility, owner, status. Status values:
filled, not hired, no owner. The "Remaining Gaps" section renders as rows with status "no
owner". Below it, the doc's compensation table verbatim with the $28,400
total.

## Implementation

- `src/runway/classify.py`: pure functions that take raw Ramp card, wallet,
  DB rows, ADP rows and return tagged records `(date, amount, section,
  subsection, label)`. Sections: excluded, revenue, sales_tax, cogs,
  overhead, people_noncore, people_core. Unit tested.
- `src/runway/aggregate.py`: monthly sums, averages with proration, AR
  summary, core people table, projection defaults (derived ratios and
  baseline curve). Unit tested. The projection arithmetic itself runs in
  page JS (`src/runway/projection.js`, inlined at build) and is mirrored by
  a Python reference implementation `src/runway/projection.py` that the
  tests use to check the defaults produce sane numbers.
- `src/runway/build.py`: loads sources, calls the above, renders
  `docs/runway_dashboard.html` from an inline HTML template (Python string
  formatting, no new dependencies). Constants for plan comp and the roles
  list live in `src/runway/plan.py`.
- Run: `.venv/bin/python -m src.runway.build`. Publish the HTML as an
  artifact.
- Each file under 500 lines. Tests in `tests/test_runway_*.py`.

## Error handling

Missing raw file: build fails with the file name. Unknown merchant: lands in
overhead and is listed in a "Review" block at the bottom of the page with
count and total so nothing is silently absorbed. ADP names that match no
core person are hourly staff by definition.

## Out of scope

Pipeline integration (TBD tile), refreshing data without a Claude session,
editing the existing Flask dashboard, net income.
