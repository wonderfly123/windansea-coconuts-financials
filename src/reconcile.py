"""Reconcile orchestrator for the Windansea Coconuts financial dashboard.

Loads the raw Mercury / Ramp / ADP pulls, runs each row through the pure
classification rules in :mod:`src.classify`, and writes the reconciled
transactions, balances, and meta into the SQLite store.

Design notes / invariants:
  * Only Mercury rows with status == "sent" are kept (pending/failed are dropped
    entirely -- they never moved cash). Kept rows are deduped by id, last wins.
  * Ramp ids are namespaced with a "ramp:" prefix so a Ramp transaction_uuid can
    never collide with a Mercury id in the shared primary-key column.
  * ADP file rows are NEVER inserted as transactions -- the Mercury "ADP ..."
    debits already represent the cash leaving the bank. ADP is used only to
    derive Harrison's W-2 gross and to cross-check the ADP cash variance.
"""

import datetime
import json
import os
from typing import Any, Dict, List, Optional

from src import store, adp
from src import constants as k
from src.classify import classify_mercury, classify_ramp


def _date10(value: Optional[str]) -> str:
    """First 10 chars of an ISO datetime -> 'YYYY-MM-DD', or '' if absent."""
    return (value or "")[:10]


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _is_jun1_split(row: Dict[str, Any]) -> bool:
    """The specific $3,400 BofA 4201 transfer on 2026-06-01 that the owner
    confirmed is $2,000 Jordan car draw + $1,400 loan to Harrison."""
    date = _date10(row.get("postedAt") or row.get("failedAt") or "")
    cp = row.get("counterpartyName") or ""
    return (
        "4201" in cp
        and date == "2026-06-01"
        and round(float(row.get("amount") or 0), 2) == -3400.00
    )


def _split_jun1(rid: str, row: Dict[str, Any], date: str) -> List[Dict[str, Any]]:
    """Two attributed rows for the split $3,400 transfer (no original kept)."""
    base = {
        "source": "Mercury",
        "account": row.get("account") or row.get("accountId"),
        "date": date,
        "counterparty": row.get("counterpartyName"),
        "description": row.get("bankDescription"),
        "raw_json": json.dumps(row),
    }
    return [
        {
            **base,
            "id": rid + ":car",
            "category": "Owner Draw",
            "amount": -2000.00,
            "bucket": k.BUCKET_OWNER_DRAW,
            "flag": k.FLAG_OWNER_DRAW_BOFA,
            "review": "Portion of the $3,400 BofA transfer, Jordan car draw",
        },
        {
            **base,
            "id": rid + ":harrison",
            "category": "Owner Pay",
            "amount": -1400.00,
            "bucket": k.BUCKET_OWNER_PAY,
            "flag": k.FLAG_HARRISON_DIRECT,
            "review": "Portion of the $3,400 BofA transfer, Jordan's personal loan to Harrison",
        },
    ]


