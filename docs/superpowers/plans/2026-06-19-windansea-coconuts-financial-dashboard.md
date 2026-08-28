# Windansea Coconuts Financial State of the Union — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile Windansea Coconuts money movement from Jan 1, 2026 to today into a durable SQLite store, then surface it as a formula-driven Excel workbook and a reusable interactive Flask dashboard that reads as a CFO State of the Union.

**Architecture:** A two-stage pipeline. Stage one: the agent pulls Mercury, Ramp, and Mercury-balance data via MCP tools and writes raw JSON to `data/raw/` (a plain script cannot call MCP). Stage two: a pure-Python pipeline reads that raw JSON plus the ADP `PayrollSummary.xlsx`, classifies every line into buckets/flags/categories, upserts into `data/coconuts.db` (dedup by source id), and emits the Excel workbook and the dashboard. Both consumers read only from the reconciled DB so they can never disagree.

**Tech Stack:** Python 3, `sqlite3` (stdlib), `openpyxl` (Excel), `Flask` (dashboard), Chart.js via CDN (chart), `pytest` (tests). MCP tools `Mercury:listTransactions`, `Mercury:getCurrentDate`, `Ramp:ramp_get_user_transactions`, `Ramp:ramp_get_ramp_business_account_balance`, plus a Mercury balance source.

**Formatting rule:** No dashes used as pauses anywhere in code, labels, comments, or generated output. Commas, periods, or restructured sentences only.

**Spec:** `docs/superpowers/specs/2026-06-19-windansea-coconuts-financial-dashboard-design.md`

---

## File Structure

| Path | Responsibility |
|---|---|
| `requirements.txt` | Python deps (flask, openpyxl, pytest) |
| `data/raw/*.json` | Raw MCP pulls (Mercury per account, Ramp, balances) |
| `data/coconuts.db` | SQLite reconciled store |
| `src/constants.py` | Shared bucket and flag string literals (load-bearing for SUMIFS and owner-comp; one definition prevents silent zero-total mismatches) |
| `src/store.py` | SQLite schema + upsert/read helpers |
| `src/classify.py` | Pure classification rules: bucket, flag, category, review |
| `src/reconcile.py` | Orchestrator: load raw + ADP, dedup, classify, write DB, ADP cross-check |
| `src/adp.py` | Parse `PayrollSummary.xlsx` into normalized ADP rows + totals |
| `src/excel_report.py` | Generate the formula-driven `.xlsx` from the DB |
| `src/aggregate.py` | Shared monthly/YTD/owner-comp aggregation from the DB (used by Excel + dashboard) |
| `src/dashboard/serve.py` | Flask app: page + JSON API reading the DB |
| `src/dashboard/templates/index.html` | Dashboard markup |
| `src/dashboard/static/app.js` | Squares, range selector, Chart.js trend, tables |
| `tests/test_store.py` | Store schema + upsert/dedup |
| `tests/test_classify.py` | Every classification rule |
| `tests/test_aggregate.py` | Monthly/YTD/net/owner-comp math |
| `tests/test_reconcile.py` | End-to-end reconcile over fixtures, ADP cross-check |
| `tests/fixtures/*.json` | Small representative Mercury/Ramp records |

Classification is split from reconciliation deliberately: `classify.py` holds pure functions (one record in, a verdict out) that are trivially unit-testable, and `reconcile.py` handles IO and orchestration. `aggregate.py` is shared so the Excel and the dashboard compute identical numbers.

---

## Task 0: Project scaffold

**Files:**
- Create: `requirements.txt`, `src/__init__.py`, `tests/__init__.py`, `.gitignore`, `pytest.ini`

- [ ] **Step 1: Create `requirements.txt`**

```
flask>=3.0
openpyxl>=3.1
pytest>=8.0
```

- [ ] **Step 2: Create directory layout and empty package files**

```bash
mkdir -p data/raw src/dashboard/templates src/dashboard/static tests/fixtures
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
data/coconuts.db
```
(Leave `data/raw/` tracked-or-not per preference; the DB is regenerable so it is ignored.)

- [ ] **Step 5: Create venv and install**

Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
Expected: installs flask, openpyxl, pytest with no errors.

- [ ] **Step 6: Commit** (skip if not using git)

---

## Task 1: Pull raw data via MCP (agent-executed, not a script)

This task is executed by the agent calling MCP tools, since a `.py` file cannot reach MCP. Write results verbatim to `data/raw/`. Do not transform here; transformation happens in reconcile.

**Files:**
- Create: `data/raw/mercury_transactions.json`, `data/raw/mercury_balances.json`, `data/raw/ramp_transactions.json`, `data/raw/ramp_balance.json`, `data/raw/pull_meta.json`

- [ ] **Step 1: Get the current date**

