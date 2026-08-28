from src.runway import plan as P
from src.runway.classify import tag_card, tag_wallet, tag_db_row, tag_adp_row


def card(merchant, amount="$10.00", state="CLEARED", cat="Restaurants"):
    return {"merchant_name": merchant, "amount": amount, "state": state,
            "merchant_category": cat, "transaction_time": "2026-07-04T10:00:00+00:00",
            "spent_by_user": "Harrison Goldfarb"}


def wallet(ttype, signed, src="", dst="", status="COMPLETED", memo=None, details=""):
    return {"transfer_type": ttype, "signed_amount": signed, "status": status,
            "created_at": "2026-08-04T10:00:00+00:00", "source_account_name": src,
            "destination_account_name": dst, "memo": memo, "transaction_details": details}


def dbrow(counterparty, amount, bucket="Operating Expense", flag=None, date="2026-05-10", desc=""):
    return {"date": date, "counterparty": counterparty, "description": desc,
            "category": "", "bucket": bucket, "flag": flag, "amount": amount}


# card -------------------------------------------------------------------
def test_card_sun_hing_is_cogs():
    r = tag_card(card("SUN HING FOODS, INC", "$1,131.00"))
    assert r.section == P.COGS and r.amount == 1131.0 and r.date == "2026-07-04"


def test_card_uber_is_overhead_and_known():
    r = tag_card(card("Uber", cat="Taxi and Rideshare"))
    assert r.section == P.OVERHEAD and r.known is True


def test_card_general_merchandise_marked_for_review():
    assert tag_card(card("Ariana Cohen", cat="General Merchandise")).known is False


def test_card_cogs_is_known():
    assert tag_card(card("Coy's Produce Co")).known is True


def test_card_nathan_zini_is_noncore_contractor():
    r = tag_card(card("Nathan Zini"))
    assert r.section == P.PEOPLE_NONCORE and r.sub == P.SUB_CONTRACTOR


def test_card_kosmos_is_tim_core():
    r = tag_card(card("Kosmos Accounting"))
    assert r.section == P.PEOPLE_CORE and r.sub == "tim"


def test_card_declined_ignored():
    assert tag_card(card("Uber", state="DECLINED")) is None


# wallet -------------------------------------------------------------------
def test_wallet_square_deposit_is_revenue_after_cutover():
    r = tag_wallet(wallet("DEPOSIT", 500, src="Square Inc"))
    assert r.section == P.REVENUE and r.label == "Square payouts"


def test_wallet_currency_cloud_is_revenue():
    r = tag_wallet(wallet("DEPOSIT", 67226, src="Currency Cloud"))
    assert r.section == P.REVENUE and r.amount == 67226


def test_wallet_macys_ach_is_revenue():
    assert tag_wallet(wallet("DEPOSIT", 6912, src="MACYS CORP.SVCS.")).section == P.REVENUE


def test_wallet_cleared_check_is_revenue():
    assert tag_wallet(wallet("CHECK_DEPOSIT", 4185, src="External account")).section == P.REVENUE


def test_wallet_bitter_herb_excluded():
    assert tag_wallet(wallet("DEPOSIT", 14485, src="The Bitter Herb")).section == P.EXCLUDED


def test_wallet_adp_wage_pay_excluded():
    assert tag_wallet(wallet("WITHDRAWAL", -4617, dst="ADP WAGE PAY")).section == P.EXCLUDED


def test_wallet_adp_fees_overhead():
    assert tag_wallet(wallet("WITHDRAWAL", -89, dst="ADP PAYROLL FEES")).section == P.OVERHEAD


def test_wallet_statement_payment_excluded():
    assert tag_wallet(wallet("STATEMENT_PAYMENT", -4137)).section == P.EXCLUDED


def test_wallet_sales_tax():
    assert tag_wallet(wallet("WITHDRAWAL", -12278, dst="CA DEPT TAX FEE")).section == P.SALES_TAX


def test_wallet_venmo_noncore():
    r = tag_wallet(wallet("WITHDRAWAL", -381, dst="VENMO"))
    assert r.section == P.PEOPLE_NONCORE and r.sub == P.SUB_VENMO


def test_wallet_chase_8371_is_harrison():
    r = tag_wallet(wallet("WITHDRAWAL", -2000, dst="TOTAL CHECKING (···· 8371)"))
    assert r.section == P.PEOPLE_CORE and r.sub == "harrison" and r.amount == 2000


def test_wallet_bofa_4201_and_capital_one_are_jordan():
    assert tag_wallet(wallet("WITHDRAWAL", -540, dst="Adv Plus Banking (···· 4201)")).sub == "jordan"
    assert tag_wallet(wallet("WITHDRAWAL", -674.51, dst="CAPITAL ONE AUTO")).sub == "jordan"


