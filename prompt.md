Windansea Coconuts Financial Health Dashboard — Build Prompt for Claude Code
You are building a financial health dashboard and reconciled spreadsheet for Windansea Coconuts (operated under The Bitter Herb LLC, an S-corp). You have access to three connected data sources via MCP: Square, Mercury (business banking), and Ramp (newer corporate card, adopted over the last ~3 months). You also have an ADP payroll export. The owners are Jordan Millhausen and Harrison Goldfarb.
Critical formatting rule
Never use dashes (em dashes or hyphens as pauses) in any writing or labels. Use commas, periods, or restructured sentences.
Scope and window

Entity: Windansea Coconuts ONLY. All three connectors belong to this single entity.
Date window: January 1, 2026 to today. Pull everything from Jan 1 forward.

Data sources and how to pull them
Mercury (Mercury:listTransactions): Paginate fully from start=2026-01-01 to today using order=desc and the page.nextPage cursor as start_after. Results larger than context will be stored to disk; read them with python/grep, do not try to render inline. There are 3 Mercury accounts (operating checking a803d718-..., a SoCal/credit-linked account c8016c12-..., and a savings/estimated-taxes account 47545954-...). Dedup all transactions by id. Filter to status=="sent" only (ignore failed).
Ramp (Ramp:ramp_get_user_transactions): Use transactions_to_retrieve="all_transactions_across_entire_business", state="all", from_date=2026-01-01, to_date=today, page_size=100, paginating via next_page_cursor until null. There are ~335 records. Amounts come as strings like "$12.44" or "-$18.00" (negative = refund/credit). Ramp is 100% operating expenses (no income). Also call Ramp:ramp_get_ramp_business_account_balance for the live Ramp checking balance.
Square: Square's actual settled revenue already lands inside Mercury as deposits with bankDescription starting "Square Inc; SQ######" (counterparty "Square Inc"). These are net-of-fee payouts, which is exactly what we want (user confirmed: actual payments collected, counted net after Square fees). Use these Mercury deposits as the Square revenue source of truth. You do not need to separately reconcile gross Square data unless you want a cross-check.
Revenue rules (what counts as income)
Include as revenue, money actually received (not invoices):

