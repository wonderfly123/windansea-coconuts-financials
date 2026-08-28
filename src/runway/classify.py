"""Tag raw records into runway sections. Pure functions, no I/O.

Each tagger returns a Rec, a list of Recs (for splits), or None (ignore).
Amounts are positive for outflows and for revenue; refunds on expense
merchants come back negative so they net against the section.
"""

from dataclasses import dataclass

from src.runway import plan as P


@dataclass(frozen=True)
class Rec:
    date: str
    amount: float
    section: str
    sub: str
    label: str
    known: bool = True  # False = fell through to overhead with no rule, listed for review


def _has(text: str, keys) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keys)


def _money(s: str) -> float:
    return float(str(s).replace("$", "").replace(",", ""))


def _outflow_section(name: str):
    """Shared merchant rules for card, bill pay and DB outflows.

    Returns (section, sub) or None when no rule matches.
    """
    if _has(name, P.SALES_TAX_NAMES):
        return P.SALES_TAX, ""
    if _has(name, P.ADP_FEES):
        return P.OVERHEAD, "adp fees"
    if _has(name, P.ADP_DEBITS):
        return P.EXCLUDED, "adp debit"
    if _has(name, P.HARRISON_DIRECT):
        return P.PEOPLE_CORE, "harrison"
    if _has(name, P.JORDAN_DIRECT):
        return P.PEOPLE_CORE, "jordan"
    if _has(name, P.TIM_DIRECT):
        return P.PEOPLE_CORE, "tim"
    if _has(name, P.VENMO_LIKE):
        return P.PEOPLE_NONCORE, P.SUB_VENMO
    if _has(name, P.NONCORE_CONTRACTORS):
        return P.PEOPLE_NONCORE, P.SUB_CONTRACTOR
    if _has(name, P.COGS_MERCHANTS):
        return P.COGS, ""
    return None


# Ramp card ------------------------------------------------------------------
def tag_card(t: dict):
    if t.get("state") == "DECLINED":
        return None
    name = t.get("merchant_name") or ""
    amt = _money(t["amount"])
    date = t["transaction_time"][:10]
    hit = _outflow_section(name)
    if hit:
        return Rec(date, amt, hit[0], hit[1], name)
    cat = t.get("merchant_category") or ""
    return Rec(date, amt, P.OVERHEAD, cat, name, known=cat.lower() not in P.UNKNOWN_CATEGORIES)


# Ramp checking ---------------------------------------------------------------
def tag_wallet(t: dict):
    if t.get("status") != "COMPLETED":
        return None
    date = t["created_at"][:10]
    amt = float(t["signed_amount"])
    ttype = t.get("transfer_type")
    if amt > 0:
        src = t.get("source_account_name") or ""
        if ttype == "PROVIDER_INTEREST_PAYMENT" or _has(src, P.EXCLUDED_INFLOWS):
            return Rec(date, amt, P.EXCLUDED, "inflow", src)
        if _has(src, ["square inc"]):
            return Rec(date, amt, P.REVENUE, "square", "Square payouts")
        label = "Check deposits" if ttype == "CHECK_DEPOSIT" else src
        return Rec(date, amt, P.REVENUE, ttype.lower(), label)
    amt = -amt
    if ttype == "STATEMENT_PAYMENT":
        return Rec(date, amt, P.EXCLUDED, "card paydown", "Ramp card paydown")
    if ttype == "REIMBURSEMENT_PAYMENT":
        who = (t.get("transaction_details") or "").replace("Paid to ", "").split(" (")[0].strip()
        return Rec(date, amt, P.OVERHEAD, "reimbursement", f"Reimbursement: {who or 'unknown'}")
    if ttype == "BILLPAY_PAYMENT":
        memo = t.get("memo") or t.get("transaction_details") or ""
        vendor = memo.split(" - ")[-1].strip() if " - " in memo else memo
        hit = _outflow_section(vendor) or _outflow_section(t.get("transaction_details") or "")
        if hit:
            return Rec(date, amt, hit[0], hit[1], vendor)
        return Rec(date, amt, P.OVERHEAD, "bill pay", vendor, known=False)
    dst = t.get("destination_account_name") or t.get("transaction_details") or ""
    hit = _outflow_section(dst)
    if hit:
        return Rec(date, amt, hit[0], hit[1], dst)
    if _has(dst, P.EXCLUDED_OUTFLOWS) or _has(dst, ["square inc"]):
        return Rec(date, amt, P.EXCLUDED, "transfer", dst)
    return Rec(date, amt, P.OVERHEAD, "withdrawal", dst, known=False)


# SQLite rows (Mercury, Ramp, Square before the cutover) ------------------------
def tag_db_row(r: dict):
    date = r["date"]
    if date < P.WINDOW_START or date >= P.RAW_CUTOVER:
        return None
    name = r.get("counterparty") or r.get("description") or ""
    amt = float(r["amount"])
    bucket = r.get("bucket") or ""
    if amt > 0:
        if bucket == "Revenue" or _has(name, P.REVENUE_NAMES):
            return Rec(date, amt, P.REVENUE, "db", name)
        if bucket in ("Operating Expense",):
            return Rec(date, -amt, P.OVERHEAD, "refund", name)
        return Rec(date, amt, P.EXCLUDED, "inflow", name)
    amt = -amt
    split = P.SPLIT_BOFA.get(date)
    if split and _has(name, ["4201"]) and abs(amt - split["amount"]) < 0.01:
        return [Rec(date, split["jordan"], P.PEOPLE_CORE, "jordan", name),
                Rec(date, split["harrison"], P.PEOPLE_CORE, "harrison", name)]
    hit = _outflow_section(name)
    if hit:
        return Rec(date, amt, hit[0], hit[1], name)
    if bucket == "Excluded" or _has(name, P.EXCLUDED_OUTFLOWS):
        return Rec(date, amt, P.EXCLUDED, "db excluded", name)
    if (r.get("category") or "") == "COGS":
        return Rec(date, amt, P.COGS, "", name)
    if bucket == "Payroll":
        return Rec(date, amt, P.PEOPLE_NONCORE, P.SUB_VENMO, name)
    cat = r.get("category") or ""
    return Rec(date, amt, P.OVERHEAD, cat, name, known=cat.lower() not in P.UNKNOWN_CATEGORIES)


# ADP export --------------------------------------------------------------------
def tag_adp_row(r: dict):
    date = r["check_date"]
    if date < P.WINDOW_START or date > P.WINDOW_END:
        return None
    amt = float(r["total_expenses"])
    key = P.ADP_CORE_NAMES.get(r["name"])
    if key:
        return Rec(date, amt, P.PEOPLE_CORE, key, r["name"])
    return Rec(date, amt, P.PEOPLE_NONCORE, P.SUB_ADP_HOURLY, r["name"])
