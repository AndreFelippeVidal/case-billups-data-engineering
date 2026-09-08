from billups.report import _month_label, _money


def test_report_formats_months_and_money():
    """Report presentation formats Gold values consistently."""
    assert _month_label("2017-10") == "Oct 2017"
    assert _money("12.3") == "$12.30"
