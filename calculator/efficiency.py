"""
calculator/efficiency.py
------------------------
Standalone functions for efficiency KPI calculations.

Contains two types of efficiency:

1. Cyclotron current efficiency (%) — derived from Rubidium data
   (``get_efficiency_weeks`` and friends).

2. Per-isotope production efficiency (mCi/µAh) — how much activity
   is produced per unit of beam charge, calculated from bestralingen +
   opbrengsten data (``calculate_*_production_efficiency`` and friends).
"""

import bisect
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
    valid_data = [d for d in efficiency_data if d['efficiency'] is not None and d['efficiency'] != 0]

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

        if record_date >= one_year_ago and record['efficiency'] is not None and record['efficiency'] != 0:
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

        if record_date >= three_months_ago and record['efficiency'] is not None and record['efficiency'] != 0:
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

        if record_date >= one_year_ago and record['efficiency'] is not None:
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
        if record_date is None or record['efficiency'] is None:
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


# ============================================================================
# Per-isotope production efficiency (mCi/µAh)
# ============================================================================

def _parse_duur_hours(duur) -> float:
    """Convert a Duur value (HH.MM float/string) to decimal hours."""
    if duur is None:
        return 0.0
    try:
        s = str(duur).strip()
        if '.' in s:
            h, m = s.split('.', 1)
            return float(h) + float(m.ljust(2, '0')) / 60.0
        return float(s)
    except Exception:
        return 0.0


def _get_friday_week(d: date) -> date:
    """Return the Friday that starts the Friday-Thursday week containing *d*."""
    return d - timedelta(days=(d.weekday() - 4) % 7)


def _week_result(weekly_data: dict) -> list:
    """Convert weekly_data dict to sorted list of dicts with week_number + friday."""
    result = []
    for friday, info in sorted(weekly_data.items(), reverse=True):
        if info['efficiencies']:
            avg = sum(info['efficiencies']) / len(info['efficiencies'])
            monday = friday + timedelta(days=3)
            _, iso_week, _ = monday.isocalendar()
            result.append({'friday': friday, 'week_number': iso_week, 'efficiency': avg})
    return result


def _efficiency_averages(all_weeks: list) -> tuple:
    """Return (all_time_avg, past_year_avg, past_3months_avg) from a weeks list."""
    if not all_weeks:
        return 0.0, 0.0, 0.0
    today          = datetime.now().date()
    one_year_ago   = today - timedelta(days=365)
    three_months_ago = today - timedelta(days=90)

    all_effs  = [w['efficiency'] for w in all_weeks]
    all_time  = sum(all_effs) / len(all_effs)

    yr_effs   = [w['efficiency'] for w in all_weeks if w['friday'] >= one_year_ago]
    past_year = sum(yr_effs) / len(yr_effs) if yr_effs else 0.0

    m3_effs     = [w['efficiency'] for w in all_weeks if w['friday'] >= three_months_ago]
    past_3months = sum(m3_effs) / len(m3_effs) if m3_effs else 0.0

    return all_time, past_year, past_3months


def _efficiency_weeks_result(all_weeks: list) -> tuple:
    """Return (last_10_weeks_with_color, overall_avg) for dashboard tables."""
    if not all_weeks:
        return [], 0.0
    all_effs    = [w['efficiency'] for w in all_weeks]
    overall_avg = sum(all_effs) / len(all_effs)
    last_10     = all_weeks[:10]
    result = []
    for w in last_10:
        diff = w['efficiency'] - overall_avg
        color = '#3BB143' if diff > 0.05 else ('#FF2400' if diff < -0.05 else '#000000')
        result.append({'week': w['week_number'], 'efficiency': w['efficiency'], 'color': color})
    return result, overall_avg


# ---------------------------------------------------------------------------
# Gallium mCi/µAh
# ---------------------------------------------------------------------------

def calculate_gallium_production_efficiency(gallium_data: list,
                                            gallium_opbrengsten_data: list) -> list:
    """Calculate Gallium production efficiency (mCi/µAh) per week."""
    parsed_opb = []
    for opb in gallium_opbrengsten_data:
        d = _to_date(opb['date'])
        if d:
            parsed_opb.append((d, opb))
    parsed_opb.sort(key=lambda x: x[0])
    opb_dates = [x[0] for x in parsed_opb]

    weekly: dict = defaultdict(lambda: {'efficiencies': []})
    for bestraling in gallium_data:
        eob_date = _to_date(bestraling['date'])
        if eob_date is None:
            continue
        idx = bisect.bisect_right(opb_dates, eob_date)
        if idx >= len(parsed_opb):
            continue
        opb = parsed_opb[idx][1]
        ts  = bestraling.get('targetstroom')
        duur = bestraling.get('duur')
        mbq  = opb.get('opbrengst_mbq')
        if ts is None or duur is None or mbq is None:
            continue
        hours = _parse_duur_hours(duur)
        uah = ts * hours
        if uah <= 0:
            continue
        eff = (mbq / 37.0) / uah
        friday = _get_friday_week(eob_date)
        weekly[friday]['efficiencies'].append(eff)

    return _week_result(weekly)


