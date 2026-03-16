"""
calculator/shift_stats.py
--------------------------
Standalone functions for shift-level production statistics.

Productions are assigned proportionally to shifts (ochtenddienst 07–15,
middagdienst 15–23, nachtdienst 23–07) based on how many hours of beam
time fell within each shift window.
"""

from collections import defaultdict
from datetime import datetime, timedelta, date, time as dt_time


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_date(d):
    """Normalise any date/datetime/str value to a datetime.date, or None."""
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


def _parse_time_field(time_field):
    """Parse various time field formats to (hours, minutes) tuple, or None."""
    if time_field is None:
        return None

    try:
        if hasattr(time_field, 'hour'):
            return (time_field.hour, time_field.minute)

        if isinstance(time_field, float):
            hours = int(time_field)
            fraction = time_field - hours
            minutes = int(round(fraction * 100))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return (hours, minutes)
            return None

        time_str = str(time_field).strip()
        if len(time_str) > 10:
            return None

        if '.' in time_str:
            parts = time_str.split('.')
            if len(parts) == 2:
                try:
                    hours = int(float(parts[0]))
                    minutes = int(float(parts[1]))
                    if 0 <= hours <= 23 and 0 <= minutes <= 59:
                        return (hours, minutes)
                except (ValueError, OverflowError):
                    return None

        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                try:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    if 0 <= hours <= 23 and 0 <= minutes <= 59:
                        return (hours, minutes)
                except (ValueError, OverflowError):
                    return None

        if time_str.isdigit() and len(time_str) in [3, 4]:
            time_str = time_str.zfill(4)
            try:
                hours = int(time_str[:2])
                minutes = int(time_str[2:])
                if 0 <= hours <= 23 and 0 <= minutes <= 59:
                    return (hours, minutes)
            except (ValueError, OverflowError):
                return None

    except (ValueError, OverflowError):
        return None
    except Exception as e:
        print(f"Warning: Could not parse time field '{time_field}': {e}")
        return None

    return None


def _parse_time_duration(duration_str):
    """Parse HH.MM format to total decimal hours.

    Format: HH.MM where MM is actual minutes (0-59), not decimal.
    Examples:
      - 9.05  = 9 hours  5 minutes  = 9.0833 hours
      - 12.30 = 12 hours 30 minutes = 12.5   hours
      - 10.45 = 10 hours 45 minutes = 10.75  hours
    """
    if duration_str is None or duration_str == '':
        return 0

    try:
        duration_str = str(duration_str).strip()

        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 2:
                hours = float(parts[0])
                minutes = float(parts[1])
                return hours + (minutes / 60.0)

        if '.' in duration_str:
            parts = duration_str.split('.')
            if len(parts) == 2:
                hours = float(parts[0])
                minute_str = parts[1].ljust(2, '0')
                minutes = float(minute_str)
                return hours + (minutes / 60.0)

        return float(duration_str)

    except Exception as e:
        print(f"Warning: Could not parse duration '{duration_str}': {e}")
        return 0


def _is_production_in_spec(production, isotope_type, spec_settings):
    """Return True if the production record passes spec for the given isotope."""
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