Call `Mercury:getCurrentDate`. Use the returned date as `to_date` everywhere. Record it in `data/raw/pull_meta.json` as `{"pulled_through": "<date>"}`. (Per MCP guidance, always anchor date ranges to this.)

- [ ] **Step 2: Pull Mercury transactions, all three accounts, fully paginated**

For each account id (`a803d718-...` operating checking, `c8016c12-...` SoCal/credit-linked, `47545954-...` savings/estimated-taxes):
- Call `Mercury:listTransactions` with `start=2026-01-01`, `order=desc`.
- Follow `page.nextPage` as `start_after` until exhausted.
- If any response says "Result too long, truncated", immediately re-call with a smaller limit (halve it) before paginating. Never use truncated data.

Collect every transaction, tag each with its source `account` id, and write the combined array to `data/raw/mercury_transactions.json`. Do NOT dedup or filter here (reconcile does that); preserve raw records including `id`, `status`, `kind`, `bankDescription`, `counterpartyName`, `amount`, `postedAt`/`createdAt`, `categoryData`, `glAllocations`.

- [ ] **Step 3: Pull Mercury balances**

Capture each account's current balance (via `Mercury:getAccount`/`Mercury:getAccounts` or the latest running balance in the stream). Write `data/raw/mercury_balances.json` as `[{"account": "<id>", "name": "<friendly>", "balance": <number>, "as_of": "<date>"}]`.

- [ ] **Step 4: Pull Ramp transactions, fully paginated**

Call `Ramp:ramp_get_user_transactions` with `transactions_to_retrieve="all_transactions_across_entire_business"`, `state="all"`, `from_date=2026-01-01`, `to_date=<current date>`, `page_size=100`. Follow `next_page_cursor` until null (~335 records). Write the combined array to `data/raw/ramp_transactions.json`, preserving `id`, `amount` (string like `"$12.44"`/`"-$18.00"`), `merchant_name`, `merchant_category`, `spend_allocation_name`, and the transaction date.

- [ ] **Step 5: Pull Ramp balance**

Call `Ramp:ramp_get_ramp_business_account_balance`. Write `data/raw/ramp_balance.json` as `{"balance": <number>, "as_of": "<date>"}`.

- [ ] **Step 6: Sanity-check counts**

Confirm Ramp count is in the expected ~335 range and Mercury returned non-trivial counts for all three accounts. Note actual counts in `pull_meta.json`. If a pull looks short, re-paginate before proceeding.

- [ ] **Step 7: Commit the raw pulls** (optional)

---

## Task 2: SQLite store (`src/store.py`)

**Files:**
- Create: `src/store.py`, `tests/test_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_store.py
import sqlite3
from src import store

def test_init_creates_tables():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"transactions", "balances", "meta"} <= names

def test_upsert_transaction_dedups_by_id():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    row = {"id": "t1", "source": "Mercury", "account": "a", "date": "2026-01-05",
           "counterparty": "Square Inc", "description": "Square Inc; SQ123",
           "category": "Revenue", "amount": 100.0, "bucket": "Revenue",
           "flag": None, "review": None, "raw_json": "{}"}
    store.upsert_transaction(conn, row)
    store.upsert_transaction(conn, {**row, "amount": 100.0})  # same id again
    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 1

def test_set_and_get_meta():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    store.set_meta(conn, "last_refresh", "2026-06-19")
    assert store.get_meta(conn, "last_refresh") == "2026-06-19"
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/pytest tests/test_store.py -v`
Expected: FAIL (module/functions not defined).

- [ ] **Step 3: Implement `src/store.py`**

