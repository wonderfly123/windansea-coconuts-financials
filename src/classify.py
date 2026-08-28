"""Pure transaction classification for the Windansea Coconuts reconciliation.

Each function takes ONE raw record (Mercury or Ramp) and returns how it should
be bucketed. No I/O, no DB, no status filtering here -- the reconcile step keeps
only "sent" Mercury rows and decides what to do with Ramp PENDING state. This
module is purely the rules, so they can be unit-tested against the real data
shapes pulled to disk.

Highest-risk decisions encoded here (grounded against data/raw/*.json):

  * Owner Car  : "CAPITAL ONE AUTO; DIRECTPAY; Jordan Millhausen", -674.51/mo.
                 Must win over the generic transfer exclusion.
  * Owner Draw : BofA "••4201" external transfers. ONLY the ~$2,000 May-2026+
                 transfers are the car draw; every other 4201 amount is an
                 ambiguous transfer that gets EXCLUDED *with a review note* --
                 never silently treated as a draw.
  * Harrison   : direct transfers whose PAYEE is exactly "Harrison Goldfarb" and
                 that are not reimbursements/payroll/Venmo/Ramp. Vendor charges
                 that merely carry his name in the description are NOT owner pay.
  * Venmo/etc  : "VENMO" / "CASH APP" / "APPLE CASH" outflows are owner pay.
  * ADP        : payroll debits.
  * Exclusions : internal/external transfers, Ramp wallet/deposit moves, Mercury
                 IO credit-card payments/cashback, savings interest.
"""

import re
from typing import Any, Dict, Optional, Tuple

from src.constants import (
    BUCKET_REVENUE,
    BUCKET_OPERATING,
    BUCKET_PAYROLL,
    BUCKET_OWNER_PAY,
    BUCKET_OWNER_DRAW,
    BUCKET_EXCLUDED,
    FLAG_OWNER_CAR,
    FLAG_OWNER_DRAW_BOFA,
    FLAG_HARRISON_DIRECT,
    FLAG_VENMO,
)

# Substrings that mark a Mercury Venmo/CashApp/Apple-Cash "pay" outflow. These
# also disqualify a line from the Harrison-direct rule (a Venmo to Harrison is a
# Venmo pay, not a direct transfer).
_VENMO_TOKENS = ("VENMO", "CASH APP", "CASHAPP", "APPLE CASH")

# Substrings that mark Ramp / Mercury-IO credit movements. These disqualify a
# line from the Harrison-direct rule and (most of them) drive exclusion.
_RAMP_IO_TOKENS = (
    "RAMP WALLET",
    "RAMP; DEPOSIT",
    "ACH WITHDR",
    "RAMP; ACH",
    "IO PAYMENT",
    "IO AUTOPAY",
    "IO CASHBACK",
)

# All exclusion substrings (superset of the Ramp/IO ones, plus auto-transfer
# rules, generic cashback and interest).
_EXCLUSION_TOKENS = _RAMP_IO_TOKENS + (
    "PERCENTAGE-BASED RULE",
    "CASHBACK",
    "INTEREST",
)

_TRANSFER_KINDS = ("internalTransfer", "externalTransfer")


def _category(txn: Dict[str, Any]) -> Optional[str]:
    """mercuryCategory if present, else categoryData.name, else None."""
    return txn.get("mercuryCategory") or (txn.get("categoryData") or {}).get("name")


def _desc(txn: Dict[str, Any]) -> str:
    """Concatenated, upper-cased bankDescription + counterpartyName for matching."""
    bd = txn.get("bankDescription") or ""
    cp = txn.get("counterpartyName") or ""
    return (bd + " " + cp).upper()


def _month_key(txn: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    """(year, month) parsed from postedAt / failedAt / date, or None."""
    raw = txn.get("postedAt") or txn.get("failedAt") or txn.get("date")
    if not raw or not isinstance(raw, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})", raw)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _is_adp(desc_upper: str) -> bool:
    """True for ADP payroll lines: 'ADP ' anywhere, or description starts 'ADP'."""
    return "ADP " in desc_upper or desc_upper.startswith("ADP")