def _get_bestraling_timing(production, isotope_type):
    """Return (start_dt, end_dt) datetimes for a bestraling record, or (None, None)."""
    try:
        if isotope_type in ['gallium', 'indium', 'thallium', 'rubidium']:
            eob_date = production.get('date')
            if eob_date is None:
                return None, None

            if isinstance(eob_date, str):
                eob_date = datetime.strptime(eob_date, '%Y-%m-%d').date()
            elif isinstance(eob_date, datetime):
                eob_date = eob_date.date()

            duur = production.get('duur')
            if duur is None:
                return None, None

            hours = _parse_time_duration(duur)
            if hours is None:
                return None, None

            eob_time_field = production.get('eobhrmin') or production.get('eob_tijd')
            if eob_time_field is None:
                end_dt = datetime.combine(eob_date, datetime.min.time()) + timedelta(hours=23, minutes=59)
            else:
                time_tuple = _parse_time_field(eob_time_field)
                if time_tuple:
                    h, m = time_tuple
                    end_dt = datetime.combine(eob_date, datetime.min.time()) + timedelta(hours=h, minutes=m)
                else:
                    end_dt = datetime.combine(eob_date, datetime.min.time()) + timedelta(hours=23, minutes=59)

            start_dt = end_dt - timedelta(hours=hours)
            return start_dt, end_dt

        elif isotope_type == 'iodine':
            stop_date = production.get('stop_datum')
            stop_time = production.get('stop_tijd')
            total_time = production.get('totale_bestralingstijd')
            storing_time = production.get('totale_storingstijd', 0)

            if stop_date is None or stop_time is None or total_time is None:
                return None, None

            if isinstance(stop_date, datetime):
                stop_date = stop_date.date()
            elif isinstance(stop_date, str):
                try:
                    stop_date = datetime.strptime(stop_date, '%Y-%m-%d').date()
                except Exception:
                    return None, None

            time_tuple = _parse_time_field(stop_time)
            if time_tuple:
                h, m = time_tuple
                end_dt = datetime.combine(stop_date, datetime.min.time()) + timedelta(hours=h, minutes=m)
            else:
                end_dt = datetime.combine(stop_date, datetime.min.time()) + timedelta(hours=23, minutes=59)

            total_hours = _parse_time_duration(total_time)
            storing_hours = _parse_time_duration(storing_time) if storing_time else 0

            if total_hours is None:
                return None, None

            duration_hours = total_hours + (storing_hours or 0)
            start_dt = end_dt - timedelta(hours=duration_hours)

            return start_dt, end_dt

    except Exception:
        return None, None

    return None, None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def calculate_shift_overlap(start_dt, end_dt, shift_name):
    """Calculate total hours of overlap between a bestraling and a named shift.

    Iterates day-by-day over the production window.

    Args:
        start_dt: datetime start of the bestraling.
        end_dt:   datetime end of the bestraling.
        shift_name: one of 'ochtenddienst', 'middagdienst', 'nachtdienst'.

    Returns:
        float hours of overlap.
    """
    total_overlap = 0
    current_dt = start_dt

    shifts = {
        'ochtenddienst': (7, 15),
        'middagdienst':  (15, 23),
        'nachtdienst':   (23, 7)
    }

    shift_start_hour, shift_end_hour = shifts[shift_name]

    while current_dt < end_dt:
        day_end = datetime.combine(current_dt.date(), datetime.min.time()) + timedelta(days=1)
        segment_end = min(end_dt, day_end)

        if shift_name == 'nachtdienst':
            shift_start = datetime.combine(current_dt.date(), datetime.min.time()) + timedelta(hours=shift_start_hour)
            shift_end   = datetime.combine(current_dt.date(), datetime.min.time()) + timedelta(days=1, hours=shift_end_hour)
        else:
            shift_start = datetime.combine(current_dt.date(), datetime.min.time()) + timedelta(hours=shift_start_hour)
            shift_end   = datetime.combine(current_dt.date(), datetime.min.time()) + timedelta(hours=shift_end_hour)

        overlap_start = max(current_dt, shift_start)
        overlap_end   = min(segment_end, shift_end)

        if overlap_start < overlap_end:
            overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
            total_overlap += overlap_hours

        current_dt = day_end

    return total_overlap


def _calculate_shift_overlaps(start_dt, end_dt):
    """Return a list of (date, shift_name, hours) tuples for all shifts the
    bestraling window touches.

    Night shift belongs to the date it starts (23:00).  The scan begins one
    day before start_dt to catch productions whose early hours fall in a night
    shift that started the previous evening.
    """
    overlaps = []

    current_date = start_dt.date() - timedelta(days=1)
    end_date = end_dt.date()

    while current_date <= end_date + timedelta(days=1):
        ochtend_start = datetime.combine(current_date, dt_time(7, 0))
        ochtend_end   = datetime.combine(current_date, dt_time(15, 0))

        middag_start  = datetime.combine(current_date, dt_time(15, 0))
        middag_end    = datetime.combine(current_date, dt_time(23, 0))

        nacht_start   = datetime.combine(current_date, dt_time(23, 0))
        nacht_end     = datetime.combine(current_date + timedelta(days=1), dt_time(7, 0))

        for shift_name, shift_start, shift_end in [
            ('ochtenddienst', ochtend_start, ochtend_end),
            ('middagdienst',  middag_start,  middag_end),
            ('nachtdienst',   nacht_start,   nacht_end),
        ]:
            overlap_start = max(start_dt, shift_start)
            overlap_end   = min(end_dt,   shift_end)

            if overlap_start < overlap_end:
                overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                if overlap_hours > 0:
                    overlaps.append((current_date, shift_name, overlap_hours))

        current_date += timedelta(days=1)

    return overlaps


