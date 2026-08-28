"""Tests for the transaction classification engine (src/classify.py).

Records use the REAL Mercury/Ramp field shapes observed on disk:
  - Mercury: amount is a signed NUMBER (negative = money out), bankDescription,
    counterpartyName, kind, mercuryCategory (or categoryData.name), postedAt.
  - Ramp: amount is a STRING like "$34.22" / "-$18.00", merchant_name, etc.

Real anchor data confirmed in data/raw/mercury_transactions.json:
  - Capital One owner car: "CAPITAL ONE AUTO; DIRECTPAY; Jordan Millhausen",
    amount -674.51, monthly (Jan-May 2026), kind "other".
  - BofA 4201: counterpartyName "Bank of America - Checking ••4201", bankDesc
    "Transfer from Mercury to another bank account", kind externalTransfer.
    Only the -2000 on 2026-05-15 matches the $2,000 car-draw rule; the others
    (-200, -125, -3400, -540, -296.22, -150) do not.
  - Square revenue deposits: counterpartyName "Square Inc",
    bankDesc "Square Inc; SQ260518; Harrison Goldfarb", category "Revenue", amt>0.
"""

import pytest

from src import classify
from src.classify import classify_mercury, classify_ramp, parse_amount
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


# ---------------------------------------------------------------------------
# Helpers / record factories (real shapes)
# ---------------------------------------------------------------------------