```python
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    source TEXT, account TEXT, date TEXT,
    counterparty TEXT, description TEXT, category TEXT,
    amount REAL, bucket TEXT, flag TEXT, review TEXT, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS balances (
    account TEXT PRIMARY KEY, name TEXT, balance REAL, as_of TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

TXN_COLS = ["id","source","account","date","counterparty","description",
            "category","amount","bucket","flag","review","raw_json"]

def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()

def upsert_transaction(conn, row):
    placeholders = ",".join("?" for _ in TXN_COLS)
    updates = ",".join(f"{c}=excluded.{c}" for c in TXN_COLS if c != "id")
    conn.execute(
        f"INSERT INTO transactions ({','.join(TXN_COLS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}",
        [row.get(c) for c in TXN_COLS])
    conn.commit()

def upsert_balance(conn, account, name, balance, as_of):
    conn.execute(
        "INSERT INTO balances (account,name,balance,as_of) VALUES (?,?,?,?) "
        "ON CONFLICT(account) DO UPDATE SET name=excluded.name, "
        "balance=excluded.balance, as_of=excluded.as_of",
        [account, name, balance, as_of])
    conn.commit()

def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta (key,value) VALUES (?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", [key, value])
    conn.commit()

def get_meta(conn, key):
    r = conn.execute("SELECT value FROM meta WHERE key=?", [key]).fetchone()
    return r[0] if r else None
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/pytest tests/test_store.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

---

## Task 3: Classification rules (`src/classify.py`) — the heart

Pure functions. Each takes one raw record and returns `(bucket, flag, category, review)`. Buckets: `Revenue`, `Operating Expense`, `Payroll`, `Owner Pay`, `Owner Draw`, `Excluded`. This is the highest-risk logic, so it gets the most tests.

**Files:**
- Create: `src/constants.py`, `src/classify.py`, `tests/test_classify.py`

> **Before Step 1:** Create `src/constants.py` defining every bucket and flag as a
> named constant (e.g. `FLAG_OWNER_CAR = "Owner Car Capital One (Jordan)"`,
> `FLAG_OWNER_DRAW = "Owner Draw BofA Car (Jordan)"`,
> `FLAG_HARRISON_DIRECT = "Owner Pay Direct Transfer (Harrison)"`,
> `FLAG_HARRISON_ADP = "Owner Pay ADP"`, `FLAG_VENMO = "Venmo/CashApp Pay"`).
> Import these in `classify.py`, `reconcile.py`, `aggregate.py`, and `excel_report.py`.
> These strings are load-bearing: `owner_comp` and the Excel `SUMIFS` match on them
> exactly, so a single typo would silently zero a total. One definition, imported
> everywhere.

- [ ] **Step 1: Write failing tests (one per rule)**

```python
# tests/test_classify.py
from src import classify as c

# --- Mercury revenue ---
def test_square_deposit_is_revenue():
    txn = {"bankDescription": "Square Inc; SQ12345", "counterpartyName": "Square Inc",
           "amount": 240.50, "kind": "externalCheck", "categoryData": {"name": "Revenue"}}
    b, flag, cat, _ = c.classify_mercury(txn)
    assert b == "Revenue" and cat == "Revenue"

def test_mercury_revenue_category_inbound_is_revenue():
    txn = {"bankDescription": "ACCESS XP LLC (Windansea Coconuts)",
           "counterpartyName": "ACCESS XP LLC", "amount": 500.0,
           "kind": "externalAch", "categoryData": {"name": "Revenue"}}
    assert c.classify_mercury(txn)[0] == "Revenue"

# --- Exclusions ---
def test_internal_transfer_excluded():
    txn = {"bankDescription": "Transfer to savings", "kind": "internalTransfer",
           "amount": -1000.0, "categoryData": {}}
    assert c.classify_mercury(txn)[0] == "Excluded"

def test_ramp_wallet_deposit_excluded():
    txn = {"bankDescription": "RAMP WALLET DEPOSIT; RAMP", "kind": "externalAch",
           "amount": -5000.0, "categoryData": {}}
    assert c.classify_mercury(txn)[0] == "Excluded"

def test_io_autopay_excluded():
    txn = {"bankDescription": "IO PAYMENT", "kind": "externalAch",
           "amount": -2300.0, "categoryData": {}}
    assert c.classify_mercury(txn)[0] == "Excluded"

def test_tax_sweep_excluded():
    txn = {"bankDescription": "Percentage-based rule auto-transfer",
           "kind": "internalTransfer", "amount": -800.0, "categoryData": {}}
    assert c.classify_mercury(txn)[0] == "Excluded"

def test_cashback_and_interest_excluded():
    assert c.classify_mercury({"bankDescription": "Mercury IO Cashback",
        "kind": "other", "amount": 12.0, "categoryData": {}})[0] == "Excluded"
    assert c.classify_mercury({"bankDescription": "Interest payment",
        "kind": "other", "amount": 3.0, "categoryData": {"name": "Interest"}})[0] == "Excluded"

# --- Pay rules ---
def test_venmo_outflow_is_pay():
    txn = {"bankDescription": "VENMO; PAYMENT", "kind": "externalAch",
           "amount": -300.0, "counterpartyName": "Venmo", "categoryData": {}}
    b, flag, _, _ = c.classify_mercury(txn)
    assert b == "Payroll" and flag == "Venmo/CashApp Pay"

def test_capital_one_car_is_owner_car():
    txn = {"bankDescription": "CAPITAL ONE AUTO; DIRECTPAY; Jordan Millhausen",
           "kind": "externalAch", "amount": -674.0, "categoryData": {}}
    b, flag, _, _ = c.classify_mercury(txn)
    assert b == "Owner Pay" and flag == "Owner Car Capital One (Jordan)"

def test_bofa_4201_2000_is_owner_draw():
    txn = {"bankDescription": "Transfer to Bank of America - Checking ••4201",
           "kind": "externalTransfer", "amount": -2000.0, "date": "2026-05-15",
           "categoryData": {}}
    b, flag, _, review = c.classify_mercury(txn)
    assert b == "Owner Draw" and flag == "Owner Draw BofA Car (Jordan)"