def run(conn, mercury_path, ramp_path, adp_path, mercury_balances, ramp_balance,
        pull_date: Optional[str] = None, square_path: Optional[str] = None,
        ramp_wallet_path: Optional[str] = None) -> None:
    """Load raw pulls, classify, and write the reconciled DB.

    Parameters
    ----------
    conn : sqlite3.Connection (already init_db'd)
    mercury_path, ramp_path : paths to the raw JSON array pulls
    adp_path : path to the ADP PayrollSummary.xlsx
    mercury_balances : list of {account, name, balance, as_of}
    ramp_balance : {balance, as_of}
    pull_date : optional override for the window-end / refresh date.
    """
    # ------------------------------------------------------------------ Mercury
    mercury_raw = _load_json(mercury_path)
    kept: Dict[str, Dict[str, Any]] = {}
    for row in mercury_raw:
        if row.get("status") != "sent":
            continue
        kept[row.get("id")] = row  # last one wins on duplicate id

    for rid, row in kept.items():
        date = _date10(row.get("postedAt") or row.get("failedAt") or "")

        # Manual split (owner-confirmed): the $3,400 BofA 4201 transfer on
        # 2026-06-01 was $2,000 of Jordan's car draw plus a $1,400 personal loan
        # Jordan made to Harrison. Store it as two rows so each owner is
        # attributed correctly, and do NOT store the original $3,400 line.
        if _is_jun1_split(row):
            for split in _split_jun1(rid, row, date):
                store.upsert_transaction(conn, split)
            continue

        bucket, flag, category, review = classify_mercury(row)
        store.upsert_transaction(conn, {
            "id": rid,
            "source": "Mercury",
            "account": row.get("account") or row.get("accountId"),
            "date": date,
            "counterparty": row.get("counterpartyName"),
            "description": row.get("bankDescription"),
            "category": category,
            "amount": float(row.get("amount") or 0),
            "bucket": bucket,
            "flag": flag,
            "review": review,
            "raw_json": json.dumps(row),
        })

    # --------------------------------------------------------------------- Ramp
    ramp_raw = _load_json(ramp_path)
    for row in ramp_raw:
        rid = "ramp:" + row["transaction_uuid"]
        c = classify_ramp(row)
        date = _date10(row.get("transaction_time") or "")
        review = (
            "Ramp PENDING, not yet cleared"
            if row.get("state") == "PENDING"
            else c["review"]
        )
        store.upsert_transaction(conn, {
            "id": rid,
            "source": "Ramp",
            "account": "Ramp",
            "date": date,
            "counterparty": c["counterparty"],
            "description": row.get("merchant_name") or row.get("spend_allocation_name"),
            "category": c["category"],
            "amount": c["amount"],
            "bucket": c["bucket"],
            "flag": c["flag"],
            "review": review,
            "raw_json": json.dumps(row),
        })

    # ------------------------------------------------------------------- Square
    # Square payouts are the revenue source of truth: net of fees and bank
    # agnostic, so they capture sales no matter which bank Square deposited to.
    # The matching Mercury "Square Inc" deposits are excluded in classify so this
    # is not double counted.
    if square_path and os.path.exists(square_path):
        for p in _load_json(square_path):
            if p.get("status") not in ("PAID", "SENT"):
                continue
            cents = (p.get("amount_money") or {}).get("amount") or 0
            store.upsert_transaction(conn, {
                "id": "square:" + p["id"],
                "source": "Square",
                "account": (p.get("destination") or {}).get("id") or "Square",
                "date": _date10(p.get("arrival_date")),
                "counterparty": "Square Inc",
                "description": "Square net payout",
                "category": "Revenue",
                "amount": cents / 100.0,
                "bucket": k.BUCKET_REVENUE,
                "flag": None,
                "review": None,
                "raw_json": json.dumps(p),
            })

    # --------------------------------------------------- Ramp checking (wallet)
    # The Ramp CHECKING account (separate from the card) pays vendor bills and
    # receives Square deposits, starting mid May 2026. Square inflows are already
    # counted via the Square source; transfers in from Mercury are internal; the
    # outflows are real expenses the card view never showed.
    if ramp_wallet_path and os.path.exists(ramp_wallet_path):
        merc_sources = ("THE BITTER HERB", "SOCAL", "ESTIMATED TAXES")
        for i, w in enumerate(_load_json(ramp_wallet_path)):
            src = w.get("source_account_name") or ""
            su = src.upper()
            amt = float(w.get("amount") or 0)
            memo = (w.get("memo") or "")
            date = _date10(w.get("date"))
            base = {
                "id": f"rampw:{date}:{i}",
                "source": "Ramp Checking",
                "account": "Ramp Checking",
                "date": date,
                "counterparty": src or None,
                "description": memo or None,
                "raw_json": json.dumps(w),
            }
            if su == "SQUARE INC":
                continue  # already counted from the Square payouts source
            if any(m in su for m in merc_sources):
                store.upsert_transaction(conn, {**base, "amount": amt,
                    "category": "Internal transfer", "bucket": k.BUCKET_EXCLUDED,
                    "flag": None, "review": "Transfer in from your Mercury account, internal"})
            elif src == "Checking Account":
                out = -abs(amt)
                if "BILL" in memo.upper():
                    vendor = memo.split("-")[-1].strip() if "-" in memo else memo
                    store.upsert_transaction(conn, {**base, "amount": out,
                        "counterparty": vendor, "category": "Bill Pay",
                        "bucket": k.BUCKET_OPERATING, "flag": None, "review": None})
                elif abs(amt - 674.51) < 0.01:
                    store.upsert_transaction(conn, {**base, "amount": out,
                        "counterparty": "Capital One Auto", "category": "Owner Car",
                        "bucket": k.BUCKET_OWNER_PAY, "flag": k.FLAG_OWNER_CAR,
                        "review": "Likely the June Capital One car payment (matches the monthly amount), verify"})
                elif abs(amt - 6432.23) < 0.01:
                    # ADP payroll draft funded from Ramp checking. From late May 2026
                    # ADP stopped drafting from Mercury (banking moved to Ramp), so this
                    # run is NOT in the Mercury ADP debits and is NOT a card paydown.
                    # Real payroll expense. (Owner confirmed.)
                    store.upsert_transaction(conn, {**base, "amount": out,
                        "counterparty": "ADP Payroll", "category": "Payroll",
                        "bucket": k.BUCKET_PAYROLL, "flag": None,
                        "review": "ADP payroll draft funded from Ramp checking (June 15 payroll), owner confirmed"})
                elif amt in (1000.0, 3000.0, 1400.0, 10000.0):
                    store.upsert_transaction(conn, {**base, "amount": out,
                        "category": "Transfer", "bucket": k.BUCKET_EXCLUDED, "flag": None,
                        "review": "Ramp round-number transfer, verify if internal or an owner draw"})
                else:
                    # Unlabeled Ramp checking outflows are card-balance paydowns,
                    # which are already counted as expense via the Ramp card spend.
                    # Excluded to avoid double counting. (Owner confirmed.)
                    store.upsert_transaction(conn, {**base, "amount": out,
                        "category": "Ramp card paydown", "bucket": k.BUCKET_EXCLUDED, "flag": None,
                        "review": "Ramp card balance paydown, already counted in Ramp card spend"})
            else:
                store.upsert_transaction(conn, {**base, "amount": amt,
                    "category": "Unclassified", "bucket": k.BUCKET_EXCLUDED, "flag": None,
                    "review": "Ramp transfer with unclear source, verify direction"})

    # ---------------------------------------------------------------------- ADP
    adp_data = adp.load_adp(adp_path)

    harrison_gross = 0.0
    for r in adp_data["rows"]:
        emp = (r.get("employee") or "").lower()
        if "harrison" in emp or "goldfarb" in emp:
            harrison_gross += r["gross"]
    store.set_meta(conn, k.META_HARRISON_W2_GROSS, str(round(harrison_gross, 2)))

    # ADP cash cross-check: the Mercury "ADP ..." sent debits already hold the
    # cash, so compare their absolute sum to ADP's reported cash_out.
    mercury_adp_cash = abs(sum(
        float(row.get("amount") or 0)
        for row in kept.values()
        if (row.get("bankDescription") or "").upper().startswith("ADP")
    ))
    cash_out = adp_data["totals"]["cash_out"]
    variance = round(mercury_adp_cash - cash_out, 2)
    store.set_meta(conn, k.META_ADP_VARIANCE, str(variance))

    # ----------------------------------------------------------------- Balances
    for entry in mercury_balances:
        store.upsert_balance(
            conn,
            entry["account"],
            entry.get("name"),
            entry.get("balance"),
            entry.get("as_of"),
        )
    store.upsert_balance(
        conn,
        "ramp",
        "Ramp Checking",
        ramp_balance["balance"],
        ramp_balance.get("as_of"),
    )

    # --------------------------------------------------------------------- Meta
    window_end = pull_date or ramp_balance.get("as_of") or "2026-06-19"
    refresh = ramp_balance.get("as_of") or datetime.date.today().isoformat()
    store.set_meta(conn, k.META_LAST_REFRESH, refresh)
    store.set_meta(conn, k.META_WINDOW_START, "2026-01-01")
    store.set_meta(conn, k.META_WINDOW_END, window_end)


def run_from_disk(conn, data_dir: str = "data/raw",
                  adp_path: str = "PayrollSummary.xlsx") -> None:
    """Convenience wrapper: read the four raw files from disk and run()."""
    mercury_path = os.path.join(data_dir, "mercury_transactions.json")
    ramp_path = os.path.join(data_dir, "ramp_transactions.json")
    square_path = os.path.join(data_dir, "square_payouts.json")
    ramp_wallet_path = os.path.join(data_dir, "ramp_wallet_transfers.json")
    mercury_balances = _load_json(os.path.join(data_dir, "mercury_balances.json"))
    ramp_balance = _load_json(os.path.join(data_dir, "ramp_balance.json"))

    pull_date = None
    pull_meta_path = os.path.join(data_dir, "pull_meta.json")
    if os.path.exists(pull_meta_path):
        meta = _load_json(pull_meta_path)
        pull_date = meta.get("pulled_through") or meta.get("window_end")

    run(conn, mercury_path, ramp_path, adp_path,
        mercury_balances, ramp_balance, pull_date=pull_date, square_path=square_path,
        ramp_wallet_path=ramp_wallet_path)
