import re

import pytest

from src.runway import loaders as L
from src.runway import plan as P
from src.runway import build


def test_loaders_read_real_files():
    assert len(L.load_card()) > 100
    assert len(L.load_wallet()) > 100
    assert len(L.load_db_rows("data/coconuts.db", "2026-05-01", "2026-06-18")) > 100
    adp = L.load_adp()
    assert adp and adp[0]["check_date"].startswith("2026-")
    assert len(L.load_invoices()) == 200


@pytest.fixture(scope="module")
def ctx():
    return build.build_context()


def test_context_numbers(ctx):
    assert ctx["cash"] == pytest.approx(127454.72)
    assert ctx["ar"]["count"] == 37 and ctx["ar"]["total"] == pytest.approx(60003.70)
    assert ctx["avgs"][P.COGS] > 5000 and ctx["avgs"][P.OVERHEAD] > 5000
    assert ctx["core"]["plan_total"] == 28800
    assert "2026-01" in ctx["rev_months"] and len(ctx["proj"]["baseline"]) == 12


def test_render_contents(ctx):
    html = build.render(ctx)
    for needle in ["Money in the bank", "$127,455", "TBD", "Roles from the doc", "Runway, the next twelve months",
                   'data-preset="plan"', "window.RUNWAY", "Sales tax remitted", "How we sell", "Owner: <strong>Trent</strong>", "<title>Windansea Coconuts Runway</title>"]:
        assert needle in html, needle
    # No dashes as pauses in headings or table headers
    for tag in re.findall(r"<(?:h[1-3]|th)[^>]*>(.*?)</(?:h[1-3]|th)>", html):
        assert "—" not in tag and " - " not in tag, tag


def test_build_writes_file(tmp_path):
    out = build.main(tmp_path / "x.html")
    assert out.stat().st_size > 20_000