def test_bofa_4201_other_amount_flagged_for_review():
    # A 4201 transfer that is NOT the $2,000 car draw must not be silently bucketed.
    txn = {"bankDescription": "Transfer to Bank of America - Checking ••4201",
           "kind": "externalTransfer", "amount": -3500.0, "date": "2026-04-02",
           "categoryData": {}}
    b, flag, _, review = c.classify_mercury(txn)
    assert review is not None  # surfaced, not guessed

def test_harrison_direct_transfer_is_owner_pay_direct():
    txn = {"bankDescription": "Send Money transaction to Harrison Goldfarb",
           "counterpartyName": "Harrison Goldfarb", "kind": "externalAch",
           "amount": -1500.0, "categoryData": {}}
    b, flag, _, _ = c.classify_mercury(txn)
    assert b == "Owner Pay" and flag == "Owner Pay Direct Transfer (Harrison)"

def test_adp_debit_is_payroll():
    txn = {"bankDescription": "ADP WAGE PAY", "kind": "externalAch",
           "amount": -3200.0, "categoryData": {}}
    assert c.classify_mercury(txn)[0] == "Payroll"

# --- Generic operating expense ---
def test_generic_card_spend_is_operating_expense():
    txn = {"bankDescription": "COSTCO WHSE", "kind": "debitCardTransaction",
           "amount": -212.0, "categoryData": {"name": "Cost of Goods Sold"}}
    b, flag, cat, _ = c.classify_mercury(txn)
    assert b == "Operating Expense" and cat == "Cost of Goods Sold"

# --- Ramp ---
def test_ramp_amount_parsing_and_expense():
    txn = {"amount": "$12.44", "merchant_name": "Canva",
           "merchant_category": "Software", "spend_allocation_name": "Software"}
    row = c.classify_ramp(txn)
    assert row["amount"] == -12.44 and row["bucket"] == "Operating Expense"

def test_ramp_refund_is_positive_credit_still_operating():
    txn = {"amount": "-$18.00", "merchant_name": "Amazon",
           "merchant_category": "Inventory", "spend_allocation_name": "Inventory"}
    row = c.classify_ramp(txn)
    assert row["amount"] == 18.00  # negative string = refund/credit = money back
    assert row["bucket"] == "Operating Expense"
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/pytest tests/test_classify.py -v`
Expected: FAIL (functions not defined).

- [ ] **Step 3: Implement `src/classify.py`**

Implement matching the tests. Key rules, evaluated in this priority order for Mercury (first match wins):

1. **Exclusions** (return `Excluded`): `kind in {"internalTransfer","externalTransfer"}` UNLESS it matches the BofA 4201 $2,000 owner-draw rule below; description contains any of `RAMP WALLET DEPOSIT`, `RAMP; DEPOSIT`, `ACH WITHDR ... RAMP`, `IO PAYMENT`, `IO AUTOPAY`, `Percentage-based rule auto-transfer`, `Mercury IO Cashback`; or category/description indicates savings interest. (Order matters: check the BofA-4201 car-draw and Capital-One rules before the generic transfer exclusion.)
2. **Owner Car (Capital One)**: description contains `CAPITAL ONE AUTO` and `Jordan Millhausen` -> `("Owner Pay", "Owner Car Capital One (Jordan)", "Owner Car", None)`.
3. **Owner Draw (BofA 4201 car)**: description contains `Bank of America` and `4201`. If `abs(amount)` is within a tolerance of 2000 (say 1900 to 2100) and date is May or later -> `("Owner Draw", "Owner Draw BofA Car (Jordan)", "Owner Draw", None)`. Otherwise -> `("Excluded", None, "Transfer", "BofA 4201 transfer not matching $2,000 car draw, confirm classification")` so it is surfaced for review, never silently counted as a draw.
4. **Harrison direct transfer**: counterparty/description contains `Harrison Goldfarb` and it is an outflow that is not ADP and not a reimbursement -> `("Owner Pay", "Owner Pay Direct Transfer (Harrison)", "Owner Pay", None)`.
5. **Venmo/CashApp/Apple Cash pay**: description matches `VENMO; PAYMENT`, `CASH APP`, or `Apple Cash` and amount < 0 -> `("Payroll", "Venmo/CashApp Pay", "Pay", None)`.
6. **ADP payroll**: description starts with `ADP ` (WAGE PAY, Tax, PAY-BY-PAY, PAYROLL FEES) -> `("Payroll", None, "Payroll", None)`. NOTE: a Mercury ADP debit is an aggregate bank draw with no per-employee name, so the `FLAG_HARRISON_ADP` ("Owner Pay ADP") flag is NOT set here. Harrison W-2 attribution comes from the ADP file in Task 4 ($1,000 semimonthly + the one $3,000 April check) and is surfaced by `reconcile.py` / the Owner Comp block, not by `classify_mercury`.
7. **Revenue**: `categoryData.name == "Revenue"` OR Square deposit (`bankDescription` starts with `Square Inc; SQ` / counterparty `Square Inc`) -> `("Revenue", None, "Revenue", None)`. Add a `review` note for non-Square revenue so each inbound is sanity-checked.
8. **Default**: outflow -> `("Operating Expense", None, categoryData.name or "Uncategorized", None)`; unexpected inflow not matching revenue -> `("Operating Expense" if amount<0 else "Revenue", None, ..., "Unexpected inflow, confirm if revenue")`.

```python
# src/classify.py  (skeleton; fill bodies to satisfy the tests above)
import re