def test_wallet_reimbursement_overhead():
    r = tag_wallet(wallet("REIMBURSEMENT_PAYMENT", -975, details="Paid to Harrison Goldfarb (ZBMUBSRFHC)"))
    assert r.section == P.OVERHEAD and r.label == "Reimbursement: Harrison Goldfarb"


def test_wallet_error_status_ignored():
    assert tag_wallet(wallet("CHECK_DEPOSIT", 14491, status="ERROR")) is None


def test_wallet_billpay_sun_hing_cogs():
    r = tag_wallet(wallet("BILLPAY_PAYMENT", -1131, memo="Bill #IL319215 - SUN HING FOODS, INC.",
                          details="SUN HING FOODS, INC. (NAXLU54HQT)"))
    assert r.section == P.COGS


def test_wallet_billpay_josh_escalante_noncore():
    r = tag_wallet(wallet("BILLPAY_PAYMENT", -515, memo="Bill #001 - Josh Escalante", details="Josh Escalante (X)"))
    assert r.section == P.PEOPLE_NONCORE and r.sub == P.SUB_CONTRACTOR


def test_wallet_billpay_photographer_overhead():
    assert tag_wallet(wallet("BILLPAY_PAYMENT", -95, memo="Bill #1 - Miguel Flores Photography")).section == P.OVERHEAD


def test_wallet_transfer_to_mercury_excluded():
    assert tag_wallet(wallet("WITHDRAWAL", -5500, dst="SoCal ••4813 (···· 4813)")).section == P.EXCLUDED


# db rows ------------------------------------------------------------------
def test_db_sales_tax_rule_beats_excluded_bucket():
    r = tag_db_row(dbrow("CA DEPT TAX FEE", -3858, bucket="Excluded"))
    assert r.section == P.SALES_TAX and r.amount == 3858


def test_db_adp_wage_pay_excluded():
    assert tag_db_row(dbrow("ADP WAGE PAY", -5000, bucket="Payroll")).section == P.EXCLUDED


def test_db_square_inflow_excluded():
    assert tag_db_row(dbrow("Square Inc", 3000, bucket="Excluded")).section == P.EXCLUDED


def test_db_datafold_revenue():
    r = tag_db_row(dbrow("Datafold, Inc.", 25860, bucket="Revenue"))
    assert r.section == P.REVENUE and r.amount == 25860


def test_db_harrison_flag():
    r = tag_db_row(dbrow("Chase - Checking ••8371", -5500, bucket="Owner Pay", flag=P.__dict__.get("FLAG", "Owner Pay Direct Transfer (Harrison)")))
    assert r.section == P.PEOPLE_CORE and r.sub == "harrison"


def test_db_bofa_split_on_jun_1():
    recs = tag_db_row(dbrow("Bank of America - Checking ••4201", -3400, bucket="Excluded", date="2026-06-01"))
    assert isinstance(recs, list) and {(r.sub, r.amount) for r in recs} == {("jordan", 2000.0), ("harrison", 1400.0)}


def test_db_bofa_2000_is_jordan():
    r = tag_db_row(dbrow("Bank of America - Checking ••4201", -2000, bucket="Owner Draw", date="2026-05-15"))
    assert r.section == P.PEOPLE_CORE and r.sub == "jordan"


def test_db_row_after_cutover_ignored():
    assert tag_db_row(dbrow("Uber", -10, date="2026-06-19")) is None


def test_db_venmo_noncore():
    r = tag_db_row(dbrow("VENMO", -200, bucket="Payroll", flag="Venmo/CashApp Pay"))
    assert r.section == P.PEOPLE_NONCORE and r.sub == P.SUB_VENMO


def test_db_indico_noncore():
    assert tag_db_row(dbrow("Indico Thread Consulting", -4000)).section == P.PEOPLE_NONCORE


def test_db_card_paydown_excluded():
    assert tag_db_row(dbrow("Checking Account", -1000, bucket="Excluded")).section == P.EXCLUDED


def test_db_refund_inflow_reduces_overhead():
    r = tag_db_row(dbrow("Amazon", 33, bucket="Operating Expense"))
    assert r.section == P.OVERHEAD and r.amount == -33


# adp ----------------------------------------------------------------------
def test_adp_harrison_core():
    r = tag_adp_row({"check_date": "2026-07-15", "name": "Goldfarb, Harrison L", "total_expenses": 1076.5})
    assert r.section == P.PEOPLE_CORE and r.sub == "harrison" and r.amount == 1076.5


def test_adp_grace_hourly():
    r = tag_adp_row({"check_date": "2026-07-15", "name": "O'malley, Grace", "total_expenses": 300})
    assert r.section == P.PEOPLE_NONCORE and r.sub == P.SUB_ADP_HOURLY


def test_adp_april_check_ignored():
    assert tag_adp_row({"check_date": "2026-04-30", "name": "Livolsi, Trent", "total_expenses": 1}) is None
