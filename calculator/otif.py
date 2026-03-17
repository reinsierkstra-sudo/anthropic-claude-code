"""
calculator/otif.py
-------------------
Standalone functions for OTIF (On Time In Full) gedraaide producties KPI calculations.

OTIF gedraaide producties measures how close each production's actual targetstroom was
to its nominal value, expressed as a percentage.  Only actual production records are
used — no changelog data.
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, date


def _get_friday_week(d):
    """Return the Friday that starts the Friday-Thursday week containing date d."""
    return d - timedelta(days=(d.weekday() - 4) % 7)


def _parse_date(d):
    """Convert date/datetime/str to datetime.date, or None on failure."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if hasattr(d, 'year') and not isinstance(d, datetime):
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(d, '%Y-%m-%d').date()
        except Exception:
            return None
    return None


def calculate_otif_gedraaide_producties(gallium_data, rubidium_data, indium_data,
                                        thallium_data, iodine_data, spec_settings):
    """Calculate OTIF percentage per week based on actual vs nominal targetstroom for all isotopes.

    Nominal values are derived from the midpoints of the SPEC_SETTINGS min/max ranges.

    Returns a list of dicts (most-recent week first):
        [{'year': int, 'week': int, 'percentage': float, 'friday': date}, ...]
    """
    ga_philips_nominal = (spec_settings['gallium']['philips']['min'] + spec_settings['gallium']['philips']['max']) / 2  # 80
    ga_iba_nominal     = (spec_settings['gallium']['iba']['min']    + spec_settings['gallium']['iba']['max'])    / 2  # 135
    in_philips_nominal = (spec_settings['indium']['philips']['min'] + spec_settings['indium']['philips']['max']) / 2  # 80
    in_iba_nominal     = (spec_settings['indium']['iba']['min']     + spec_settings['indium']['iba']['max'])     / 2  # 135
    tl_nominal         = (spec_settings['thallium']['min']          + spec_settings['thallium']['max'])          / 2  # 170
    rb_nominal         = 70.0  # µA

    # Collect actual productions per (friday_week, isotope)
    weekly_actuals = defaultdict(lambda: defaultdict(list))

    # Gallium
    for record in gallium_data:
        d = _parse_date(record.get('date'))
        if d is None:
            continue
        ts = record.get('targetstroom')
        if ts is None:
            pct = 0.0
        else:
            nominal = ga_iba_nominal if str(record.get('cyclotron', '')).upper().startswith('IBA') else ga_philips_nominal
            pct = (ts / nominal) * 100.0
        weekly_actuals[_get_friday_week(d)]['gallium'].append(pct)

    # Indium
    for record in indium_data:
        d = _parse_date(record.get('date'))
        if d is None:
            continue
        ts = record.get('targetstroom')
        if ts is None:
            pct = 0.0
        else:
            nominal = in_iba_nominal if str(record.get('cyclotron', '')).upper().startswith('IBA') else in_philips_nominal
            pct = (ts / nominal) * 100.0
        weekly_actuals[_get_friday_week(d)]['indium'].append(pct)

    # Thallium
    for record in thallium_data:
        d = _parse_date(record.get('date'))
        if d is None:
            continue
        ts = record.get('targetstroom')
        if ts is None:
            pct = 0.0
        else:
            pct = (ts / tl_nominal) * 100.0
        weekly_actuals[_get_friday_week(d)]['thallium'].append(pct)

    # Iodine
    for record in iodine_data:
        d = _parse_date(record.get('date'))
        if d is None:
            continue
        bo_ts = record.get('bo_targetstroom')
        ts    = record.get('targetstroom')
        if bo_ts is None or ts is None:
            pct = 0.0
        else:
            pct = (ts / bo_ts) * 100.0
        weekly_actuals[_get_friday_week(d)]['iodine'].append(pct)

    # Rubidium
    for record in rubidium_data:
        d = _parse_date(record.get('date'))
        if d is None:
            continue
        stroom = record.get('stroom')
        if stroom is None:
            pct = 0.0
        else:
            pct = (stroom / rb_nominal) * 100.0
        weekly_actuals[_get_friday_week(d)]['rubidium'].append(pct)

    # Compute weekly average from actuals only
    result = []
    for friday in sorted(weekly_actuals.keys(), reverse=True):
        all_pcts = []
        for isotope_pcts in weekly_actuals[friday].values():
            all_pcts.extend(isotope_pcts)

        if not all_pcts:
            continue

        thursday = friday + timedelta(days=6)
        iso_year, iso_week, _ = thursday.isocalendar()
        if iso_year < 1900 or iso_year > 3000:
            continue

        result.append({
            'year': iso_year,
            'week': iso_week,
            'percentage': sum(all_pcts) / len(all_pcts),
            'friday': friday,
        })

    return result


def get_otif_gedraaide_weeks(gallium_data, rubidium_data, indium_data,
                              thallium_data, iodine_data, spec_settings):
    """Get last 10 weeks of OTIF gedraaide producties with green/red color coding.

    Color is green when percentage >= 97, red otherwise.

    Returns (last_10, average) where last_10 is a list of dicts with keys
    'week', 'percentage', 'color', 'no_data'.
    """
    weekly_data = calculate_otif_gedraaide_producties(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )
    if not weekly_data:
        return [], 0

    all_pcts = [w['percentage'] for w in weekly_data]
    average = statistics.mean(all_pcts) if all_pcts else 0

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
            color = '#3BB143' if percentage >= 97 else '#FF2400'
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


def get_otif_gedraaide_last_year_average(gallium_data, rubidium_data, indium_data,
                                          thallium_data, iodine_data, spec_settings):
    """Calculate OTIF gedraaide average for the last year (365 days).

    Returns a float percentage (0–100+).
    """
    weekly_data = calculate_otif_gedraaide_producties(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )
    if not weekly_data:
        return 0

    one_year_ago = datetime.now() - timedelta(days=365)
    pcts = []
    for w in weekly_data:
        try:
            week_date = datetime.combine(date.fromisocalendar(w['year'], w['week'], 1), datetime.min.time())
            if week_date >= one_year_ago:
                pcts.append(w['percentage'])
        except Exception:
            continue
    return statistics.mean(pcts) if pcts else 0


def get_otif_gedraaide_last_3months_average(gallium_data, rubidium_data, indium_data,
                                             thallium_data, iodine_data, spec_settings):
    """Calculate OTIF gedraaide average for the last 3 months (90 days).

    Returns a float percentage (0–100+).
    """
    weekly_data = calculate_otif_gedraaide_producties(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data, spec_settings
    )
    if not weekly_data:
        return 0

    three_months_ago = datetime.now() - timedelta(days=90)
    pcts = []
    for w in weekly_data:
        try:
            week_date = datetime.combine(date.fromisocalendar(w['year'], w['week'], 1), datetime.min.time())
            if week_date >= three_months_ago:
                pcts.append(w['percentage'])
        except Exception:
            continue
    return statistics.mean(pcts) if pcts else 0