def _desc(txn):
    return (txn.get("bankDescription") or "") + " " + (txn.get("counterpartyName") or "")

def classify_mercury(txn):
    d = _desc(txn).upper()
    amt = float(txn.get("amount") or 0)
    cat = (txn.get("categoryData") or {}).get("name")
    kind = txn.get("kind") or ""
    date = txn.get("date") or txn.get("postedAt") or txn.get("createdAt") or ""
    # ... implement rules 1-8 in priority order, returning (bucket, flag, category, review)
    ...

def parse_amount(s):
    if isinstance(s, (int, float)):
        return float(s)
    neg = s.strip().startswith("-")
    val = float(re.sub(r"[^0-9.]", "", s))
    return val if neg else -val  # Ramp: plain charge = money out (negative)

def classify_ramp(txn):
    amount = parse_amount(txn.get("amount"))
    cat = txn.get("merchant_category") or txn.get("spend_allocation_name") or "Uncategorized"
    return {"bucket": "Operating Expense", "flag": None, "category": cat,
            "review": None, "amount": amount,
            "counterparty": txn.get("merchant_name")}
```

Note the Ramp sign convention in the test: a plain `"$12.44"` charge becomes `-12.44` (money out), and a `"-$18.00"` refund becomes `+18.00` (money back). Keep this consistent with Mercury where negative = outflow.

- [ ] **Step 4: Run, verify all pass**

Run: `.venv/bin/pytest tests/test_classify.py -v`
Expected: PASS (all rule tests).

- [ ] **Step 5: Commit**

---

## Task 4: ADP parser (`src/adp.py`)

**Files:**
- Create: `src/adp.py`, `tests/test_adp.py`
- Read: `PayrollSummary.xlsx` (project root)

- [ ] **Step 1: Inspect the real file first**

Run a quick `openpyxl` read of `PayrollSummary.xlsx` to learn its actual sheet names, header row, and columns. Do not assume; the brief gives totals (gross $39,330.80, employee tax $5,760.16, employer liability $4,094.80, total cash cost $43,425.60) which the parser must reproduce as a checksum.

- [ ] **Step 2: Write failing test**

```python
# tests/test_adp.py
from src import adp

def test_adp_totals_match_known_checksums():
    data = adp.load_adp("PayrollSummary.xlsx")
    t = data["totals"]
    assert round(t["gross"], 2) == 39330.80
    assert round(t["employee_tax"], 2) == 5760.16
    assert round(t["employer_liability"], 2) == 4094.80
    assert round(t["total_cash_cost"], 2) == 43425.60
    # true cash leaving bank = gross + employer liability
    assert round(t["cash_out"], 2) == round(39330.80 + 4094.80, 2)
```

- [ ] **Step 3: Implement `src/adp.py`**

`load_adp(path)` returns `{"rows": [...per run...], "totals": {...}}`. Derive `cash_out = gross + employer_liability`. Itemize per pay-run rows with date, gross, employee_tax, employer_liability so the Excel can show the breakdown. Identify Harrison W-2 lines ($1,000 semimonthly plus the one $3,000 April check) so reconcile can flag them `Owner Pay ADP`.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/pytest tests/test_adp.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

---

## Task 5: Reconcile orchestrator (`src/reconcile.py`)

**Files:**
- Create: `src/reconcile.py`, `tests/test_reconcile.py`, `tests/fixtures/mercury_sample.json`, `tests/fixtures/ramp_sample.json`

- [ ] **Step 1: Create small fixtures** mirroring real shapes: include a Square deposit, an internal transfer, a duplicate Mercury id (to prove dedup), a `status != "sent"` row (to prove it is dropped), a Venmo outflow, a Capital One car payment, a $2,000 BofA 4201 transfer, a Harrison direct transfer, and two Ramp rows (a charge and a refund).

- [ ] **Step 2: Write failing tests**

```python
# tests/test_reconcile.py
import sqlite3
from src import reconcile, store

