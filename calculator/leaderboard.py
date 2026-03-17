"""
calculator/leaderboard.py
--------------------------
Standalone functions for ploeg (team) performance leaderboard calculations.

Productions are assigned proportionally to ploegen based on how many hours of
beam time each shift contributed, using planning_data to identify which ploeg
led each shift on each day.

Also provides:
- ``collect_ploeg_production_details`` — build per-ploeg production list
- ``build_production_history``         — invert to per-BO lookup
"""

from collections import defaultdict
from datetime import datetime, timedelta, date, time as dt_time
import traceback


# ---------------------------------------------------------------------------
# Internal helpers (duplicated from shift_stats to keep modules self-contained)
# ---------------------------------------------------------------------------

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
    """Parse HH.MM format to total decimal hours."""
    if duration_str is None or duration_str == '':
        return 0
    try:
        duration_str = str(duration_str).strip()
        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 2:
                return float(parts[0]) + float(parts[1]) / 60.0
        if '.' in duration_str:
            parts = duration_str.split('.')
            if len(parts) == 2:
                hours = float(parts[0])
                minute_str = parts[1].ljust(2, '0')
                return hours + float(minute_str) / 60.0
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
    """Return (start_dt, end_dt) datetimes for a production record, or (None, None)."""
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
            duration_hours = total_hours + (storing_hours or 0)
            start_dt = end_dt - timedelta(hours=duration_hours)
            return start_dt, end_dt

    except Exception:
        return None, None

    return None, None


def _calculate_shift_overlaps(start_dt, end_dt):
    """Return list of (date, shift_name, overlap_hours) for all shifts touched."""
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


