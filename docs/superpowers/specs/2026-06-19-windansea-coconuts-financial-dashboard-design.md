# Windansea Coconuts Financial Health Dashboard — Design Spec

**Date:** 2026-06-19
**Entity:** Windansea Coconuts (operated under The Bitter Herb LLC, an S-corp)
**Owners:** Jordan Millhausen, Harrison Goldfarb

> Formatting rule honored throughout this project: no dashes used as pauses in any
> writing, labels, or generated output. Commas, periods, or restructured sentences only.

## 1. Goal

Deliver a State of the Union for Windansea Coconuts: a reconciled financial picture
from January 1, 2026 to today, drawn from three live MCP connectors (Square, Mercury,
Ramp) plus an ADP payroll export, surfaced as a reusable interactive dashboard backed
by a durable local store. The owner (Jordan) will return to the dashboard over time
and refresh it as new months land.

This is a briefing, not just a reconciliation. It must answer the questions an owner
walks in asking: are we making money, how long does our cash last, what did the owners
draw, and where is the money going. Every headline number is derived from the same
reconciled DB, so the numbers and the narrative cannot disagree.

## 2. Architecture

Single reconciled source of truth feeds two read-only consumers.

```
MCP pull (through Claude)  ->  reconcile module  ->  coconuts.db (SQLite)
                                                          |
                                                          +-- Excel workbook (.xlsx)
                                                          +-- Local dashboard (Flask -> browser)
```

- The reconciliation logic lives in one Python module. It pulls, applies all
  bucket/flag/exclusion rules, and writes to SQLite.
- The Excel workbook and the dashboard both read from the reconciled DB, so they
  cannot disagree. This satisfies the prompt's "build the spreadsheet, reconcile,
  then generate the dashboard from the same numbers" intent with a single store.

### Why SQLite

The dataset is small (roughly 1,000 rows over six months). SQLite is a single file,
needs no server to install, dedups automatically on re-pull via upsert keyed on the
source transaction id, and is the long-term store the owner asked for. Refreshing
next month is a re-pull that upserts into the same DB.

### Why a local Flask app for the dashboard

The owner wants "SQL feeds the dashboard." A plain `file://` HTML page cannot read a
local SQLite file (browser security). A tiny Flask app (`python serve.py` ->
`localhost:8000`) serves the page and answers queries from the DB live, so the
dashboard always reflects current DB contents without regenerating an HTML file.

### Constraint surfaced to the owner

The bank connectors (Mercury, Ramp, Square) are reachable only through the MCP
session, i.e. through Claude. A standalone app cannot self-refresh from the banks.
"Reusable in the future" therefore means: the dashboard stays fully interactive on
its stored data indefinitely, and a monthly "refresh" is a Claude-driven re-pull that
upserts into the same DB. The owner accepted this model.

## 3. Tech stack

- Python (data pull, reconciliation, Excel generation, dashboard server)
- `sqlite3` (standard library) for the store
- `Flask` for the dashboard server and a small JSON data endpoint
- `openpyxl` for the formula-driven Excel workbook
- Chart.js (CDN) for the in-browser revenue chart

## 4. Data store schema (`coconuts.db`)

### `transactions`
Primary key on `id` (the source transaction id) so re-pulls upsert and dedup.

| Column | Notes |
|---|---|
| `id` | TEXT PK. Source transaction id (Mercury/Ramp). Synthetic stable id for ADP rows. |
| `source` | Square / Mercury / Ramp / ADP |
| `account` | Mercury account id or friendly name; Ramp; ADP |
| `date` | ISO date (posting/effective date) |
| `counterparty` | Merchant / payer / payee |
| `description` | Original bank/card description |
| `category` | Derived category (COGS, Software, Marketing, Travel, Meals, Fuel, Rideshare, Inventory, Professional Services, Payroll, etc.) |
| `amount` | REAL, signed. Positive = money in, negative = money out. |
| `bucket` | One of: Revenue, Operating Expense, Payroll, Owner Pay, Owner Draw, Excluded |
| `flag` | Special-item flag (see section 6), else null |
| `review` | Free-text note for anything ambiguous, else null |
| `raw_json` | Full original record for audit |

### `balances`
Live balances captured at pull time.

| Column | Notes |
|---|---|
| `account` | Mercury account id/name, or Ramp |
| `balance` | REAL |
| `as_of` | ISO timestamp |

### `meta`
Key/value: `last_refresh` timestamp, `window_start`, `window_end`, and any
reconciliation variance notes (e.g. ADP file vs Mercury ADP debits).

## 5. Reconciliation rules (the reconcile module)

### Data pull
- **Mercury** (`Mercury:listTransactions`): paginate fully from `start=2026-01-01`
  to today, `order=desc`, using `page.nextPage` as `start_after`. Three accounts:
  operating checking `a803d718-...`, SoCal/credit-linked `c8016c12-...`, savings/
  estimated-taxes `47545954-...`. Large results spill to disk and are read with
  python/grep, not rendered inline. Dedup by `id`. Keep only `status == "sent"`.
