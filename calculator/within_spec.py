"""
calculator/within_spec.py
--------------------------
Standalone functions for within-spec KPI calculations.

A production is "within spec" when its key metric (targetstroom, efficiency,
or output percentage) falls within the acceptable range defined in spec_settings.
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


def _is_production_in_spec(production, isotope_type, spec_settings):
    """Check if a single production record is within spec for the given isotope type.

    Uses the ranges defined in spec_settings.  Returns True/False.
    """
    if isotope_type == 'gallium':
        targetstroom = production.get('targetstroom')
        cyclotron = production.get('cyclotron', 'Philips')
        if targetstroom is None:
            return False
        ts_rounded = round(targetstroom)

        if cyclotron and str(cyclotron).upper().startswith('IBA'):
            spec = spec_settings['gallium']['iba']
        else:
            spec = spec_settings['gallium']['philips']

        return spec['min'] <= ts_rounded <= spec['max']

    elif isotope_type == 'rubidium':
        efficiency = production.get('efficiency')
        if efficiency is None:
            return False
        eff_rounded = round(efficiency)

        spec = spec_settings['rubidium']
        return spec['min'] <= eff_rounded <= spec['max']

    elif isotope_type == 'indium':
        targetstroom = production.get('targetstroom')
        cyclotron = production.get('cyclotron', 'Philips')
        if targetstroom is None:
            return False
        ts_rounded = round(targetstroom)

        if cyclotron and str(cyclotron).upper().startswith('IBA'):
            spec = spec_settings['indium']['iba']
        else:
            spec = spec_settings['indium']['philips']

        return spec['min'] <= ts_rounded <= spec['max']

    elif isotope_type == 'thallium':
        targetstroom = production.get('targetstroom')
        if targetstroom is None:
            return False
        ts_rounded = round(targetstroom)

        spec = spec_settings['thallium']
        return spec['min'] <= ts_rounded <= spec['max']

    elif isotope_type == 'iodine':
        # Both output% and targetstroom must be within spec
        output_percent = production.get('output_percent')
        targetstroom = production.get('targetstroom')

        if output_percent is None:
            return False
        output_spec = spec_settings['iodine']['within_spec']['output']
        output_ok = output_spec['min'] <= output_percent <= output_spec['max']

        if targetstroom is None:
            return False
        ts_spec = spec_settings['iodine']['within_spec']['targetstroom']
        targetstroom_ok = ts_spec['min'] <= targetstroom <= ts_spec['max']

        return output_ok and targetstroom_ok

    return False


def calculate_within_spec_percentage(gallium_data, rubidium_data, indium_data,
                                     thallium_data, iodine_data, spec_settings):
    """Calculate percentage of productions within spec for each Friday-Thursday week.

    Returns a list of dicts (most-recent week first), each with keys:
        year, week, percentage, total, within_spec, friday, thursday, dates, date_str
    """
    all_productions = []
    isotope_datasets = [
        (gallium_data,  'gallium',  'Gallium'),
        (rubidium_data, 'rubidium', 'Rubidium'),
        (indium_data,   'indium',   'Indium'),
        (thallium_data, 'thallium', 'Thallium'),
        (iodine_data,   'iodine',   'Iodine'),
    ]
    bad_years = set()
    for data, spec_key, label in isotope_datasets:
        for record in data:
            d = _to_date(record['date'])
            if d is None:
                continue
            if not (1900 <= d.year <= 3000):
                bad_years.add(d.year)
                continue
            within_spec = _is_production_in_spec(record, spec_key, spec_settings)
            all_productions.append({
                'date': d,
                'isotope': label,
                'within_spec': within_spec,
            })
    if bad_years:
        print(f"[WARNING] Skipped production record(s) with unrealistic year(s): {sorted(bad_years)}")

    # Group by week (Friday-Thursday; key = start-of-week Friday date)
    weekly_data = defaultdict(lambda: {'total': 0, 'within_spec': 0, 'dates': [], 'friday': None})

    for prod in all_productions:
        if prod['date'] is None:
            continue

        days_since_friday = (prod['date'].weekday() - 4) % 7
        week_start_friday = prod['date'] - timedelta(days=days_since_friday)

        if not (1900 <= week_start_friday.year <= 3000):
            continue

        week_key = week_start_friday

        if weekly_data[week_key]['friday'] is None:
            weekly_data[week_key]['friday'] = week_start_friday

        weekly_data[week_key]['total'] += 1
        weekly_data[week_key]['dates'].append((prod['date'], prod['isotope'], prod['within_spec']))
        if prod['within_spec']:
            weekly_data[week_key]['within_spec'] += 1

    # Build result list sorted most-recent first
    weekly_percentages = []
    for friday, data in sorted(weekly_data.items(), reverse=True):
        if data['total'] > 0:
            thursday = friday + timedelta(days=6)
            iso_year, iso_week, _ = thursday.isocalendar()

            if iso_year < 1900 or iso_year > 3000:
                continue

            percentage = (data['within_spec'] / data['total']) * 100
            weekly_percentages.append({
                'year': iso_year,
                'week': iso_week,
                'percentage': percentage,
                'total': data['total'],
                'within_spec': data['within_spec'],
                'friday': friday,
                'thursday': thursday,
                'dates': data['dates'],
                'date_str': f'{iso_year}-W{iso_week:02d}'
            })

    return weekly_percentages


def get_within_spec_weeks(gallium_data, rubidium_data, indium_data,
                          thallium_data, iodine_data, spec_settings):
    """Get last 10 weeks of within-spec percentages with green/red color coding.

    Returns (last_10, average) where last_10 is a list of dicts with keys
    'week', 'percentage', 'color', 'no_data'.
    """
    weekly_data = calculate_within_spec_percentage(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )

    if not weekly_data:
        return [], 0

    # All-time average, excluding weeks below 10%
    valid_percentages = [w['percentage'] for w in weekly_data if w['percentage'] >= 10.0]
    average = statistics.mean(valid_percentages) if valid_percentages else 0

    # Build lookup: (year, week) -> percentage
    week_lookup = {(r['year'], r['week']): r['percentage'] for r in weekly_data}

    # Generate fixed last 10 production weeks using Thursday-based ISO week
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7
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
            percentage = week_lookup[(yr, wk)]
            color = "#3BB143" if percentage >= average else "#FF2400"
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

    return last_10, average


def _within_spec_average_since(days, gallium_data, rubidium_data, indium_data,
                                thallium_data, iodine_data, spec_settings):
    """Return average within-spec percentage for weeks within the last *days* days (min 10% filter)."""
    weekly_data = calculate_within_spec_percentage(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )
    if not weekly_data:
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    percentages = []
    for w in weekly_data:
        try:
            week_date = datetime.combine(date.fromisocalendar(w['year'], w['week'], 1), datetime.min.time())
            if week_date >= cutoff and w['percentage'] >= 10.0:
                percentages.append(w['percentage'])
        except (ValueError, TypeError):
            continue
    return statistics.mean(percentages) if percentages else 0


def get_within_spec_last_year_average(gallium_data, rubidium_data, indium_data,
                                      thallium_data, iodine_data, spec_settings):
    """Calculate within-spec average for the last year (365 days).

    Returns a float percentage (0–100).
    """
    return _within_spec_average_since(
        365, gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )


def get_within_spec_last_3months_average(gallium_data, rubidium_data, indium_data,
                                         thallium_data, iodine_data, spec_settings):
    """Calculate within-spec average for the last 3 months (90 days).

    Returns a float percentage (0–100).
    """
    return _within_spec_average_since(
        90, gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )


def get_within_spec_past_year(gallium_data, rubidium_data, indium_data,
                               thallium_data, iodine_data, spec_settings):
    """Get within-spec weekly data for the past year (365 days).

    Returns a list of week dicts sorted by (year, week), each containing the
    same keys produced by calculate_within_spec_percentage.
    """
    weekly_data = calculate_within_spec_percentage(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)

    past_year = []
    for w in weekly_data:
        try:
            week_date = datetime.combine(date.fromisocalendar(w['year'], w['week'], 1), datetime.min.time())
            if week_date >= one_year_ago:
                past_year.append(w)
        except Exception:
            continue

    return sorted(past_year, key=lambda x: (x['year'], x['week']))


def get_within_spec_all_time(gallium_data, rubidium_data, indium_data,
                              thallium_data, iodine_data, spec_settings):
    """Get all within-spec data grouped by quarter from 2010 onwards.

    Returns a list of dicts sorted by date:
        [{'year': int, 'quarter': int, 'percentage': float, 'date_str': 'YYYY-QN'}, ...]
    """
    weekly_data = calculate_within_spec_percentage(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )

    # Group by quarter (Q1: weeks 1–13, Q2: 14–26, Q3: 27–39, Q4: 40–52/53)
    quarterly_data = defaultdict(lambda: {'total': 0, 'within_spec': 0})

    for w in weekly_data:
        if w['year'] < 2010:
            continue

        if w['week'] <= 13:
            quarter = 1
        elif w['week'] <= 26:
            quarter = 2
        elif w['week'] <= 39:
            quarter = 3
        else:
            quarter = 4

        quarter_key = (w['year'], quarter)
        quarterly_data[quarter_key]['total'] += w['total']
        quarterly_data[quarter_key]['within_spec'] += w['within_spec']

    result = []
    for (year, quarter), data in sorted(quarterly_data.items()):
        if data['total'] > 0:
            percentage = (data['within_spec'] / data['total']) * 100
            result.append({
                'year': year,
                'quarter': quarter,
                'percentage': percentage,
                'date_str': f'{year}-Q{quarter}'
            })

    return result