def _build_shift_stats_all_time(gallium_data, rubidium_data, indium_data,
                                  thallium_data, iodine_data, spec_settings, lookback_date):
    """Single-pass computation of per-day/per-shift proportional stats.

    Returns defaultdict[date][shift_name] -> {'total': float, 'in_spec': float}
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


def _get_ploeg_number_for_shift(day_date, shift_name, planning_data, ploegen_data):
    """Look up the ploeg number responsible for a given shift on a given date.

    Returns the integer ploeg_number, or None if not found.
    """
    if day_date not in planning_data:
        return None
    lead_person = planning_data[day_date].get(shift_name)
    if not lead_person or len(lead_person) < 2:
        return None
    first_two = lead_person[:2].upper()
    ploeg_info = ploegen_data.get(first_two)
    if ploeg_info is None:
        return None
    return ploeg_info['ploeg_number']


def _get_ploeg_name(ploeg_number, ploegen_data):
    """Return the ploeg_name string for a given ploeg_number, or None."""
    for ploeg_info in ploegen_data.values():
        if ploeg_info['ploeg_number'] == ploeg_number:
            return ploeg_info['ploeg_name']
    return None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def calculate_ploeg_leaderboard(gallium_data, rubidium_data, indium_data,
                                 thallium_data, iodine_data, ploegen_data,
                                 planning_data, ploegenwissel_date, spec_settings):
    """Calculate ploeg performance leaderboard for the past 30 days.

    Returns a list of dicts sorted by percentage descending then total descending:
        [{'ploeg_number': int, 'name': str, 'total': float,
          'in_spec': float, 'percentage': float}, ...]
    """
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)

    shift_stats = _build_shift_stats_all_time(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data,
        spec_settings, thirty_days_ago
    )

    ploeg_stats = defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0})

    for day_date, shifts in shift_stats.items():
        if day_date < thirty_days_ago:
            continue

        for shift_name in ['ochtenddienst', 'middagdienst', 'nachtdienst']:
            if shift_name not in shifts:
                continue
            stats = shifts[shift_name]
            if stats['total'] == 0:
                continue

            ploeg_number = _get_ploeg_number_for_shift(day_date, shift_name, planning_data, ploegen_data)
            if ploeg_number is None:
                continue

            ploeg_stats[ploeg_number]['total']   += stats['total']
            ploeg_stats[ploeg_number]['in_spec'] += stats['in_spec']

    leaderboard = []
    for ploeg_num, stats in ploeg_stats.items():
        if stats['total'] > 0:
            percentage = (stats['in_spec'] / stats['total']) * 100
            ploeg_name = _get_ploeg_name(ploeg_num, ploegen_data)
            if ploeg_name:
                leaderboard.append({
                    'ploeg_number': ploeg_num,
                    'name': ploeg_name,
                    'total': stats['total'],
                    'in_spec': stats['in_spec'],
                    'percentage': percentage
                })

    leaderboard.sort(key=lambda x: (x['percentage'], x['total']), reverse=True)
    return leaderboard


def calculate_ploeg_rolling_averages(gallium_data, rubidium_data, indium_data,
                                      thallium_data, iodine_data, ploegen_data,
                                      planning_data, ploegenwissel_date, spec_settings):
    """Calculate rolling 30-day within-spec percentages per ploeg over the past 6 months.

    Returns a dict mapping ploeg_number (int) to a list of dicts:
        {ploeg_number: [{'date': 'YYYY-MM-DD', 'percentage': float}, ...], ...}
    Only data points with percentage > 0 are included.
    """
    today = datetime.now().date()
    six_months_ago = today - timedelta(days=180)

    shift_stats = _build_shift_stats_all_time(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data,
        spec_settings, six_months_ago
    )

    all_dates = sorted([d for d in shift_stats.keys() if d >= six_months_ago])

    if not all_dates:
        return {}

    # Per-ploeg daily totals
    ploeg_daily = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0}))

    for day_date in all_dates:
        if day_date not in planning_data:
            continue

        shifts = shift_stats[day_date]
        for shift_name in ['ochtenddienst', 'middagdienst', 'nachtdienst']:
            if shift_name not in shifts:
                continue
            stats = shifts[shift_name]
            if stats['total'] == 0:
                continue

            ploeg_number = _get_ploeg_number_for_shift(day_date, shift_name, planning_data, ploegen_data)
            if ploeg_number is None:
                continue

            ploeg_daily[ploeg_number][day_date]['total']   += stats['total']
            ploeg_daily[ploeg_number][day_date]['in_spec'] += stats['in_spec']

    # Rolling 30-day window for each ploeg
    ploeg_rolling = {}

    for ploeg_number in sorted(ploeg_daily.keys()):
        rolling_data = []

        for current_date in all_dates:
            window_start = current_date - timedelta(days=30)

            total_in_window   = 0.0
            in_spec_in_window = 0.0

            for check_date in all_dates:
                if window_start <= check_date <= current_date:
                    if check_date in ploeg_daily[ploeg_number]:
                        total_in_window   += ploeg_daily[ploeg_number][check_date]['total']
                        in_spec_in_window += ploeg_daily[ploeg_number][check_date]['in_spec']

            if total_in_window > 0:
                percentage = (in_spec_in_window / total_in_window) * 100
                if percentage > 0:
                    rolling_data.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'percentage': round(percentage, 1)
                    })

        if rolling_data:
            ploeg_rolling[ploeg_number] = rolling_data

    return ploeg_rolling


def calculate_ploeg_statistics(gallium_data, rubidium_data, indium_data,
                                thallium_data, iodine_data, ploegen_data,
                                planning_data, ploegenwissel_date, spec_settings):
    """Calculate 6-month, 3-month, and monthly in-spec averages per ploeg.

    Returns three dicts (ploeg_stats_6month, ploeg_stats_3month, ploeg_stats_monthly),
    each mapping ploeg_number (int) to {'total': float, 'in_spec': float}.
    """
    today = datetime.now().date()
    six_months_ago   = today - timedelta(days=180)
    three_months_ago = today - timedelta(days=90)
    one_month_ago    = today - timedelta(days=30)

    shift_stats = _build_shift_stats_all_time(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data,
        spec_settings, six_months_ago
    )

    ploeg_stats_6month  = defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0})
    ploeg_stats_3month  = defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0})
    ploeg_stats_monthly = defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0})

    unmatched_count = 0

    for day_date, shifts in shift_stats.items():
        if day_date not in planning_data:
            continue

        for shift_name in ['ochtenddienst', 'middagdienst', 'nachtdienst']:
            if shift_name not in shifts:
                continue
            stats = shifts[shift_name]
            if stats['total'] == 0:
                continue

            lead_person = planning_data[day_date].get(shift_name)
            if not lead_person or len(lead_person) < 2:
                unmatched_count += 1
                continue

            first_two = lead_person[:2].upper()
            if first_two not in ploegen_data:
                unmatched_count += 1
                continue

            ploeg_number = ploegen_data[first_two]['ploeg_number']

            if day_date >= six_months_ago:
                ploeg_stats_6month[ploeg_number]['total']   += stats['total']
                ploeg_stats_6month[ploeg_number]['in_spec'] += stats['in_spec']

            if day_date >= three_months_ago:
                ploeg_stats_3month[ploeg_number]['total']   += stats['total']
                ploeg_stats_3month[ploeg_number]['in_spec'] += stats['in_spec']

            if day_date >= one_month_ago:
                ploeg_stats_monthly[ploeg_number]['total']   += stats['total']
                ploeg_stats_monthly[ploeg_number]['in_spec'] += stats['in_spec']

    if unmatched_count > 0:
        print(f"Warning: Total unmatched shifts: {unmatched_count}")

    return ploeg_stats_6month, ploeg_stats_3month, ploeg_stats_monthly


def calculate_last_month_winner(gallium_data, rubidium_data, indium_data,
                                 thallium_data, iodine_data, ploegen_data,
                                 planning_data, ploegenwissel_date, spec_settings):
    """Determine which ploeg had the highest in-spec percentage last full calendar month.

    Returns a dict with keys 'ploeg_number', 'name', 'total', 'in_spec',
    'percentage', 'month', 'year', or None if no data is available.
    """
    import calendar

    today = datetime.now().date()

    if today.month == 1:
        last_month      = 12
        last_month_year = today.year - 1
    else:
        last_month      = today.month - 1
        last_month_year = today.year

    first_day    = datetime(last_month_year, last_month, 1).date()
    last_day_num = calendar.monthrange(last_month_year, last_month)[1]
    last_day     = datetime(last_month_year, last_month, last_day_num).date()
    month_name   = calendar.month_name[last_month]

    shift_stats = _build_shift_stats_all_time(
        gallium_data, rubidium_data, indium_data, thallium_data, iodine_data,
        spec_settings, first_day
    )

    ploeg_stats = defaultdict(lambda: {'total': 0.0, 'in_spec': 0.0})

    for day_date, shifts in shift_stats.items():
        if not (first_day <= day_date <= last_day):
            continue
        if day_date not in planning_data:
            continue

        for shift_name in ['ochtenddienst', 'middagdienst', 'nachtdienst']:
            if shift_name not in shifts:
                continue
            stats = shifts[shift_name]
            if stats['total'] == 0:
                continue

            ploeg_number = _get_ploeg_number_for_shift(day_date, shift_name, planning_data, ploegen_data)
            if ploeg_number is None:
                continue

            ploeg_stats[ploeg_number]['total']   += stats['total']
            ploeg_stats[ploeg_number]['in_spec'] += stats['in_spec']

    winner          = None
    best_percentage = 0

    for ploeg_num, stats in ploeg_stats.items():
        if stats['total'] > 0:
            percentage = (stats['in_spec'] / stats['total']) * 100
            if percentage > best_percentage:
                best_percentage = percentage
                ploeg_name = _get_ploeg_name(ploeg_num, ploegen_data)
                if ploeg_name:
                    winner = {
                        'ploeg_number': ploeg_num,
                        'name':         ploeg_name,
                        'total':        stats['total'],
                        'in_spec':      stats['in_spec'],
                        'percentage':   percentage,
                        'month':        month_name,
                        'year':         last_month_year
                    }

    return winner


# ============================================================================
# collect_ploeg_production_details / build_production_history
# ============================================================================

def _to_date_lb(d):
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


def _add_production_to_ploeg(ploeg_productions, production, isotope_type,
                              start_dt, end_dt,
                              planning_data, ploegen_data, spec_settings):
    """Assign *production* proportionally to ploegen based on shift overlaps."""
    total_dur = (end_dt - start_dt).total_seconds() / 3600
    if total_dur <= 0:
        return

    from config.spec_settings import is_production_in_spec
    in_spec   = is_production_in_spec(production, isotope_type)
    overlaps  = _calculate_shift_overlaps(start_dt, end_dt)
    if not overlaps:
        return

    first_shift = True
    for _date_key, shift_name, overlap_hours in overlaps:
        proportion = overlap_hours / total_dur
        if _date_key not in planning_data:
            continue
        if shift_name not in planning_data[_date_key]:
            continue
        lead_person = planning_data[_date_key][shift_name]
        if not lead_person or len(lead_person) < 2:
            continue
        first_two = lead_person[:2].upper()
        if first_two not in ploegen_data:
            continue
        ploeg_number = ploegen_data[first_two]['ploeg_number']

        shift_code = {'ochtenddienst': 'OD', 'middagdienst': 'MD', 'nachtdienst': 'ND'}.get(
            shift_name, shift_name)

        if first_shift:
            display_time = start_dt
            first_shift = False
        else:
            shift_hour = {'ochtenddienst': 7, 'middagdienst': 15, 'nachtdienst': 23}.get(shift_name, 7)
            display_time = datetime.combine(_date_key, datetime.min.time()).replace(hour=shift_hour)

        ploeg_productions[ploeg_number].append({
            'date':       display_time.strftime('%Y-%m-%d %H:%M'),
            'shift':      shift_code,
            'isotope':    isotope_type,
            'proportion': proportion * 100,
            'in_spec':    in_spec,
            'data':       production,
            'sort_key':   display_time,
        })


def _build_eob_and_start(datum_parsed, eob_field, duur_field, fallback_hour=12):
    """Return (start_dt, eob_dt) for a bestraling record."""
    time_tuple = _parse_time_field(eob_field) if eob_field else None
    if time_tuple:
        h, m = time_tuple
        eob_dt = datetime.combine(datum_parsed, datetime.min.time()) + timedelta(hours=h, minutes=m)
    else:
        eob_dt = datetime.combine(datum_parsed, datetime.min.time()) + timedelta(hours=fallback_hour)
    duur_hours = _parse_time_duration(duur_field) if duur_field else 0
    start_dt = eob_dt - timedelta(hours=duur_hours)
    return start_dt, eob_dt


def collect_ploeg_production_details(gallium_data, rubidium_data, indium_data,
                                     thallium_data, iodine_data,
                                     gallium_opbrengsten_data, indium_opbrengsten_data,
                                     planning_data, ploegen_data, spec_settings,
                                     ploegenwissel_date=None) -> dict:
    """Collect per-ploeg production details for the last 6 months.

    Returns a dict ``{ploeg_number: [prod_detail, ...], ...}``.
    """
    end_date   = datetime.now().date()
    default_start = end_date - timedelta(days=180)
    start_date = max(ploegenwissel_date, default_start) if ploegenwissel_date else default_start

    ploeg_productions: dict = defaultdict(list)

    # ------------------------------------------------------------------
    # GALLIUM
    # ------------------------------------------------------------------
    try:
        ga_opb = {(_to_date_lb(d['date']) if not isinstance(d['date'], (date, datetime)) else
                   (d['date'].date() if isinstance(d['date'], datetime) else d['date'])): d
                  for d in (gallium_opbrengsten_data or [])}

        for prod in gallium_data:
            datum_parsed = _to_date_lb(prod.get('date'))
            if not datum_parsed or not (start_date <= datum_parsed <= end_date):
                continue
            start_dt, eob_dt = _build_eob_and_start(
                datum_parsed, prod.get('eobhrmin'), prod.get('duur'))
            opb_data = ga_opb.get(datum_parsed, {})
            production = {
                'date': datum_parsed.strftime('%Y-%m-%d'),
                'bo_nummer': prod.get('identifier'),
                'targetstroom': prod.get('targetstroom'),
                'duur': (eob_dt - start_dt).total_seconds() / 3600,
                'bob_time': start_dt.strftime('%Y-%m-%d %H:%M'),
                'eob_time': eob_dt.strftime('%Y-%m-%d %H:%M'),
                'opmerking': prod.get('opmerking'),
                'cyclotron': prod.get('cyclotron', 'Philips'),
                'opbrengst_mbq': opb_data.get('opbrengst_mbq'),
            }
            _add_production_to_ploeg(ploeg_productions, production, 'gallium',
                                     start_dt, eob_dt, planning_data, ploegen_data, spec_settings)
    except Exception as e:
        print(f"✗ Error collecting Gallium ploeg details: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # RUBIDIUM
    # ------------------------------------------------------------------
    try:
        for prod in rubidium_data:
            datum_parsed = _to_date_lb(prod.get('date'))
            if not datum_parsed or not (start_date <= datum_parsed <= end_date):
                continue
            start_dt, eob_dt = _build_eob_and_start(
                datum_parsed, prod.get('eob_tijd'), prod.get('duur'))
            production = {
                'date': datum_parsed.strftime('%Y-%m-%d'),
                'bo_nummer': prod.get('identifier'),
                'stroom': prod.get('stroom'),
                'efficiency': prod.get('efficiency'),
                'duur': (eob_dt - start_dt).total_seconds() / 3600,
                'bob_time': start_dt.strftime('%Y-%m-%d %H:%M'),
                'eob_time': eob_dt.strftime('%Y-%m-%d %H:%M'),
                'opmerking': prod.get('opmerking'),
            }
            _add_production_to_ploeg(ploeg_productions, production, 'rubidium',
                                     start_dt, eob_dt, planning_data, ploegen_data, spec_settings)
    except Exception as e:
        print(f"✗ Error collecting Rubidium ploeg details: {e}")

    # ------------------------------------------------------------------
    # INDIUM
    # ------------------------------------------------------------------
    try:
        in_opb = {(_to_date_lb(d['date']) if not isinstance(d['date'], (date, datetime)) else
                   (d['date'].date() if isinstance(d['date'], datetime) else d['date'])): d
                  for d in (indium_opbrengsten_data or [])}

        for prod in indium_data:
            datum_parsed = _to_date_lb(prod.get('date'))
            if not datum_parsed or not (start_date <= datum_parsed <= end_date):
                continue
            start_dt, eob_dt = _build_eob_and_start(
                datum_parsed, prod.get('eobhrmin'), prod.get('duur'))
            opb_data = in_opb.get(datum_parsed, {})
            production = {
                'date': datum_parsed.strftime('%Y-%m-%d'),
                'bo_nummer': prod.get('identifier'),
                'targetstroom': prod.get('targetstroom'),
                'duur': (eob_dt - start_dt).total_seconds() / 3600,
                'bob_time': start_dt.strftime('%Y-%m-%d %H:%M'),
                'eob_time': eob_dt.strftime('%Y-%m-%d %H:%M'),
                'opmerking': prod.get('opmerking'),
                'cyclotron': prod.get('cyclotron', 'Philips'),
                'opbrengst_mbq': opb_data.get('opbrengst_mbq'),
            }
            _add_production_to_ploeg(ploeg_productions, production, 'indium',
                                     start_dt, eob_dt, planning_data, ploegen_data, spec_settings)
    except Exception as e:
        print(f"✗ Error collecting Indium ploeg details: {e}")

    # ------------------------------------------------------------------
    # THALLIUM
    # ------------------------------------------------------------------
    try:
        for prod in thallium_data:
            datum_parsed = _to_date_lb(prod.get('date'))
            if not datum_parsed or not (start_date <= datum_parsed <= end_date):
                continue
            start_dt, eob_dt = _build_eob_and_start(
                datum_parsed, prod.get('eob_tijd'), prod.get('duur'))
            production = {
                'date': datum_parsed.strftime('%Y-%m-%d'),
                'bo_nummer': prod.get('identifier'),
                'targetstroom': prod.get('targetstroom'),
                'kant': prod.get('kant'),
                'duur': (eob_dt - start_dt).total_seconds() / 3600,
                'bob_time': start_dt.strftime('%Y-%m-%d %H:%M'),
                'eob_time': eob_dt.strftime('%Y-%m-%d %H:%M'),
                'opmerking': prod.get('opmerking'),
            }
            _add_production_to_ploeg(ploeg_productions, production, 'thallium',
                                     start_dt, eob_dt, planning_data, ploegen_data, spec_settings)
    except Exception as e:
        print(f"✗ Error collecting Thallium ploeg details: {e}")

    # ------------------------------------------------------------------
    # IODINE
    # ------------------------------------------------------------------
    try:
        for prod in iodine_data:
            datum_parsed = _to_date_lb(prod.get('date'))
            if not datum_parsed or not (start_date <= datum_parsed <= end_date):
                continue
            stop_datum = prod.get('stop_datum')
            stop_datum_parsed = (_to_date_lb(stop_datum) if stop_datum else None) or datum_parsed
            start_dt, eob_dt = _build_eob_and_start(
                stop_datum_parsed, prod.get('stop_tijd'),
                prod.get('totale_bestralingstijd'), fallback_hour=18)
            production = {
                'date': datum_parsed.strftime('%Y-%m-%d'),
                'bo_nummer': prod.get('identifier'),
                'targetstroom': prod.get('targetstroom'),
                'duur': (eob_dt - start_dt).total_seconds() / 3600,
                'bob_time': start_dt.strftime('%Y-%m-%d %H:%M'),
                'eob_time': eob_dt.strftime('%Y-%m-%d %H:%M'),
                'opmerking': prod.get('opmerking'),
                'yield_percent': prod.get('yield_percent'),
                'output_percent': prod.get('output_percent'),
                'meting_d1': prod.get('meting_d1'),
                'verwacht': prod.get('verwacht'),
                'totale_storingstijd': prod.get('totale_storingstijd'),
            }
            _add_production_to_ploeg(ploeg_productions, production, 'iodine',
                                     start_dt, eob_dt, planning_data, ploegen_data, spec_settings)
    except Exception as e:
        print(f"✗ Error collecting Iodine ploeg details: {e}")

    return dict(ploeg_productions)


def build_production_history(ploeg_production_details: dict, ploegen_data: dict) -> dict:
    """Invert ploeg_production_details from per-ploeg to per-BO number.

    Returns ``{bo_nummer_str: {'isotope': ..., 'shifts': [...], 'production_data': ...}, ...}``.
    """
    production_history: dict = {}

    for ploeg_number, productions in ploeg_production_details.items():
        for prod in productions:
            bo_nummer = prod['data'].get('bo_nummer')
            if not bo_nummer:
                continue
            bo_str = str(bo_nummer)

            if bo_str not in production_history:
                production_history[bo_str] = {
                    'isotope':          prod['isotope'],
                    'shifts':           [],
                    'production_data':  prod['data'],
                }

            ploeg_name = 'Unknown'
            for code, info in ploegen_data.items():
                if info['ploeg_number'] == ploeg_number:
                    ploeg_name = info['ploeg_name']
                    break

            production_history[bo_str]['shifts'].append({
                'date':         prod['date'],
                'shift':        prod['shift'],
                'ploeg_number': ploeg_number,
                'ploeg_name':   ploeg_name,
                'proportion':   prod['proportion'],
                'in_spec':      prod['in_spec'],
                'sort_key':     prod.get('sort_key'),
            })

    for bo_str in production_history:
        production_history[bo_str]['shifts'].sort(
            key=lambda x: x.get('sort_key') or x['date'])

    return production_history
