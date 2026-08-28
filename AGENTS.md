# Windansea Coconuts Financial Dashboard — Project Memory

Project-local context for this repo. Auto-loaded by Codex when working here.

## What this is

Financial "State of the Union" dashboard for **Windansea Coconuts**, a food/events
business operated under **The Bitter Herb LLC** (an S-corp). Owners: **Jordan Millhausen**
and **Harrison Goldfarb**. Covers Jan 1 to Jun 19, 2026.

**Stack:** Python. SQLite `data/coconuts.db` is the single source of truth. Pipeline:
pull raw data via MCP -> `src/reconcile.py` classifies into buckets -> writes DB ->
`src/excel_report.py` (workbook `windansea_coconuts_financials.xlsx`) and
`src/dashboard/serve.py` (Flask). Rules in `src/classify.py`, shared math in
`src/aggregate.py`, constants in `src/constants.py`. Tests: `.venv/bin/pytest`.

**Run dashboard:** `.venv/bin/python -m src.dashboard.serve` -> `localhost:8000`. Static
JS/CSS update on browser refresh; `templates/index.html` changes need a server restart.
Kill stale server: `lsof -ti:8000 | xargs kill -9`.

**Refresh data:** re-pull the MCP sources (below) then `.venv/bin/python -m src.build_all`.
build_all clears only the financial tables and PRESERVES the `questions` table (owner's
typed notes survive). Data is reachable only through MCP in a Codex session, so the app
cannot self-refresh; a human triggers the re-pull.

## Revenue reconciliation gotchas (the hard-won, non-obvious stuff)

**Revenue source of truth is Square payouts pulled DIRECTLY from Square**, not Mercury
deposits. Square changed its deposit bank THREE times in 2026, so Mercury only saw a slice:
- Jan to ~Mar 23: bank `Ebez4ZF…` (old account, ~$26k)
- ~Mar 24 to May 18: `szQX…` = Mercury SoCal checking (~$61k, the only part Mercury saw)
- ~May 21 on (incl. all June): `mkAq…` = the **Ramp checking account** (~$52k)
Pull all Square payouts via `payouts.list` (net of fees, bank agnostic). True YTD revenue
~$218,915 (Square ~$139,580 + company ACH in Mercury ~$79,335), vs only ~$166k if trusting
Mercury. Mercury "Square Inc" deposits are EXCLUDED to avoid double counting.

**Ramp has TWO parts: the card AND the checking account.** Pull the card
(`ramp_get_user_transactions`) AND the checking via `ramp_list_wallet_transfers`. Ramp
checking receives Square deposits and pays vendor bills. Labeled "Bill #…" outflows = real
vendor expense; UNLABELED "Checking Account" outflows = card-balance paydowns already
counted in the Ramp card spend, so EXCLUDED. A $6,432 Jun 13 payment is flagged for manual
verification.

**Mercury accounts:** `a803d718…` = "SoCal ••4813" active main checking; `47545954…` =
"Estimated Taxes" savings ($0); `4f3bf40a…` = "Vegas ••5742" archived ($0). The original
prompt's `c8016c12` account does NOT exist.

**Cash vs net:** Current Cash (~$38,931 = Mercury $10,643 + Ramp $28,288) and Revenue are
trustworthy. NET is unreliable (incomplete expense capture + unknown opening balance), so
net was removed from the dashboard.

## Owner-confirmed classification

**Harrison Goldfarb pay ~$36,486** is LUMPED INTO EXPENSES (he runs the business) AND shown
in Owner Comp: ADP W-2 ~$13,000 (in Payroll) + direct distributions ~$23,486 (flag
"Owner Pay Direct Transfer (Harrison)": Chase card $8,000, Amex $2,047, transfers to his
personal Chase checking ••8371 = $11,500, JPMorgan $539, $1,400 loan from Jordan). Lumpy:
~$15,500 hit in May (paying down personal debt), which is why May expenses spike.

**Jordan Millhausen pay** stays OUT of expenses (Owner Comp only): Capital One auto
~$674.51/mo (car loan) + BofA ••4201 $2,000/mo draws from May.

**$3,400 BofA ••4201 on 2026-06-01** is split: $2,000 Jordan car draw + $1,400 loan to
Harrison.

**Excluded (internal / pass-through):** Bitter Herb / JPMorgan "Ext Trnsfr" inflows (own
money from old Chase), CDTFA / "CA DEPT TAX" (sales tax remittance, pass-through), internal
transfers, IO credit autopay/cashback, estimated-tax sweeps, interest, Ramp wallet funding.

**Counted:** Venmo / Apple Cash outflows = staff pay (Payroll). Intuit/QuickBooks deposits
+ ACCESS XP = customer revenue. "Send Money" = vendor payments (Sun Hing Foods, Coy's,
Terra Catering, Indico, etc.), COGS/operating.

## Dashboard presentation preferences (Jordan)

- **No "net" anywhere** (squares, chart, takeaways). Focus on Cash and Revenue.
- **Six squares:** Current Cash (green), Revenue YTD (green), Revenue avg, Expenses avg,
  Margin (green), Cash on the Way ("TBD", cannot be derived). All have hover/click tooltips.
- **Expenses** = Operating + Payroll + Harrison's pay (NOT Jordan's draws).
- **Margin** = (avg revenue minus avg expenses) / avg revenue, ~36%.
- **Default window: April–June 2026**; end auto-advances to the latest month, partial June
  included; selector adjustable.
- **Takeaways panel removed.** Chart sits next to the Questions/Notes panel.
- **Questions / Notes panel** saves to the SQLite `questions` table; survives refreshes.
- **No dashes as pauses** in any label or generated text (commas/periods/parentheses).
- Surface ambiguous items rather than guessing; he engages deeply and corrects classification.