- **Ramp** (`Ramp:ramp_get_user_transactions`):
  `transactions_to_retrieve="all_transactions_across_entire_business"`, `state="all"`,
  `from_date=2026-01-01`, `to_date=today`, `page_size=100`, paginate on
  `next_page_cursor` until null (~335 records). Amounts are strings like `"$12.44"`
  or `"-$18.00"` (negative = refund/credit). Ramp is 100% operating expense, no
  income. Also call `Ramp:ramp_get_ramp_business_account_balance` for live balance.
- **Square**: settled revenue already lands in Mercury as deposits with
  `bankDescription` starting `"Square Inc; SQ######"` (counterparty "Square Inc"),
  net of fees. These Mercury deposits are the Square revenue source of truth. No
  separate gross Square pull required (optional cross-check only).
- **ADP**: read from `PayrollSummary.xlsx` (already in project root). Window Jan 23 to
  Jun 15, 2026. File totals: gross paid $39,330.80, employee tax withheld $5,760.16
  (sits inside gross), employer liability $4,094.80, total cash cost $43,425.60.

### Revenue (money actually received, not invoices)
Include:
- Square payouts (the `Square Inc; SQ######` Mercury deposits), net of fees.
- Real inbound customer revenue via ACH/check. Use Mercury
  `categoryData.name == "Revenue"` as a strong signal, sanity-checked per item.
  Examples seen: ACCESS XP LLC, PRA Disb, Foodbeast Inc, Datafold Inc., AI on the
  Lot LLC, Gearheart Industry credits, Boot Barn revenue-flagged, Cheapflightsfares
  credit-card credits flagged Revenue, Upwork inflows flagged Revenue.

### Exclusions (NOT revenue and NOT expense; stored with bucket=Excluded)
Anything that is an internal/external transfer or platform plumbing:
- `kind` in (`internalTransfer`, `externalTransfer`)
- RAMP; ACH WITHDR / RAMP WALLET DEPOSIT / RAMP; DEPOSIT
- IO PAYMENT / IO AUTOPAY (Mercury credit autopay)
- Percentage-based rule auto-transfer (estimated-taxes sweep)
- Mercury IO Cashback
- Savings-interest lines

Excluded rows are stored (not dropped) so the audit trail is complete, but they are
filtered out of every total.

### Expense and pay rules
- **ADP payroll**: true cash leaving the bank per run = gross + employer liability.
  In Mercury these appear as ADP WAGE PAY, ADP Tax, ADP PAY-BY-PAY, ADP PAYROLL FEES.
  Reconcile the ADP file against these Mercury debits to avoid double-counting; note
  any variance in `meta`. Show employee + employer taxes explicitly from the file.
- **Venmo / CashApp / Apple Cash outflows = pay.** Every `VENMO; PAYMENT` (and any
  CashApp / Apple Cash) outflow is treated as pay, rolled into the pay/expense bucket,
  itemized per line, no tax treatment (off-payroll net cash out).
- **Harrison pay**: roll ALL Harrison pay into the payroll total, with a clear note
  splitting (a) ADP W-2 wages ($1,000/semimonthly plus one $3,000 check in April)
  from (b) direct transfers. Hunt direct transfers in Mercury/Ramp (JPMorgan Chase /
  direct ACH to Harrison Goldfarb that are not ADP and not reimbursements); flag them
  `Owner Pay — Direct Transfer (Harrison)`.
- **Jordan Millhausen car** (owner/car, separate from operating expenses):
  - ~$674/month to Capital One Auto Finance (`CAPITAL ONE AUTO; DIRECTPAY; Jordan
    Millhausen`). Use actual dates/amounts from Mercury; confirm earliest actual date
    (first hit seen mid-May), do not assume. Flag `Owner Car — Capital One (Jordan)`.
  - $2,000/month from May, to Bank of America ending 4201 (`Transfer ... Bank of
    America - Checking ••4201`). Multiple BofA 4201 transfers of varying amounts
    exist; identify which are the $2,000 owner-car payments vs other transfers and
    label only those `Owner Draw — Jordan Car ($2,000/mo from May)`.
- **All other** Ramp and Mercury card/COGS/software/marketing spend = normal
  operating expense, categorized via Mercury `categoryData.name` / `glAllocations`
  and Ramp `merchant_category` / `spend_allocation_name`.

## 6. Buckets and flags

**Buckets** (drive the totals): Revenue, Operating Expense, Payroll, Owner Pay,
Owner Draw, Excluded.

**Flags** (special items, eyeballable): Owner Pay ADP, Owner Pay Direct Transfer
(Harrison), Owner Car Capital One (Jordan), Owner Draw BofA Car (Jordan),
Venmo/CashApp Pay.

**Review column**: anything ambiguous gets a note here rather than a silent guess.

**Category vs bucket** (avoid confusion): `category` describes the *nature* of a line
(COGS, Software, Payroll, etc.) and is for breakdowns. `bucket` is the *totals driver*
(Revenue, Operating Expense, Payroll, Owner Pay, Owner Draw, Excluded). The two
taxonomies overlap in naming (e.g. "Payroll" appears in both); the reconcile module
must assign each independently and consistently. Bucket is what every total filters on.

## 7. Deliverable A — Dashboard (Flask app)

