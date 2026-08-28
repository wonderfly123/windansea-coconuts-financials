"""All file reading for the runway dashboard lives here."""

import json
import sqlite3
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "coconuts.db"
ADP_XLSX = ROOT / "PayrollSummary 4_30_26 to 8_28_26.xlsx"

PATHS = {
    "card": RAW / "ramp_card_jun19_aug28.json",
    "wallet": RAW / "ramp_wallet_jun19_aug28.json",
    "balance": RAW / "ramp_balance.json",
    "statement": RAW / "ramp_card_statement.json",
    "invoices": [RAW / "square_invoices.json", RAW / "square_invoices_p2.json"],
}


def _json(path):
    if not Path(path).exists():
        raise FileNotFoundError(f"missing data file: {path}")
    with open(path) as f:
        return json.load(f)


def load_card(path=PATHS["card"]) -> list:
    data = _json(path)
    return data["transactions"] if isinstance(data, dict) else data


def load_wallet(path=PATHS["wallet"]) -> list:
    data = _json(path)
    return data["transfers"] if isinstance(data, dict) else data


def load_balance(path=PATHS["balance"]) -> dict:
    return _json(path)


def load_statement(path=PATHS["statement"]) -> dict:
    return _json(path)


def load_invoices(paths=PATHS["invoices"]) -> list:
    out = []
    for p in paths:
        out += _json(p)["invoices"]
    return out


def load_db_rows(db_path=DB, start="2026-01-01", end="2026-12-31") -> list:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT date, counterparty, description, category, bucket, flag, amount "
        "FROM transactions WHERE date >= ? AND date <= ? ORDER BY date",
        [start, end],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_adp(path=ADP_XLSX) -> list:
    """Rows of {check_date (ISO), name, total_expenses} from the ADP export."""
    if not Path(path).exists():
        raise FileNotFoundError(f"missing ADP export: {path}")
    ws = openpyxl.load_workbook(path, data_only=True).active
    out = []
    header_seen = False
    for r in ws.iter_rows(values_only=True):
        if not header_seen:
            header_seen = r[0] == "Pay Frequency"
            continue
        if not r[2] or not isinstance(r[11], (int, float)):
            continue
        m, d, y = str(r[2]).strip().split("/")
        out.append({"check_date": f"{y}-{m}-{d}", "name": str(r[3]).strip(),
                    "total_expenses": float(r[11])})
    return out