Square payouts (Square Inc; SQ###### deposits into Mercury), net of fees.
Inbound ACH/checks that are real customer revenue. Examples seen: ACCESS XP LLC (Windansea Coconuts), PRA Disb (Windansea Coconuts), Foodbeast Inc, Datafold, Inc., AI on the Lot LLC, Gearheart Industry credits, Boot Barn revenue-flagged, Cheapflightsfares credit-card credits flagged Revenue, Upwork inflows flagged Revenue. Use Mercury's categoryData.name == "Revenue" as a strong signal, but sanity-check each.
Exclude all transfers between own accounts and between banks: anything kind in (internalTransfer, externalTransfer), RAMP; ACH WITHDR / RAMP WALLET DEPOSIT / RAMP; DEPOSIT, IO PAYMENT / IO AUTOPAY (Mercury credit autopay), Percentage-based rule auto-transfer (estimated-taxes sweep), Mercury IO Cashback, and savings-interest lines. These are NOT revenue.

Expense and pay rules

ADP payroll (from the export): Jan 23 to Jun 15, 2026. Totals in the file: gross paid $39,330.80, employee tax withheld $5,760.16 (this sits inside gross), employer liability $4,094.80, total cash cost $43,425.60. The true cash leaving the bank per payroll run = gross + employer liability. In Mercury these appear as ADP WAGE PAY, ADP Tax, ADP PAY-BY-PAY, ADP PAYROLL FEES. Reconcile the ADP file against these Mercury debits so you do not double-count. Show employee + employer taxes explicitly (the file itemizes them; you do not need Ramp/Mercury to derive tax breakdown).
Venmo/CashApp outflows = pay, automatically. Every VENMO; PAYMENT (and any CashApp/Apple Cash) outflow is treated as pay and rolled into the pay/expense bucket. Itemize each one on the spreadsheet so they can be eyeballed, but no tax treatment applies (off-payroll, net cash out).
Harrison pay: roll ALL Harrison pay into the payroll total, but add a clear note splitting (a) ADP W-2 wages ($1,000/semimonthly plus one $3,000 check in April) versus (b) direct transfers to Harrison. Hunt the direct transfers down in Mercury/Ramp (look for JPMorgan Chase / direct ACH to Harrison Goldfarb that are not ADP and not reimbursements) and show them as their own line items flagged "Owner Pay — Direct Transfer (Harrison)."
Jordan Millhausen car (label clearly as owner/car, separate from operating expenses):

~$674/month to Capital One Auto Finance (CAPITAL ONE AUTO; DIRECTPAY; Jordan Millhausen). Use actual transaction dates/amounts found in Mercury (first hit was mid-May; confirm earliest actual date, do not assume).
$2,000/month starting May, direct to Bank of America ending 4201 (Transfer ... Bank of America - Checking ••4201). Match real transactions. Note: there are multiple BofA 4201 transfers of varying amounts; identify which are the $2,000 owner-car payments versus other transfers and label accordingly. Flag clearly as "Owner Draw — Jordan Car ($2,000/mo from May)."


All other Ramp card spend and Mercury card/COGS/software/marketing/etc. are normal operating expenses. Categorize them (COGS, Payroll, Owner Pay, Travel, Software, Marketing, Inventory, Meals, Fuel, Rideshare, Professional Services, etc.) using Mercury categoryData.name / glAllocations and Ramp merchant_category / spend_allocation_name.

The four top summary squares

Current Cash = Mercury live balances + Ramp live balance. (Ramp checking was $28,288.41 at last check; recompute Mercury balances from the transaction stream or a balance call.)
Cash on the Way = hardcode "TBD" placeholder (cannot be reliably derived).
Revenue average = adjustable. Default to monthly average across complete months only, Jan through May (exclude partial June from the average math).
Expenses average = adjustable, same default window (Jan–May complete months).

Make the averages adjustable. In the spreadsheet, lay out each month's revenue and expenses in a row and compute the average with a formula over a range the user controls (so changing the window recalcs). In the HTML dashboard, add a month-range selector (start/end dropdowns) that drives the two average squares live. June is shown on the graph but excluded from the default average.
The graph
Revenue over time, January to date, by month (line or bar). Show June as a partial/stub month, visually distinct, and excluded from the average calculation.
Deliverables

A reconciled spreadsheet (.xlsx) with:

A transactions tab: every income and pay/expense line, deduped, with columns for date, source (Square/Mercury/Ramp/ADP), counterparty, category, amount, and a flag column for special items (Owner Pay ADP, Owner Pay Direct Transfer, Owner Car Capital One, Owner Draw BofA Car, Venmo/CashApp Pay).
A monthly summary tab: revenue, expenses, payroll, owner pay/draws by month (Jan–Jun), with the adjustable-average formulas.
Clear notes/callouts distinguishing ADP W-2 vs Harrison direct transfers, and the Jordan car items.
Use formulas (not hardcoded values) for all totals and averages. Zero formula errors. Professional font.


An HTML dashboard with the four top squares, the month-range average selector, and the revenue-over-time graph.

Reconciliation discipline (you are the CFO, be thorough)

Dedup Mercury by transaction id (the desc pulls overlap around mid-May).
Exclude every internal/external transfer, Ramp wallet movement, IO credit autopay, estimated-tax sweep, and cashback from BOTH revenue and expenses.
Cross-check the ADP file totals against the sum of ADP debits in Mercury; note any variance.
Verify Square payout sum against Square's own settled-payment data if you choose to pull it as a check; otherwise rely on the Mercury Square deposits (net).
Surface anything ambiguous in a "Review" column rather than silently guessing.

Build the spreadsheet first and reconcile, then generate the HTML dashboard from the same reconciled monthly numbers.