def merc(**over):
    base = {
        "id": "x",
        "amount": -10.0,
        "status": "sent",
        "bankDescription": "",
        "counterpartyName": "",
        "kind": "debitCardTransaction",
        "postedAt": "2026-05-10T00:00:00Z",
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------

def test_square_deposit_in_mercury_is_excluded():
    # Square deposits into Mercury are excluded; Square revenue is counted from the
    # Square source directly (src/reconcile loads payouts) to avoid double counting.
    t = merc(
        amount=3422.51,
        kind="other",
        bankDescription="Square Inc; SQ260515; Harrison Goldfarb",
        counterpartyName="Square Inc",
        mercuryCategory="Revenue",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert flag is None


def test_non_square_revenue_gets_review_note():
    t = merc(
        amount=25860.0,
        kind="other",
        bankDescription="Datafold, Inc.; Receivable; The Bitter Herb LLC",
        counterpartyName="Datafold, Inc.",
        mercuryCategory="Revenue",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_REVENUE
    assert flag is None
    assert category == "Revenue"
    assert review is not None
    assert "revenue" in review.lower()


def test_non_square_revenue_via_categoryData_name():
    # category comes from categoryData.name when mercuryCategory absent; a genuine
    # company ACH (not Square) stays revenue.
    t = merc(
        amount=834.08,
        kind="other",
        bankDescription="ACME CATERING; ACH PMT",
        counterpartyName="Acme Catering",
        categoryData={"name": "Revenue"},
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_REVENUE


# ---------------------------------------------------------------------------
# Owner Car (Capital One) - priority over generic transfer exclusion
# ---------------------------------------------------------------------------

def test_capital_one_auto_jordan_is_owner_pay_car():
    t = merc(
        amount=-674.51,
        kind="other",
        bankDescription="CAPITAL ONE AUTO; DIRECTPAY; Jordan Millhausen",
        counterpartyName="CAPITAL ONE AUTO",
        postedAt="2026-05-16T01:05:21Z",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_OWNER_PAY
    assert flag == FLAG_OWNER_CAR
    assert category == "Owner Car"
    assert review is None


# ---------------------------------------------------------------------------
# Owner Draw (BofA 4201 car)
# ---------------------------------------------------------------------------

def test_bofa_4201_2000_in_may_is_owner_draw():
    t = merc(
        amount=-2000.0,
        kind="externalTransfer",
        bankDescription="Transfer from Mercury to another bank account",
        counterpartyName="Bank of America - Checking ••4201",
        postedAt="2026-05-15T16:16:54Z",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_OWNER_DRAW
    assert flag == FLAG_OWNER_DRAW_BOFA
    assert category == "Owner Draw"
    assert review is None


def test_bofa_4201_2000_boundary_amounts_in_may():
    # 1900 and 2100 inclusive boundaries count as the car draw.
    for amt in (-1900.0, -2100.0):
        t = merc(
            amount=amt,
            kind="externalTransfer",
            bankDescription="Transfer from Mercury to another bank account",
            counterpartyName="Bank of America - Checking ••4201",
            postedAt="2026-06-01T00:00:00Z",
        )
        bucket, flag, _, review = classify_mercury(t)
        assert bucket == BUCKET_OWNER_DRAW, amt
        assert flag == FLAG_OWNER_DRAW_BOFA, amt


def test_bofa_4201_wrong_amount_is_excluded_with_review():
    t = merc(
        amount=-3400.0,
        kind="externalTransfer",
        bankDescription="Transfer from Mercury to another bank account",
        counterpartyName="Bank of America - Checking ••4201",
        postedAt="2026-06-01T14:40:27Z",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert flag is None
    assert category == "Transfer"
    assert review is not None
    assert "4201" in review


def test_bofa_4201_2000_before_may_is_excluded_with_review():
    # $2,000 but dated April 2026 -> rule only applies May 2026 or later.
    t = merc(
        amount=-2000.0,
        kind="externalTransfer",
        bankDescription="Transfer from Mercury to another bank account",
        counterpartyName="Bank of America - Checking ••4201",
        postedAt="2026-04-10T00:00:00Z",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert review is not None


# ---------------------------------------------------------------------------
# Harrison direct transfer
# ---------------------------------------------------------------------------

def test_harrison_direct_is_owner_pay():
    # A genuine direct transfer whose payee IS Harrison Goldfarb (not a
    # reimbursement, not a vendor charge bearing his name).
    t = merc(
        amount=-1500.00,
        kind="externalTransfer",
        bankDescription="Send Money transaction to Harrison Goldfarb",
        counterpartyName="Harrison Goldfarb",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_OWNER_PAY
    assert flag == FLAG_HARRISON_DIRECT
    assert category == "Owner Pay"
    assert review is None


def test_harrison_expense_reimbursement_is_not_owner_pay():
    # Reimbursing Harrison for a business cost he paid personally is an operating
    # expense, NOT owner pay. (The brief: owner-pay transfers are "not reimbursements".)
    t = merc(
        amount=-398.08,
        kind="expenseReimbursement",
        bankDescription="Expense Reimbursement",
        counterpartyName="Harrison Goldfarb",
        categoryData={"name": "Travel & Transportation"},
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_OPERATING
    assert flag != FLAG_HARRISON_DIRECT


def test_harrison_name_in_vendor_description_is_not_owner_pay():
    # A Tesla / JPMorgan style card charge that merely carries "HARRISON GOLDFARB"
    # in the bank description must NOT be swept into owner pay; the payee is the vendor.
    t = merc(
        amount=-220.00,
        kind="debitCardTransaction",
        bankDescription="TESLA INC; HARRISON GOLDFARB",
        counterpartyName="Tesla Inc",
        mercuryCategory="Automotive",
    )
    bucket, flag, category, _ = classify_mercury(t)
    assert bucket == BUCKET_OPERATING
    assert flag != FLAG_HARRISON_DIRECT
    assert category == "Automotive"


def test_harrison_positive_amount_not_harrison_direct():
    # Square deposit description contains "Harrison Goldfarb" but amt>0, so it is
    # never Harrison owner pay (it is an excluded Square deposit).
    t = merc(
        amount=834.08,
        kind="other",
        bankDescription="Square Inc; SQ260518; Harrison Goldfarb",
        counterpartyName="Square Inc",
        mercuryCategory="Revenue",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert flag != FLAG_HARRISON_DIRECT


def test_harrison_on_adp_line_is_payroll_not_owner_pay():
    t = merc(
        amount=-4868.62,
        kind="other",
        bankDescription="ADP WAGE PAY; WAGE PAY; HARRISON GOLDFARB HARR",
        counterpartyName="ADP WAGE PAY",
        mercuryCategory="Payroll",
    )
    bucket, flag, category, _ = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag is None


def test_harrison_on_venmo_line_is_venmo_payroll():
    t = merc(
        amount=-50.0,
        kind="other",
        bankDescription="VENMO; PAYMENT; HARRISON GOLDFARB",
        counterpartyName="VENMO",
    )
    bucket, flag, category, _ = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag == FLAG_VENMO


# ---------------------------------------------------------------------------
# Venmo / CashApp / Apple Cash pay
# ---------------------------------------------------------------------------

def test_venmo_outflow_is_payroll_venmo():
    t = merc(
        amount=-400.0,
        kind="other",
        bankDescription="VENMO; PAYMENT; HARRISON GOLDFARB",
        counterpartyName="VENMO",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag == FLAG_VENMO
    assert category == "Pay"
    assert review is None


def test_apple_cash_outflow_is_payroll_venmo():
    t = merc(
        amount=-100.0,
        kind="debitCardTransaction",
        bankDescription="APPLE CASH SENT MONEY",
        counterpartyName="Apple Wallet",
        mercuryCategory="Fees",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag == FLAG_VENMO


def test_cashapp_outflow_is_payroll_venmo():
    t = merc(
        amount=-25.0,
        bankDescription="CASH APP*JOHN DOE",
        counterpartyName="Cash App",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag == FLAG_VENMO


# ---------------------------------------------------------------------------
# ADP payroll
# ---------------------------------------------------------------------------

def test_adp_wage_pay_is_payroll_no_flag():
    t = merc(
        amount=-3697.20,
        kind="other",
        bankDescription="ADP WAGE PAY; WAGE PAY; HARRISON GOLDFARB HARR",
        counterpartyName="ADP WAGE PAY",
        mercuryCategory="Payroll",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag is None
    assert category == "Payroll"
    assert review is None


def test_adp_tax_is_payroll():
    t = merc(
        amount=-1417.30,
        kind="other",
        bankDescription="ADP Tax; ADP Tax; HARRISON GOLDFARB",
        counterpartyName="ADP Tax",
        mercuryCategory="Taxes",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag is None


def test_adp_payroll_fees_is_payroll():
    t = merc(
        amount=-41.0,
        kind="other",
        bankDescription="ADP PAYROLL FEES; ADP FEES; 720922567THE BITTER HE",
        counterpartyName="ADP PAYROLL FEES",
        mercuryCategory="Legal & Professional Services",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_PAYROLL
    assert flag is None


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------

def test_internal_transfer_kind_is_excluded():
    t = merc(
        amount=-1775.13,
        kind="internalTransfer",
        bankDescription="Percentage-based rule auto-transfer",
        counterpartyName="Mercury Savings ••3211",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_external_transfer_kind_is_excluded():
    t = merc(
        amount=-10574.07,
        kind="externalTransfer",
        bankDescription="Transfer from Mercury to another bank account",
        counterpartyName="Ramp - Checking ••5402",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_ramp_deposit_is_excluded():
    t = merc(
        amount=-12000.0,
        kind="other",
        bankDescription="RAMP; DEPOSIT; Estimated Taxes",
        counterpartyName="RAMP",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_ramp_ach_withdr_is_excluded():
    t = merc(
        amount=3000.0,
        kind="other",
        bankDescription="RAMP; ACH WITHDR; SoCal 4813",
        counterpartyName="RAMP",
        categoryData={"name": "Transfer"},
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_io_payment_is_excluded():
    t = merc(
        amount=-5272.93,
        kind="other",
        bankDescription="IO PAYMENT",
        counterpartyName="Mercury Credit",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_io_autopay_is_excluded():
    t = merc(
        amount=-4664.41,
        kind="other",
        bankDescription="IO AUTOPAY",
        counterpartyName="Mercury Credit",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_percentage_based_rule_is_excluded():
    t = merc(
        amount=2.94,
        kind="internalTransfer",
        bankDescription="Percentage-based rule auto-transfer",
        counterpartyName="Mercury Checking ••4813",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_io_cashback_is_excluded():
    t = merc(
        amount=79.09,
        kind="other",
        bankDescription=None,
        counterpartyName="Mercury IO Cashback",
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


def test_interest_is_excluded():
    t = merc(
        amount=0.01,
        kind="other",
        bankDescription="May interest payment",
        counterpartyName="Savings Interest",
        categoryData={"name": "Interest Earned"},
    )
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED


# ---------------------------------------------------------------------------
# Default operating expense / unexpected inflow
# ---------------------------------------------------------------------------

def test_generic_card_spend_is_operating_with_category():
    t = merc(
        amount=-29.99,
        kind="debitCardTransaction",
        bankDescription="ZAPIER.COM/CHARGE",
        counterpartyName="Zapier",
        mercuryCategory="Software",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_OPERATING
    assert flag is None
    assert category == "Software"
    assert review is None


def test_generic_spend_without_category_is_uncategorized():
    t = merc(amount=-12.0, bankDescription="SOME VENDOR", counterpartyName="Vendor")
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_OPERATING
    assert category == "Uncategorized"
    assert review is None


def test_unexpected_inflow_is_operating_with_review():
    # amt>0, not revenue, not excluded -> flagged for confirmation.
    t = merc(
        amount=500.0,
        kind="other",
        bankDescription="MYSTERY DEPOSIT",
        counterpartyName="Unknown Sender",
    )
    bucket, flag, category, review = classify_mercury(t)
    assert bucket == BUCKET_OPERATING
    assert review is not None
    assert "inflow" in review.lower()


# ---------------------------------------------------------------------------
# parse_amount
# ---------------------------------------------------------------------------

def test_parse_amount_plain_charge_is_negative():
    assert parse_amount("$12.44") == -12.44


def test_parse_amount_refund_is_positive():
    assert parse_amount("-$18.00") == 18.00


def test_parse_amount_numeric_passthrough():
    assert parse_amount(34.22) == 34.22
    assert parse_amount(-5) == -5.0


def test_parse_amount_handles_commas():
    assert parse_amount("$1,234.56") == -1234.56


# ---------------------------------------------------------------------------
# Ramp
# ---------------------------------------------------------------------------

def test_ramp_charge_is_operating_negative_amount():
    t = {
        "transaction_uuid": "r1",
        "amount": "$12.44",
        "merchant_name": "Some Vendor",
        "merchant_category": "Office",
        "spend_allocation_name": "Ops",
        "state": "CLEARED",
    }
    out = classify_ramp(t)
    assert out["bucket"] == BUCKET_OPERATING
    assert out["flag"] is None
    assert out["amount"] == -12.44
    assert out["category"] == "Office"
    assert out["counterparty"] == "Some Vendor"
    assert out["review"] is None


def test_ramp_refund_is_operating_positive_amount():
    t = {
        "transaction_uuid": "r2",
        "amount": "-$18.00",
        "merchant_name": "Refund Co",
        "merchant_category": None,
        "spend_allocation_name": "Travel",
        "state": "CLEARED",
    }
    out = classify_ramp(t)
    assert out["bucket"] == BUCKET_OPERATING
    assert out["amount"] == 18.00
    # category falls back to spend_allocation_name when merchant_category missing.
    assert out["category"] == "Travel"


def test_ramp_category_fallback_to_uncategorized():
    t = {"transaction_uuid": "r3", "amount": "$5.00", "merchant_name": "X"}
    out = classify_ramp(t)
    assert out["category"] == "Uncategorized"


# ---------------------------------------------------------------------------
# Constants are imported, not hardcoded
# ---------------------------------------------------------------------------

def test_uses_constants_module():
    assert classify.BUCKET_REVENUE == BUCKET_REVENUE
    assert classify.FLAG_VENMO == FLAG_VENMO


# ---------------------------------------------------------------------------
# Owner-confirmed reclassifications (June 2026 review)
# ---------------------------------------------------------------------------

def test_bitter_herb_inflow_is_excluded_internal():
    # Money moved in from the owners' own old account, internal not customer revenue.
    t = merc(amount=10000.0, kind="other",
             bankDescription="THE BITTER HERB; ACH Pmt; Windansea Coconuts",
             counterpartyName="THE BITTER HERB", categoryData={"name": "Revenue"})
    bucket, flag, cat, review = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert flag is None


def test_jpmorgan_bitter_herb_transfer_is_excluded_internal():
    t = merc(amount=7500.0, kind="other",
             bankDescription="JPMorgan Chase; Ext Trnsfr; THE BITTER HERB L.L.C.",
             counterpartyName="JPMorgan Chase")
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert flag is None


def test_intuit_deposit_is_revenue():
    t = merc(amount=2114.20, kind="other",
             bankDescription="INTUIT 81259283; DEPOSIT; HARRISON GOLDFARB",
             counterpartyName="INTUIT")
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_REVENUE
    assert flag is None


def test_access_xp_inflow_is_revenue():
    t = merc(amount=3711.99, kind="other",
             bankDescription="ACCESS XP LLC; ACH PMNT; Windansea Coconuts",
             counterpartyName="ACCESS XP LLC")
    assert classify_mercury(t)[0] == BUCKET_REVENUE


def test_chase_card_payment_to_harrison_is_owner_pay():
    t = merc(amount=-8000.0, kind="other",
             bankDescription="CHASE CREDIT CRD; EPAY; HARRISON L GOLDFARB",
             counterpartyName="CHASE CREDIT CRD")
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_OWNER_PAY
    assert flag == FLAG_HARRISON_DIRECT


def test_amex_payment_to_harrison_is_owner_pay():
    t = merc(amount=-2047.24, kind="other",
             bankDescription="AMEX EPAYMENT; ACH PMT; HARRISON GOLDFARB",
             counterpartyName="AMEX EPAYMENT")
    assert classify_mercury(t)[:2] == (BUCKET_OWNER_PAY, FLAG_HARRISON_DIRECT)


def test_jpmorgan_transfer_to_harrison_is_owner_pay():
    t = merc(amount=-538.62, kind="other",
             bankDescription="JPMorgan Chase; Ext Trnsfr; HARRISON L GOLDFARB",
             counterpartyName="JPMorgan Chase")
    assert classify_mercury(t)[:2] == (BUCKET_OWNER_PAY, FLAG_HARRISON_DIRECT)


def test_intuit_outflow_stays_operating_expense():
    # A payment TO Intuit (software) is an expense, not revenue.
    t = merc(amount=-80.0, kind="debitCardTransaction",
             bankDescription="INTUIT *QuickBooks", counterpartyName="Intuit")
    assert classify_mercury(t)[0] == BUCKET_OPERATING


def test_chase_8371_transfer_is_harrison_owner_pay():
    # Transfers to Harrison's personal Chase checking ••8371 are owner pay, not
    # an excluded internal transfer.
    t = merc(amount=-6000.0, kind="externalTransfer",
             bankDescription="Transfer from Mercury to another bank account",
             counterpartyName="Chase - Checking ••8371")
    bucket, flag, _, _ = classify_mercury(t)
    assert bucket == BUCKET_OWNER_PAY
    assert flag == FLAG_HARRISON_DIRECT


def test_cdtfa_sales_tax_is_excluded():
    t = merc(amount=-3858.0, kind="other",
             bankDescription="CA DEPT TAX FEE; CDTFA EPMT; HLG LLC",
             counterpartyName="CA DEPT TAX FEE")
    bucket, flag, cat, review = classify_mercury(t)
    assert bucket == BUCKET_EXCLUDED
    assert "tax" in cat.lower()