def calculate_shift_statistics(gallium_data, rubidium_data, indium_data, thallium_data,
                                iodine_data, ploegen_data, planning_data,
                                ploegenwissel_date, spec_settings, week_start_friday):
    """Calculate proportional in-spec credit per shift per day for a single week.

    Args:
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data:
            Lists of production records for each isotope.
        ploegen_data:       Dict mapping first-two-letter codes to ploeg info.
        planning_data:      Dict mapping date objects to shift lead persons.
        ploegenwissel_date: date from which the current ploeg schedule is valid.
        spec_settings:      SPEC_SETTINGS dict.
        week_start_friday:  The Friday (date) that opens the week to analyse.

    Returns:
        defaultdict[date][shift_name] -> {'total': float, 'in_spec': float}
    """
    stats = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0}))
    week_end = week_start_friday + timedelta(days=6)

    for isotope_type, data_list in [
        ('gallium',  gallium_data),
        ('rubidium', rubidium_data),
        ('indium',   indium_data),
        ('thallium', thallium_data),
        ('iodine',   iodine_data),
    ]:
        for production in data_list:
            start_dt, end_dt = _get_bestraling_timing(production, isotope_type)
            if start_dt is None or end_dt is None:
                continue

            total_duration_hours = (end_dt - start_dt).total_seconds() / 3600
            if total_duration_hours <= 0:
                continue

            in_spec = _is_production_in_spec(production, isotope_type, spec_settings)
            overlaps = _calculate_shift_overlaps(start_dt, end_dt)

            for day_date, shift_name, overlap_hours in overlaps:
                if not (week_start_friday <= day_date <= week_end):
                    continue

                proportion = overlap_hours / total_duration_hours
                stats[day_date][shift_name]['total'] += proportion
                if in_spec:
                    stats[day_date][shift_name]['in_spec'] += proportion

    return stats


def calculate_shift_statistics_all_time(gallium_data, rubidium_data, indium_data,
                                         thallium_data, iodine_data, ploegen_data,
                                         planning_data, ploegenwissel_date,
                                         spec_settings, lookback_date):
    """Single-pass equivalent of calling calculate_shift_statistics for every week
    in the lookback window.  Iterates each production exactly once.

    Args:
        (same isotope/ploeg/planning args as calculate_shift_statistics)
        lookback_date: earliest date (inclusive) to include in the result.

    Returns:
        defaultdict[date][shift_name] -> {'total': float, 'in_spec': float}
    """
    stats = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0}))

    lookback_dt = (
        datetime.combine(lookback_date, datetime.min.time())
        if hasattr(lookback_date, 'year')
        else lookback_date
    )

    for isotope_type, data_list in [
        ('gallium',  gallium_data),
        ('rubidium', rubidium_data),
        ('indium',   indium_data),
        ('thallium', thallium_data),
        ('iodine',   iodine_data),
    ]:
        for production in data_list:
            start_dt, end_dt = _get_bestraling_timing(production, isotope_type)
            if start_dt is None or end_dt is None:
                continue

            if end_dt < lookback_dt:
                continue

            total_duration_hours = (end_dt - start_dt).total_seconds() / 3600
            if total_duration_hours <= 0:
                continue

            in_spec = _is_production_in_spec(production, isotope_type, spec_settings)
            overlaps = _calculate_shift_overlaps(start_dt, end_dt)

            for day_date, shift_name, overlap_hours in overlaps:
                if day_date < lookback_date:
                    continue

                proportion = overlap_hours / total_duration_hours
                stats[day_date][shift_name]['total'] += proportion
                if in_spec:
                    stats[day_date][shift_name]['in_spec'] += proportion

    return stats


def get_production_history(gallium_data, rubidium_data, indium_data,
                            thallium_data, iodine_data):
    """Build a simple chronological list of all production records across isotopes.

    Each entry contains the isotope name, the production date, and the raw
    record dict so callers can render or further process it.

    Returns:
        List of dicts sorted by date:
            [{'date': 'YYYY-MM-DD', 'isotope': str, 'record': dict}, ...]
    """
    history = []

    isotope_datasets = [
        (gallium_data,  'gallium'),
        (rubidium_data, 'rubidium'),
        (indium_data,   'indium'),
        (thallium_data, 'thallium'),
        (iodine_data,   'iodine'),
    ]

    for data_list, isotope_name in isotope_datasets:
        for record in data_list:
            d = _to_date(record.get('date'))
            if d is None:
                continue
            history.append({
                'date': d.strftime('%Y-%m-%d'),
                'isotope': isotope_name,
                'record': record,
            })

    return sorted(history, key=lambda x: x['date'])
