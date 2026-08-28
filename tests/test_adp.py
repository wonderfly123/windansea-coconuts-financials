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