def _is_venmo(desc_upper: str) -> bool:
    return any(tok in desc_upper for tok in _VENMO_TOKENS)


def _is_ramp_io(desc_upper: str) -> bool:
    return any(tok in desc_upper for tok in _RAMP_IO_TOKENS)


def classify_mercury(
    txn: Dict[str, Any]
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Classify a single Mercury transaction.

    Returns (bucket, flag, category, review). First matching rule wins; see the
    module docstring for the priority order rationale.
    """
    category = _category(txn)
    desc = _desc(txn)
    amt = float(txn.get("amount") or 0)

    # 1. Owner Car (Capital One) -- before the generic transfer exclusion.
    if "CAPITAL ONE AUTO" in desc and "JORDAN" in desc:
        return BUCKET_OWNER_PAY, FLAG_OWNER_CAR, "Owner Car", None

    # 2. Owner Draw (BofA 4201 car). Only the ~$2,000 May-2026+ transfers are the
    #    car draw; anything else on 4201 is an ambiguous transfer -> excluded
    #    WITH a review note (never silently a draw).
    if "BANK OF AMERICA" in desc and "4201" in desc:
        abs_amt = abs(amt)
        month = _month_key(txn)
        is_may_or_later = month is not None and month >= (2026, 5)
        if 1900 <= abs_amt <= 2100 and is_may_or_later:
            return BUCKET_OWNER_DRAW, FLAG_OWNER_DRAW_BOFA, "Owner Draw", None
        review = (
            f"BofA 4201 transfer of ${abs_amt:,.2f} not matching the $2,000 car "
            "draw rule, confirm classification"
        )
        return BUCKET_EXCLUDED, None, "Transfer", review

    # 2b. Harrison owner distribution by other routes: the business paying down
    #    Harrison's personal Chase / Amex cards, or a JPMorgan external transfer
    #    to him. The owner confirmed these are distributions, not business spend.
    if (
        amt < 0
        and "GOLDFARB" in desc
        and (
            "CHASE CREDIT CRD" in desc
            or "AMEX EPAYMENT" in desc
            or ("JPMORGAN" in desc and "EXT TRNSFR" in desc)
        )
    ):
        return BUCKET_OWNER_PAY, FLAG_HARRISON_DIRECT, "Owner Pay", None

    # 2c. Transfers to Harrison's personal Chase checking (••8371) are owner pay,
    #    not an internal account transfer. (Owner confirmed ••8371 is his.)
    if amt < 0 and "CHASE" in desc and "8371" in desc:
        return BUCKET_OWNER_PAY, FLAG_HARRISON_DIRECT, "Owner Pay", None

    # 3. Harrison direct owner-pay transfer: the PAYEE is Harrison Goldfarb
    #    (exact counterparty, not merely his name appearing in a vendor
    #    description such as a Tesla or JPMorgan card charge), money out, and NOT
    #    an expense reimbursement (reimbursements pay him back for business costs,
    #    so they are operating expense, not owner pay) nor an ADP/Venmo/Ramp line.
    counterparty = (txn.get("counterpartyName") or "").strip().lower()
    if (
        counterparty == "harrison goldfarb"
        and amt < 0
        and txn.get("kind") != "expenseReimbursement"
        and not _is_adp(desc)
        and not _is_venmo(desc)
        and not _is_ramp_io(desc)
    ):
        return BUCKET_OWNER_PAY, FLAG_HARRISON_DIRECT, "Owner Pay", None

    # 4. Venmo / CashApp / Apple Cash pay outflow.
    if _is_venmo(desc) and amt < 0:
        return BUCKET_PAYROLL, FLAG_VENMO, "Pay", None

    # 5. ADP payroll (WAGE PAY, Tax, PAY-BY-PAY, PAYROLL FEES).
    if _is_adp(desc):
        return BUCKET_PAYROLL, None, "Payroll", None

    # 5b. Transfers in from the owners' old Chase / Bitter Herb account are money
    #    moving between the owners' own accounts, not customer revenue. Excluded as
    #    internal. (Real Square sales are counted directly from the Square source.)
    counterparty_raw = (txn.get("counterpartyName") or "").strip().upper()
    if amt > 0 and (
        counterparty_raw == "THE BITTER HERB"
        or ("JPMORGAN" in desc and "BITTER HERB" in desc)
    ):
        return BUCKET_EXCLUDED, None, "Internal transfer", (
            "Transfer in from the old Chase/Bitter Herb account, internal not revenue"
        )

    # 5c. Intuit / QuickBooks Payments deposits are customer revenue (Mercury does
    #    not always tag them Revenue).
    if amt > 0 and "INTUIT" in desc and "DEPOSIT" in desc:
        return BUCKET_REVENUE, None, "Revenue", None

    # 5d. ACCESS XP inbound ACH is a known customer, revenue.
    if amt > 0 and "ACCESS XP" in desc:
        return BUCKET_REVENUE, None, "Revenue", None

    # 5e. Sales tax remitted to the state (CDTFA / CA DEPT TAX) is a pass-through
    #    liability collected from customers, not an operating expense. Excluded.
    if "CDTFA" in desc or "CA DEPT TAX" in desc:
        return BUCKET_EXCLUDED, None, "Sales Tax Remittance", (
            "Sales tax remitted to the state, pass-through not an operating expense")

    # 6. Exclusions: transfers, Ramp/IO credit moves, auto-transfer rules,
    #    cashback, interest.
    if (
        txn.get("kind") in _TRANSFER_KINDS
        or any(tok in desc for tok in _EXCLUSION_TOKENS)
        or (category or "").upper().find("INTEREST") != -1
    ):
        return BUCKET_EXCLUDED, None, category or "Transfer", None

    # 7a. Square deposits in Mercury are EXCLUDED here. Square revenue is counted
    #     directly from the Square source (src/reconcile loads Square payouts), so
    #     counting the Mercury deposit too would double count. Pulling from Square
    #     also captures the months Square paid out to other banks.
    is_square_deposit = "SQUARE INC" in desc
    if is_square_deposit and amt > 0:
        return BUCKET_EXCLUDED, None, "Square payout (counted via Square)", (
            "Square deposit into Mercury, counted from the Square source instead"
        )

    # 7b. Other inbound revenue: genuine company ACH (Datafold, Foodbeast, etc.).
    if category == "Revenue" and amt > 0:
        return (
            BUCKET_REVENUE,
            None,
            "Revenue",
            "Inbound flagged revenue, confirm it is real customer revenue",
        )

    # 8. Default.
    if amt < 0:
        return BUCKET_OPERATING, None, category or "Uncategorized", None
    return (
        BUCKET_OPERATING,
        None,
        category or "Uncategorized",
        "Unexpected inflow, confirm whether this is revenue",
    )


def parse_amount(s: Any) -> float:
    """Parse a Ramp amount string into a SIGNED float using Mercury's convention.

    Ramp prints a plain charge as "$12.44" (money out) and a refund/credit as
    "-$18.00". We normalize to Mercury's sign convention: money out is negative,
    money in is positive. So "$12.44" -> -12.44 and "-$18.00" -> +18.00.
    Numeric inputs are passed through unchanged.
    """
    if isinstance(s, (int, float)):
        return float(s)
    neg = s.strip().startswith("-")
    val = float(re.sub(r"[^0-9.]", "", s))
    return val if neg else -val


def classify_ramp(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a single Ramp transaction.

    Ramp spend is 100% operating expense (the card has no income). State
    (CLEARED/PENDING) is handled later by reconcile, not here.
    """
    return {
        "bucket": BUCKET_OPERATING,
        "flag": None,
        "category": (
            txn.get("merchant_category")
            or txn.get("spend_allocation_name")
            or "Uncategorized"
        ),
        "review": None,
        "amount": parse_amount(txn.get("amount")),
        "counterparty": txn.get("merchant_name"),
    }
