"""
calculator/efficiency.py
------------------------
Standalone functions for efficiency KPI calculations.

Efficiency is measured as the rubidium cyclotron current efficiency (%).
Data source: rubidium_data records with an 'efficiency' field.
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, date


def _to_date(d):
    """Normalise any date/datetime/str value to a datetime.date, or None on failure."""
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


def _get_friday_week(d):
    """Return the Friday that starts the Friday-Thursday week containing date d."""
    return d - timedelta(days=(d.weekday() - 4) % 7)


def get_efficiency_weeks(gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings):
    """Get last 10 weeks of efficiency data with color coding.

    Uses rubidium_data records that have a non-zero 'efficiency' field.

    Returns:
        (last_10_weeks, average) where last_10_weeks is a list of dicts with
        keys 'week', 'percentage', 'color', 'no_data', and average is a float.
    """
    efficiency_data = rubidium_data

    # Return empty list if no data
    if not efficiency_data:
        return [], 0

    # Filter out zeros (already done in extract)
    valid_data = [d for d in efficiency_data if d['efficiency'] != 0]

    if not valid_data:
        return [], 0

    # Calculate mean and std for outlier detection (exclude outliers from average calc)
    if len(valid_data) > 3:
        efficiencies = [d['efficiency'] for d in valid_data]
        mean = statistics.mean(efficiencies)
        stdev = statistics.stdev(efficiencies)

        # Filter outliers (beyond 2 standard deviations)
        non_outliers = [e for e in efficiencies if abs(e - mean) <= 2 * stdev]

        # Calculate average without outliers
        if non_outliers:
            average = statistics.mean(non_outliers)
        else:
            average = mean
    else:
        average = statistics.mean([d['efficiency'] for d in valid_data]) if valid_data else 0

    # Build a lookup: (iso_year, iso_week) -> list of efficiencies
    week_lookup = {}
    for record in valid_data:
        d = record['date']
        if isinstance(d, datetime):
            d = d.date()
        elif isinstance(d, str):
            try:
                d = datetime.strptime(d, '%Y-%m-%d').date()
            except Exception:
                continue
        iso_year, iso_week, _ = d.isocalendar()
        key = (iso_year, iso_week)
        if key not in week_lookup:
            week_lookup[key] = []
        week_lookup[key].append(record['efficiency'])

    # Generate fixed last 10 production weeks using Thursday-based ISO week
    # (production week = Friday–Thursday; week label = ISO week of that Thursday)
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7  # 0 if today is Friday
    current_friday = today - timedelta(days=days_since_friday)
    fixed_weeks = []
    seen = set()
    for i in range(9, -1, -1):
        friday_i = current_friday - timedelta(weeks=i)
        thursday_i = friday_i + timedelta(days=6)
        iso_year, iso_week, _ = thursday_i.isocalendar()
        key = (iso_year, iso_week)
        if key not in seen:
            seen.add(key)
            fixed_weeks.append(key)

    last_10 = []
    for (yr, wk) in fixed_weeks:
        if (yr, wk) in week_lookup:
            effs = week_lookup[(yr, wk)]
            avg_eff = sum(effs) / len(effs)
            percentage = avg_eff * 100
            color = "#3BB143" if avg_eff >= average else "#FF2400"
            last_10.append({
                'week': wk,
                'percentage': percentage,
                'color': color,
                'no_data': False
            })
        else:
            last_10.append({
                'week': wk,
                'percentage': None,
                'color': '#aaa',
                'no_data': True
            })

    return last_10, average * 100


def get_efficiency_last_year_average(gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings):
    """Calculate efficiency average for the last year (365 days), excluding outliers.

    Returns a float percentage (0–100).
    """
    efficiency_data = rubidium_data

    if not efficiency_data:
        return 0

    today = datetime.now().date()
    one_year_ago = today - timedelta(days=365)

    # Filter data from last year
    last_year_data = []
    for record in efficiency_data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue

        if record_date >= one_year_ago and record['efficiency'] != 0:
            last_year_data.append(record['efficiency'])

    if not last_year_data:
        return 0

    # Filter outliers
    if len(last_year_data) > 3:
        mean = statistics.mean(last_year_data)
        stdev = statistics.stdev(last_year_data)
        non_outliers = [e for e in last_year_data if abs(e - mean) <= 2 * stdev]
        return statistics.mean(non_outliers) * 100 if non_outliers else 0

    return statistics.mean(last_year_data) * 100


def get_efficiency_last_3months_average(gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings):
    """Calculate efficiency average for the last 3 months (90 days), excluding outliers.

    Returns a float percentage (0–100).
    """
    efficiency_data = rubidium_data

    if not efficiency_data:
        return 0

    today = datetime.now().date()
    three_months_ago = today - timedelta(days=90)

    # Filter data from last 3 months
    last_3months_data = []
    for record in efficiency_data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue

        if record_date >= three_months_ago and record['efficiency'] != 0:
            last_3months_data.append(record['efficiency'])

    if not last_3months_data:
        return 0

    # Filter outliers
    if len(last_3months_data) > 3:
        mean = statistics.mean(last_3months_data)
        stdev = statistics.stdev(last_3months_data)
        non_outliers = [e for e in last_3months_data if abs(e - mean) <= 2 * stdev]
        return statistics.mean(non_outliers) * 100 if non_outliers else 0

    return statistics.mean(last_3months_data) * 100


def get_efficiency_past_year(gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings):
    """Get efficiency data points for the past year (365 days).

    Returns a list of dicts sorted by date:
        [{'date': 'YYYY-MM-DD', 'efficiency': float_percentage}, ...]
    """
    efficiency_data = rubidium_data

    if not efficiency_data:
        return []

    today = datetime.now().date()
    one_year_ago = today - timedelta(days=365)

    past_year = []
    for record in efficiency_data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue

        if record_date >= one_year_ago:
            past_year.append({
                'date': record_date.strftime('%Y-%m-%d'),
                'efficiency': record['efficiency'] * 100  # Convert to percentage
            })

    return sorted(past_year, key=lambda x: x['date'])


def get_efficiency_all_time(gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings):
    """Get all efficiency data grouped by quarter.

    Returns a list of dicts sorted by date:
        [{'date': 'YYYY-QN', 'efficiency': float_percentage}, ...]
    """
    efficiency_data = rubidium_data

    if not efficiency_data:
        return []

    # Group by quarter
    quarterly_data = defaultdict(lambda: {'values': []})

    for record in efficiency_data:
        record_date = _to_date(record['date'])
        if record_date is None:
            continue

        year = record_date.year

        # Determine quarter based on month
        month = record_date.month
        if month <= 3:
            quarter = 1
        elif month <= 6:
            quarter = 2
        elif month <= 9:
            quarter = 3
        else:
            quarter = 4

        quarter_key = (year, quarter)
        quarterly_data[quarter_key]['values'].append(record['efficiency'] * 100)

    # Calculate average for each quarter
    result = []
    for (year, quarter), data in sorted(quarterly_data.items()):
        if data['values']:
            avg_efficiency = sum(data['values']) / len(data['values'])
            result.append({
                'date': f'{year}-Q{quarter}',
                'efficiency': avg_efficiency
            })

    return result