def get_gallium_efficiency_weeks(gallium_data, gallium_opbrengsten_data) -> tuple:
    all_weeks = calculate_gallium_production_efficiency(gallium_data, gallium_opbrengsten_data)
    return _efficiency_weeks_result(all_weeks)


def get_gallium_efficiency_averages(gallium_data, gallium_opbrengsten_data) -> tuple:
    return _efficiency_averages(
        calculate_gallium_production_efficiency(gallium_data, gallium_opbrengsten_data))


# ---------------------------------------------------------------------------
# Indium mCi/µAh
# ---------------------------------------------------------------------------

def calculate_indium_production_efficiency(indium_data: list,
                                           indium_opbrengsten_data: list) -> list:
    """Calculate Indium production efficiency (mCi/µAh) per week."""
    parsed_opb = []
    for opb in indium_opbrengsten_data:
        d = _to_date(opb['date'])
        if d:
            parsed_opb.append((d, opb))
    parsed_opb.sort(key=lambda x: x[0])
    opb_dates = [x[0] for x in parsed_opb]

    weekly: dict = defaultdict(lambda: {'efficiencies': []})
    for bestraling in indium_data:
        eob_date = _to_date(bestraling['date'])
        if eob_date is None:
            continue
        idx = bisect.bisect_right(opb_dates, eob_date)
        if idx >= len(parsed_opb):
            continue
        opb  = parsed_opb[idx][1]
        ts   = bestraling.get('targetstroom')
        duur = bestraling.get('duur')
        mbq  = opb.get('opbrengst_mbq')
        if ts is None or duur is None or mbq is None:
            continue
        hours = _parse_duur_hours(duur)
        uah = ts * hours
        if uah <= 0:
            continue
        eff = (mbq / 37.0) / uah
        friday = _get_friday_week(eob_date)
        weekly[friday]['efficiencies'].append(eff)

    return _week_result(weekly)


def get_indium_efficiency_weeks(indium_data, indium_opbrengsten_data) -> tuple:
    all_weeks = calculate_indium_production_efficiency(indium_data, indium_opbrengsten_data)
    return _efficiency_weeks_result(all_weeks)


def get_indium_efficiency_averages(indium_data, indium_opbrengsten_data) -> tuple:
    return _efficiency_averages(
        calculate_indium_production_efficiency(indium_data, indium_opbrengsten_data))


# ---------------------------------------------------------------------------
# Rubidium mCi/µAh (3–6 hour productions only)
# ---------------------------------------------------------------------------

def calculate_rubidium_production_efficiency(rubidium_data: list) -> list:
    """Calculate Rubidium production efficiency (mCi/µAh) — 3–6 h productions."""
    weekly: dict = defaultdict(lambda: {'efficiencies': []})
    for record in rubidium_data:
        d = _to_date(record['date'])
        if d is None:
            continue
        stroom = record.get('stroom')
        duur   = record.get('duur')
        mbq    = record.get('value1')
        if stroom is None or duur is None or mbq is None:
            continue
        hours = _parse_duur_hours(duur)
        if not (3 <= hours <= 6):
            continue
        uah = stroom * hours
        if uah <= 0:
            continue
        eff = (mbq / 37.0) / uah
        friday = _get_friday_week(d)
        weekly[friday]['efficiencies'].append(eff)

    return _week_result(weekly)


def get_rubidium_efficiency_weeks(rubidium_data) -> tuple:
    all_weeks = calculate_rubidium_production_efficiency(rubidium_data)
    return _efficiency_weeks_result(all_weeks)


def get_rubidium_efficiency_averages(rubidium_data) -> tuple:
    return _efficiency_averages(calculate_rubidium_production_efficiency(rubidium_data))


# ---------------------------------------------------------------------------
# Iodine mCi/µAh (≥10 beam-hour productions only)
# ---------------------------------------------------------------------------

def calculate_iodine_production_efficiency(iodine_data: list) -> list:
    """Calculate Iodine production efficiency (mCi/µAh) — ≥10 beam-hour runs."""
    weekly: dict = defaultdict(lambda: {'efficiencies': []})
    for record in iodine_data:
        d = _to_date(record['date'])
        if d is None:
            continue
        totale_dosis = record.get('totale_dosis')
        targetstroom = record.get('targetstroom')
        meting_d1    = record.get('meting_d1')
        meting_waste = record.get('meting_waste')
        if any(v is None for v in (totale_dosis, targetstroom, meting_d1, meting_waste)):
            continue
        if targetstroom <= 0:
            continue
        beam_hours = totale_dosis / targetstroom
        if beam_hours < 10:
            continue
        uah = totale_dosis
        total_mbq = meting_d1 + meting_waste
        if uah <= 0:
            continue
        eff = (total_mbq / 37.0) / uah
        friday = _get_friday_week(d)
        weekly[friday]['efficiencies'].append(eff)

    return _week_result(weekly)


def get_iodine_efficiency_weeks(iodine_data) -> tuple:
    all_weeks = calculate_iodine_production_efficiency(iodine_data)
    return _efficiency_weeks_result(all_weeks)


def get_iodine_efficiency_averages(iodine_data) -> tuple:
    return _efficiency_averages(calculate_iodine_production_efficiency(iodine_data))
