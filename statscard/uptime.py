from __future__ import annotations

from datetime import date


def format_uptime(start: date, today: date) -> str:
    """Format elapsed time from start to today as 'X anos, Y meses' (Portuguese)."""
    months_total = (today.year - start.year) * 12 + (today.month - start.month)
    if today.day < start.day:
        months_total -= 1
    months_total = max(months_total, 0)
    years, months = divmod(months_total, 12)
    year_part = f"{years} {'ano' if years == 1 else 'anos'}"
    month_part = f"{months} {'mês' if months == 1 else 'meses'}"
    if years and months:
        return f"{year_part}, {month_part}"
    if years:
        return year_part
    return month_part