`python serve.py` -> `localhost:8000`. Reads live from `coconuts.db`.

### Headline squares (the State of the Union punchline)

The original brief specified four squares (Current Cash, Cash on the Way, Revenue avg,
Expenses avg). As a CFO deliverable these are expanded so the owner does not have to do
mental math. All averages and derived figures recalc live with the month-range selector.

- **Current Cash** = sum of live Mercury balances + live Ramp balance. Always recompute
  from the live balance call / transaction stream. (The $28,288.41 Ramp checking figure
  from the brief is illustrative only; do not bake it in as a constant.)
- **Net (monthly avg)** = Revenue avg minus Expenses avg over the selected window.
  Color-coded green when positive, red when negative. This is the headline number.
- **Runway / Trajectory** = if Net is negative, Current Cash divided by monthly burn,
  shown as "N months of runway." If Net is positive, shown as "cash growing $X per
  month." Recalcs with the window.
- **Revenue average** = adjustable, default = monthly average over complete months only
  (Jan–May), partial June excluded.
- **Expenses average** = adjustable, same default window.
- **YTD Net** = cumulative revenue minus cumulative expenses, Jan 1 to today (includes
  partial June; this is a running total, not an average, so partial months are fine).
- **Cash on the Way** = hardcoded "TBD" placeholder. The owner confirmed this cannot be
  reliably derived and is to stay TBD.

- **Month-range selector** (start/end) drives every average and derived figure live
  (Net, Runway, Revenue avg, Expenses avg).

### Trend chart

Revenue, Expenses, and Net by month, January to date. This shows whether the gap is
widening or closing, not just revenue in isolation. June rendered as a visually
distinct partial/stub month, excluded from the average math (still shown on the chart).

### Owner compensation panel

A dedicated panel totaling what each owner took, since this is a two-owner S-corp:
- **Jordan**: Owner Car (Capital One ~$674/mo) + Owner Draw (BofA 4201 $2,000/mo from
  May), each line and the total.
- **Harrison**: ADP W-2 wages + direct transfers, split clearly, with the total.

### Category breakdown

Operating expense by category (COGS, Software, Marketing, Travel, etc.) so the owner
sees where the money goes.

### Auto-written takeaways

A short, plain-English briefing block (no dashes) auto-generated from the reconciled
numbers, e.g.: "Revenue averaged $X per month January through May. Expenses averaged
$Y. The business nets $Z per month. Owners drew $D year to date. At $C cash, that is N
months of runway." Regenerates with the data.

### Transactions table

Filterable and searchable table of every line, with bucket, flag, and review columns.

## 8. Deliverable B — Excel workbook (.xlsx)

Generated from the same DB. Audit artifact / accountant hand-off.

- **`Transactions` tab**: every income and pay/expense line, deduped. Columns: date,
  source (Square/Mercury/Ramp/ADP), counterparty, category, amount, flag, review.
- **`Monthly Summary` tab**: revenue, expenses, payroll, owner pay/draws by month
  (Jan–Jun), plus a **Net row** (revenue minus expenses) per month. Adjustable-average
  formulas over a user-controlled range (changing the window recalcs). A small **State
  of the Union block** at the top with formula-driven YTD totals: YTD revenue, YTD
  expenses, YTD net, total payroll, total owner pay, total owner draws, and the
  monthly Net average over the selected window. All totals and averages are formulas
  (`SUMIFS`/`AVERAGEIFS`), no hardcoded values, zero formula errors. Professional font.
- An **Owner Comp** callout block: Jordan (Capital One car + BofA $2k draws) and
  Harrison (ADP W-2 vs direct transfers), each split and totaled with formulas.
- Clear notes/callouts distinguishing ADP W-2 vs Harrison direct transfers, and the
  Jordan car items.
- **No in-Excel dashboard tab.** The four-squares/chart view lives only in the web
  dashboard to avoid duplication. (Refinement agreed with owner.)

## 9. Reconciliation discipline checklist

- Dedup Mercury by transaction id (desc pulls overlap around mid-May).
- Exclude every internal/external transfer, Ramp wallet movement, IO credit autopay,
  estimated-tax sweep, and cashback from both revenue and expenses.
- Cross-check ADP file totals against the sum of ADP debits in Mercury; record any
  variance in `meta`.
- Optional: verify Square payout sum against Square's own settled-payment data as a
  cross-check; otherwise rely on Mercury Square deposits (net).
- Surface anything ambiguous in the `review` column rather than guessing.

## 10. Build order

1. Pull + reconcile module writing to `coconuts.db`. Reconcile and validate first.
2. Excel workbook generator reading from the DB.
3. Flask dashboard reading from the DB.

## 11. Out of scope (YAGNI)

- No self-refreshing-from-banks app (not possible outside the MCP session).
- No static double-click HTML snapshot in v1 (can add later if the server start is a
  nuisance).
- No gross Square reconciliation unless used as an optional cross-check.
- No in-Excel dashboard tab (the four-squares/chart view lives only in the web app).
- No attempt to derive "Cash on the Way" from Mercury open invoices or any AR source.
  Owner decided it stays a hardcoded TBD.