def build():
    conn = sqlite3.connect(":memory:")
    store.init_db(conn)
    reconcile.run(conn,
                  mercury_path="tests/fixtures/mercury_sample.json",
                  ramp_path="tests/fixtures/ramp_sample.json",
                  adp_path="PayrollSummary.xlsx",
                  mercury_balances=[], ramp_balance={"balance": 28288.41})
    return conn

def test_mercury_deduped_by_id():
    conn = build()
    # the duplicate id appears once
    assert conn.execute("SELECT COUNT(*) FROM transactions WHERE id='dup1'").fetchone()[0] == 1

def test_non_sent_rows_dropped():
    conn = build()
    assert conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE id='pending1'").fetchone()[0] == 0

def test_excluded_rows_stored_but_not_in_totals():
    conn = build()
    excl = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE bucket='Excluded'").fetchone()[0]
    assert excl >= 1  # transfers stored, not dropped

def test_revenue_total_only_counts_revenue_bucket():
    conn = build()
    rev = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE bucket='Revenue'").fetchone()[0]
    assert rev > 0
```

- [ ] **Step 3: Implement `src/reconcile.py`**

`run(conn, mercury_path, ramp_path, adp_path, mercury_balances, ramp_balance)`:
1. Load Mercury JSON. Keep only `status == "sent"`. Dedup by `id` (dict keyed on id).
2. For each, call `classify.classify_mercury`, build the row dict, `store.upsert_transaction`.
3. Load Ramp JSON. For each, `classify.classify_ramp`, synth a stable `id` (`ramp:<source id>`), upsert.
4. Load ADP via `adp.load_adp`. Cross-check only: sum Mercury debits whose description starts `ADP ` and compare to the ADP file `cash_out`. Store the variance in `meta` as `adp_variance`. **Do NOT insert ADP-file rows into `transactions`.** The Mercury ADP debits are the cash event and are already in the table from step 1; the ADP file is used only for (a) the variance check and (b) the employee/employer tax breakdown and Harrison W-2 attribution displayed in Excel. This is the single chosen path; there is no alternative to weigh, this avoids double counting.
5. Upsert balances. Set `meta`: `last_refresh`, `window_start=2026-01-01`, `window_end=<today>`, `adp_variance`.

Guard against double counting: the cash leaving the bank is the Mercury ADP debits; the ADP file provides the tax split for display, it is not added again as separate cash.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/pytest tests/test_reconcile.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

---

## Task 6: Shared aggregation (`src/aggregate.py`)

Single source for monthly buckets, YTD totals, net, runway, and owner comp, used by BOTH Excel and dashboard so they match.

**Files:**
- Create: `src/aggregate.py`, `tests/test_aggregate.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_aggregate.py
import sqlite3
from src import store, aggregate

def seed(conn, rows):
    for r in rows:
        store.upsert_transaction(conn, {"flag": None, "review": None,
            "raw_json": "{}", "category": "", "counterparty": "", "description": "", **r})

def test_monthly_revenue_and_expense_split():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"Mercury","account":"a","date":"2026-01-10","amount":1000.0,"bucket":"Revenue"},
        {"id":"2","source":"Ramp","account":"r","date":"2026-01-12","amount":-400.0,"bucket":"Operating Expense"},
        {"id":"3","source":"Mercury","account":"a","date":"2026-02-10","amount":2000.0,"bucket":"Revenue"},
    ])
    m = aggregate.monthly(conn)
    assert m["2026-01"]["revenue"] == 1000.0
    assert m["2026-01"]["expense"] == 400.0   # absolute outflow
    assert m["2026-01"]["net"] == 600.0

def test_average_excludes_partial_june_by_default():
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    seed(conn, [
        {"id":"1","source":"Mercury","account":"a","date":"2026-01-10","amount":1000.0,"bucket":"Revenue"},
        {"id":"2","source":"Mercury","account":"a","date":"2026-06-05","amount":50.0,"bucket":"Revenue"},
    ])
    avg = aggregate.averages(conn, start="2026-01", end="2026-05")
    assert avg["revenue_avg"] == 1000.0  # June 50 excluded
