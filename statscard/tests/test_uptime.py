from datetime import date

from statscard.uptime import format_uptime


def test_format_uptime_same_day_is_zero_months():
    assert format_uptime(date(2025, 2, 1), date(2025, 2, 1)) == "0 meses"


def test_format_uptime_singular_month():
    assert format_uptime(date(2025, 2, 1), date(2025, 3, 1)) == "1 mês"


def test_format_uptime_years_and_months():
    assert format_uptime(date(2025, 2, 1), date(2026, 9, 1)) == "1 ano, 7 meses"


def test_format_uptime_whole_years_no_months():
    assert format_uptime(date(2025, 2, 1), date(2027, 2, 1)) == "2 anos"


def test_format_uptime_day_of_month_not_yet_reached():
    # One day short of completing another month.
    assert format_uptime(date(2025, 2, 15), date(2025, 3, 10)) == "0 meses"
