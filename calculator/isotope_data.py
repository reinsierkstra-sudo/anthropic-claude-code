"""
calculator/isotope_data.py
--------------------------
Standalone helpers that slice isotope data lists into the time windows
used by the dashboard:

- ``get_last_friday``          — Friday that opened the current production week
- ``get_since_friday_data``    — records since last Friday (current week)
- ``get_previous_week_data``   — records from the week before last
- ``calculate_monthly_averages``          — monthly averages for past year
- ``calculate_monthly_averages_by_kant``  — Thallium monthly averages split by kant
"""

from collections import defaultdict
from datetime import datetime, timedelta, date


def _to_date(d):
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if hasattr(d, 'year') and not isinstance(d, datetime):
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(d, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
    return None


def get_last_friday() -> date:
    """Return the most-recent Friday (exclusive of today if today IS Friday)."""
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0:
        days_since_friday = 7
    return today - timedelta(days=days_since_friday)


def get_since_friday_data(data: list) -> list:
    """Return all records from *data* that fall in the current production week.

    A production week runs from the most recent Friday up to and including
    today.  Records are returned in ascending date order.
    """
    last_friday = get_last_friday()
    today = datetime.now().date()
    result = []
    for record in data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue
        if last_friday <= record_date <= today:
            new_record = record.copy()
            new_record['date'] = record_date.strftime('%Y-%m-%d')
            result.append(new_record)
    return sorted(result, key=lambda x: x['date'])


def get_previous_week_data(data: list) -> list:
    """Return all records from the previous production week.

    The previous week runs from (last_friday − 7 days) up to and including
    (last_friday − 1 day).  Records are returned in ascending date order.
    """
    last_friday      = get_last_friday()
    previous_friday  = last_friday - timedelta(days=7)
    last_thursday    = last_friday - timedelta(days=1)
    result = []
    for record in data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue
        if previous_friday <= record_date <= last_thursday:
            new_record = record.copy()
            new_record['date'] = record_date.strftime('%Y-%m-%d')
            result.append(new_record)
    return sorted(result, key=lambda x: x['date'])


def calculate_monthly_averages(data: list, use_targetstroom: bool = False) -> list:
    """Return monthly averages for the past 365 days.

    Parameters
    ----------
    data : list[dict]
        Isotope records.  Each must have a ``'date'`` key plus either
        ``'targetstroom'`` (when *use_targetstroom* is ``True``) or
        ``'efficiency'``.
    use_targetstroom : bool
        ``True`` for Ga/In/Tl (targetstroom µA), ``False`` for Rb/Io
        (efficiency field).

    Returns
    -------
    list[dict]
        ``[{'month': 'YYYY-MM', 'average': float, 'count': int}, ...]``
        sorted ascending, limited to the last 12 months.
    """
    today        = datetime.now().date()
    one_year_ago = today - timedelta(days=365)
    monthly: dict = defaultdict(list)

    for record in data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue
        month_start = record_date.replace(day=1)
        if use_targetstroom:
            v = record.get('targetstroom')
        else:
            v = record.get('efficiency')
        if v is not None:
            monthly[month_start].append(v)

    result = []
    for month_start, values in monthly.items():
        if values and datetime.strptime(month_start.strftime('%Y-%m'), '%Y-%m').date() >= one_year_ago:
            result.append({
                'month':   month_start.strftime('%Y-%m'),
                'average': sum(values) / len(values),
                'count':   len(values),
            })

    return sorted(result, key=lambda x: x['month'])


def calculate_monthly_averages_by_kant(data: list) -> tuple:
    """Return monthly targetstroom averages for Thallium, split by kant.

    Returns
    -------
    tuple[list, list]
        ``(averages_kant_12, averages_kant_21)`` — each a list in the same
        format as :func:`calculate_monthly_averages`.
    """
    today        = datetime.now().date()
    one_year_ago = today - timedelta(days=365)
    monthly_12: dict = defaultdict(list)
    monthly_21: dict = defaultdict(list)

    for record in data:
        kant = record.get('kant')
        if kant in ('Unknown', None):
            continue
        record_date = _to_date(record['date'])
        if record_date is None:
            continue
        month_start = record_date.replace(day=1)
        v = record.get('targetstroom')
        if v is None:
            continue
        if kant == '1.2':
            monthly_12[month_start].append(v)
        elif kant == '2.1':
            monthly_21[month_start].append(v)

    def _build(monthly):
        result = []
        for month_start, values in monthly.items():
            if values and datetime.strptime(month_start.strftime('%Y-%m'), '%Y-%m').date() >= one_year_ago:
                result.append({
                    'month':   month_start.strftime('%Y-%m'),
                    'average': sum(values) / len(values),
                    'count':   len(values),
                })
        return sorted(result, key=lambda x: x['month'])

    return _build(monthly_12), _build(monthly_21)