```

- [ ] **Step 2: Run, verify fail.** `.venv/bin/pytest tests/test_aggregate.py -v`

- [ ] **Step 3: Implement `src/aggregate.py`**

Functions:
- `monthly(conn)` -> `{ "2026-01": {revenue, expense, payroll, owner_pay, owner_draw, net}, ... }`. Revenue = sum of positive amounts in `Revenue` bucket. Expense = absolute sum of `Operating Expense`. Payroll, owner_pay, owner_draw = absolute sums of their buckets. **Net = revenue minus (expense + payroll + owner_pay + owner_draw)**, i.e. true cash net (all cash out). This is the ONE net definition used everywhere: the dashboard "Net (monthly avg)" square, the chart's Net series, the Excel monthly Net row, and YTD Net ALL read this same number, so they cannot diverge. (The spec's looser phrase "revenue minus expenses" resolves to this full cash-out definition.) Confirm the definition with the owner during validation (Task 9); if the owner prefers an operating-only net that excludes owner draws, change it in this one function and everything downstream updates.
- `averages(conn, start, end)` -> revenue_avg, expense_avg, net_avg over the inclusive month range (default Jan to May).
- `ytd(conn)` -> cumulative revenue, expense, net, payroll, owner_pay, owner_draw Jan 1 to latest.
- `runway(conn, current_cash, start, end)` -> if net_avg < 0: months = current_cash / abs(net_avg); else growth = net_avg.
- `owner_comp(conn)` -> Jordan (Capital One total, BofA draw total) and Harrison (ADP W-2 total, direct transfer total), from flags.
- `current_cash(conn)` -> sum of `balances`.

- [ ] **Step 4: Run, verify pass.** Commit.

---

## Task 7: Excel workbook (`src/excel_report.py`)

**Files:**
- Create: `src/excel_report.py`, `tests/test_excel_report.py`

- [ ] **Step 1: Write failing structural test**

```python
# tests/test_excel_report.py
import sqlite3, openpyxl
from src import store, excel_report

def test_workbook_has_tabs_and_formula_cells(tmp_path):
    conn = sqlite3.connect(":memory:"); store.init_db(conn)
    store.upsert_transaction(conn, {"id":"1","source":"Mercury","account":"a",
        "date":"2026-01-10","counterparty":"Square Inc","description":"Square Inc; SQ1",
        "category":"Revenue","amount":1000.0,"bucket":"Revenue","flag":None,
        "review":None,"raw_json":"{}"})
    out = tmp_path / "out.xlsx"
    excel_report.build(conn, str(out))
    wb = openpyxl.load_workbook(out)
    assert {"Transactions", "Monthly Summary"} <= set(wb.sheetnames)
    ms = wb["Monthly Summary"]
    # at least one cell is a formula (starts with =), proving no hardcoded totals
    formulas = [c.value for row in ms.iter_rows() for c in row
                if isinstance(c.value, str) and c.value.startswith("=")]
    assert formulas, "Monthly Summary must use formulas"
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement `src/excel_report.py`**

`build(conn, out_path)`:
- **Transactions tab**: header row (Date, Source, Account, Counterparty, Category, Amount, Bucket, Flag, Review), one row per transaction ordered by date. Use an Excel Table for filterability. Professional font (e.g. Calibri 11), bold header, accounting number format on Amount.
- **Monthly Summary tab**:
  - A month grid Jan to Jun with rows Revenue, Expenses, Payroll, Owner Pay, Owner Draw, Net. Each cell is a `SUMIFS` against the Transactions tab by bucket and month (so totals are live formulas, not hardcoded). Net row = Revenue minus the sum of the cost rows, as a formula.
  - Two input cells `Window Start` and `Window End` (month labels). Revenue avg, Expenses avg, Net avg computed with `AVERAGEIFS`/`AVERAGE` over the selected columns so changing the window recalcs.
  - A **State of the Union block**: YTD Revenue, YTD Expenses, YTD Net, Total Payroll, Total Owner Pay, Total Owner Draws, all `SUMIFS` formulas.
  - An **Owner Comp block**: Jordan (Capital One total, BofA draw total) and Harrison (ADP W-2 total, Direct Transfer total) via `SUMIFS` on the flag column, each split and totaled, with a note line distinguishing W-2 from direct transfers and the two Jordan car items.
- No dashes in any label. Verify zero formula errors by reloading and scanning for `#` error strings is not reliable via openpyxl alone, so keep formulas simple and well-formed; final manual open in Excel/Sheets during Task 9 is the formula-error gate.

- [ ] **Step 4: Run, verify pass.** Commit.

---

## Task 8: Flask dashboard (`src/dashboard/`)

**Files:**
- Create: `src/dashboard/serve.py`, `src/dashboard/templates/index.html`, `src/dashboard/static/app.js`
- Create: `tests/test_dashboard_api.py`

- [ ] **Step 1: Write failing API test**

```python
# tests/test_dashboard_api.py
import sqlite3
from src import store
from src.dashboard import serve

def test_summary_endpoint_returns_squares(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db); store.init_db(conn)
    store.upsert_transaction(conn, {"id":"1","source":"Mercury","account":"a",
        "date":"2026-01-10","counterparty":"Square Inc","description":"SQ",
        "category":"Revenue","amount":1000.0,"bucket":"Revenue","flag":None,
        "review":None,"raw_json":"{}"})
    store.upsert_balance(conn, "a", "Operating", 5000.0, "2026-06-19")
    conn.commit(); conn.close()
    app = serve.create_app(str(db))
    client = app.test_client()
    r = client.get("/api/summary?start=2026-01&end=2026-05")
    j = r.get_json()
    assert "current_cash" in j and "revenue_avg" in j and "net_avg" in j
    assert j["cash_on_the_way"] == "TBD"
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement `serve.py`** with `create_app(db_path)` factory:
- `GET /` renders `index.html`.
- `GET /api/summary?start=&end=` returns JSON: `current_cash`, `cash_on_the_way` (literal "TBD"), `revenue_avg`, `expense_avg`, `net_avg`, `runway` (string like "4.2 months of runway" or "cash growing $X per month"), `ytd` block, `monthly` series (for the chart), `owner_comp`, `categories`, and `takeaways` (list of plain-English sentences, no dashes). All computed via `src.aggregate`.
- `GET /api/transactions?q=&bucket=` returns filtered rows for the table.
- `serve.py` `if __name__ == "__main__":` runs `create_app("data/coconuts.db").run(port=8000)`.

- [ ] **Step 4: Implement `index.html` + `app.js`**:
- Header with entity name and "State of the Union" and the pull date.
- Square row: Current Cash, Net (green/red), Runway, Revenue avg, Expenses avg, YTD Net, Cash on the Way (TBD).
- Month-range selector (two dropdowns) that refetches `/api/summary` and updates squares + takeaways live.
- Chart.js trend: Revenue, Expenses, Net by month, June styled distinct (dashed/again no literal dash characters in text, just a different visual style) and labeled partial.
- Owner Comp panel (Jordan, Harrison split).
- Category breakdown (bar or list).
- Takeaways block.
- Filterable transactions table hitting `/api/transactions`.
- Load Chart.js from CDN. Keep `app.js` plain vanilla JS.

- [ ] **Step 5: Run, verify API test passes.** `.venv/bin/pytest tests/test_dashboard_api.py -v`

- [ ] **Step 6: Commit.**

---

## Task 9: End-to-end run, reconciliation validation, and owner review

**Files:**
- Create: `src/build_all.py` (one entry point: reconcile from `data/raw/` + ADP, write DB, write Excel)

- [ ] **Step 1: Implement `src/build_all.py`** that opens `data/coconuts.db`, runs `reconcile.run` with the real `data/raw/` paths and `PayrollSummary.xlsx`, then `excel_report.build(conn, "windansea_coconuts_financials.xlsx")`.

- [ ] **Step 2: Run the full pipeline**

Run: `.venv/bin/python -m src.build_all`
Expected: `data/coconuts.db` populated, `windansea_coconuts_financials.xlsx` written, console prints row counts, YTD revenue, YTD expenses, YTD net, and the ADP variance.

- [ ] **Step 3: Reconciliation sanity checks (CFO discipline)**
- Confirm Mercury dedup worked (no duplicate ids; the desc pulls overlap mid-May).
- Confirm every internal/external transfer, Ramp wallet move, IO autopay, tax sweep, and cashback is in `bucket='Excluded'`, not in any total.
- Print the ADP variance (Mercury ADP debits vs file `cash_out`); if non-trivial, note it.
- Print all rows where `review IS NOT NULL` and eyeball them (especially BofA 4201 transfers and non-Square inbound revenue).
- Confirm Square deposit sum looks sane against expectation.

- [ ] **Step 4: Start the dashboard and eyeball it**

Run: `.venv/bin/python -m src.dashboard.serve`
Open `localhost:8000`. Verify the seven squares, the range selector recalcs Net/Revenue/Expenses, the trend chart shows all three series with June distinct, owner comp totals look right, and the takeaways read cleanly with no dashes.

- [ ] **Step 5: Open the Excel workbook** in Excel or Google Sheets. Confirm zero formula errors, the window inputs recalc the averages, and the SOTU + Owner Comp blocks are correct.

- [ ] **Step 6: Present the `review` items and the ADP variance to the owner** for the judgment calls (which BofA 4201 transfers are car draws, any ambiguous inbound revenue). Apply decisions, rerun `build_all`.

- [ ] **Step 7: Final commit.**

---

## Done criteria

- `data/coconuts.db` holds every Jan 1 to today line, deduped, classified, with excluded transfers stored but not counted.
- `windansea_coconuts_financials.xlsx` opens with zero formula errors, all totals/averages are formulas, and has the SOTU + Owner Comp blocks.
- The Flask dashboard runs from the DB, the range selector drives Net/Revenue/Expenses/Runway live, the trend chart shows revenue/expenses/net with June as a distinct partial, and the takeaways narrate the numbers.
- All `review` items and the ADP variance have been surfaced to the owner, not silently guessed.
