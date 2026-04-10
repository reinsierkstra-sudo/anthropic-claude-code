"""
run_calculator.py
-----------------
Entry point that reads raw data from the SQLite database and runs all
KPI calculators (efficiency, within-spec, OTIF, shift stats, leaderboard,
issues).

This is phase 2 of the refactored pipeline:
  run_collector  →  **run_calculator**  →  run_renderer

Usage::

    python run_calculator.py

No dependency on gallium_extractor.IsotopeDashboardGenerator.
"""

import traceback
from datetime import datetime, timedelta

from config.loader import load_settings
from config.spec_settings import SPEC_SETTINGS


def main() -> dict:
    """Run all calculators and return the results dict."""
    cfg       = load_settings()
    paths     = cfg.get("paths", {})
    sqlite_db = paths.get("raw_db", "data/raw.db")

    from collector import raw_db, excel_reader

    from calculator import efficiency  as eff_mod
    from calculator import within_spec as ws_mod
    from calculator import otif        as otif_mod
    from calculator import issues      as issue_mod
    from calculator import shift_stats as ss_mod
    from calculator import leaderboard as lb_mod
    from calculator.isotope_data import (
        get_since_friday_data, get_previous_week_data,
        calculate_monthly_averages, calculate_monthly_averages_by_kant,
        get_last_friday,
    )

    print("=" * 60)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] run_calculator — KPI calculations")
    print("=" * 60)

    raw_conn = raw_db.connect(sqlite_db)

    # ── Load raw isotope data ────────────────────────────────────────────────
    ga_data = raw_db.load_table(raw_conn, 'gallium_data')
    rb_data = raw_db.load_table(raw_conn, 'rubidium_data')
    in_data = raw_db.load_table(raw_conn, 'indium_data')
    tl_data = raw_db.load_table(raw_conn, 'thallium_data')
    io_data = raw_db.load_table(raw_conn, 'iodine_data')
    print(f"✓ Loaded raw data: ga={len(ga_data)} rb={len(rb_data)} "
          f"in={len(in_data)} tl={len(tl_data)} io={len(io_data)}")

    # ── Load opbrengsten and auxiliary data ──────────────────────────────────
    ga_opb = raw_db.load_table(raw_conn, 'gallium_opbrengsten')
    in_opb = raw_db.load_table(raw_conn, 'indium_opbrengsten')

    eff_targets       = raw_db.load_table(raw_conn, 'efficiency_targets')
    iba_storingen     = raw_db.load_table(raw_conn, 'iba_storingen')
    philips_storingen = raw_db.load_table(raw_conn, 'philips_storingen')

    otif_kpi_data   = raw_db.load_blob(raw_conn, 'otif_kpi_data',   default=[])
    otif_table_data = raw_db.load_blob(raw_conn, 'otif_table_data', default={})
    vsm_data        = raw_db.load_blob(raw_conn, 'vsm_data',        default=[])
    planning_html   = raw_db.load_blob(raw_conn, 'planning_html',   default=None)
    prod_html       = raw_db.load_blob(raw_conn, 'productieschema_html', default=None)
    dosissen_html   = raw_db.load_blob(raw_conn, 'dosissen_html',   default=None)
    heartbeat_data  = raw_db.load_blob(raw_conn, 'heartbeat_data',  default=[])

    # ── Load ploegen / planning ──────────────────────────────────────────────
    ploegen_data     = {}
    ploegenwissel_date = None
    planning_data    = {}

    ploegen_path  = paths.get("ploegen_excel", "")
    planning_path = paths.get("planning_excel", "")

    if ploegen_path:
        try:
            ploegen_data, ploegenwissel_date = excel_reader.load_ploegen_definitions(
                ploegen_path, raw_conn)
            print(f"✓ Loaded ploegen definitions ({len(ploegen_data)} entries)")
        except Exception as e:
            print(f"⚠ Could not load ploegen definitions: {e}")

    if planning_path:
        try:
            planning_data = excel_reader.load_planning_data(planning_path, raw_conn)
            print(f"✓ Loaded planning data ({len(planning_data)} dates)")
        except Exception as e:
            print(f"⚠ Could not load planning data: {e}")

    raw_conn.close()

    # Shared positional args for calculators that accept all 5 isotopes + spec
    _all5      = (ga_data, rb_data, in_data, tl_data, io_data)
    _all5_spec = _all5 + (SPEC_SETTINGS,)

    results: dict = {}

    # ── Efficiency KPI ────────────────────────────────────────────────────────
    try:
        results["efficiency_weeks"], results["efficiency_average"] = \
            eff_mod.get_efficiency_weeks(*_all5_spec, efficiency_targets=eff_targets)
        results["efficiency_last_year_avg"]    = eff_mod.get_efficiency_last_year_average(*_all5_spec, efficiency_targets=eff_targets)
        results["efficiency_last_3months_avg"] = eff_mod.get_efficiency_last_3months_average(*_all5_spec, efficiency_targets=eff_targets)
        results["efficiency_past_year"]        = eff_mod.get_efficiency_past_year(*_all5_spec, efficiency_targets=eff_targets)
        results["efficiency_all_time"]         = eff_mod.get_efficiency_all_time(*_all5_spec, efficiency_targets=eff_targets)
        print("✓ Efficiency calculations complete")
    except Exception as e:
        print(f"⚠ Efficiency calculations failed: {e}")
        results.update({"efficiency_weeks": [], "efficiency_average": 0.0,
                        "efficiency_last_year_avg": 0.0, "efficiency_last_3months_avg": 0.0,
                        "efficiency_past_year": [], "efficiency_all_time": []})

    # ── Within-spec KPI ───────────────────────────────────────────────────────
    try:
        results["within_spec_weeks"], results["within_spec_average"] = \
            ws_mod.get_within_spec_weeks(*_all5_spec)
        results["within_spec_last_year_avg"]    = ws_mod.get_within_spec_last_year_average(*_all5_spec)
        results["within_spec_last_3months_avg"] = ws_mod.get_within_spec_last_3months_average(*_all5_spec)
        results["within_spec_past_year"]        = ws_mod.get_within_spec_past_year(*_all5_spec)
        results["within_spec_all_time"]         = ws_mod.get_within_spec_all_time(*_all5_spec)
        print("✓ Within-spec calculations complete")
    except Exception as e:
        print(f"⚠ Within-spec calculations failed: {e}")
        results.update({"within_spec_weeks": [], "within_spec_average": 0.0,
                        "within_spec_last_year_avg": 0.0, "within_spec_last_3months_avg": 0.0,
                        "within_spec_past_year": [], "within_spec_all_time": []})

    # ── OTIF gedraaide producties ──────────────────────────────────────────────
    try:
        results["otif_gedraaide_weeks"], results["otif_gedraaide_average"] = \
            otif_mod.get_otif_gedraaide_weeks(*_all5_spec)
        results["otif_gedraaide_last_year_avg"]    = \
            otif_mod.get_otif_gedraaide_last_year_average(*_all5_spec)
        results["otif_gedraaide_last_3months_avg"] = \
            otif_mod.get_otif_gedraaide_last_3months_average(*_all5_spec)
        print("✓ OTIF gedraaide calculations complete")
    except Exception as e:
        print(f"⚠ OTIF gedraaide calculations failed: {e}")
        results.update({"otif_gedraaide_weeks": [], "otif_gedraaide_average": 0.0,
                        "otif_gedraaide_last_year_avg": 0.0,
                        "otif_gedraaide_last_3months_avg": 0.0})

    # ── Issue counts ──────────────────────────────────────────────────────────
    try:
        _issue_conn = raw_db.connect(sqlite_db)
        results["issue_counts"]   = issue_mod.get_issue_counts(_issue_conn)
        results["isotope_issues"] = issue_mod.get_isotope_issue_counts(_issue_conn)
        _issue_conn.close()
        print("✓ Issue counts complete")
    except Exception as e:
        print(f"⚠ Issue counts failed: {e}")
        results.update({"issue_counts": {"this_week": {}, "last_week": {}, "all_time": {}},
                        "isotope_issues": {}})

    # ── Per-isotope production efficiency (mCi/µAh) ───────────────────────────
    try:
        eff_weeks, eff_avg = eff_mod.get_gallium_efficiency_weeks(ga_data, ga_opb)
        all_t, yr, m3 = eff_mod.get_gallium_efficiency_averages(ga_data, ga_opb)
        results.update({"gallium_eff_weeks": eff_weeks, "gallium_eff_avg": eff_avg,
                        "gallium_eff_all_time": all_t, "gallium_eff_year": yr, "gallium_eff_3months": m3})
        print("✓ Gallium production efficiency complete")
    except Exception as e:
        print(f"⚠ Gallium production efficiency failed: {e}")
        results.update({"gallium_eff_weeks": [], "gallium_eff_avg": 0.0,
                        "gallium_eff_all_time": 0.0, "gallium_eff_year": 0.0, "gallium_eff_3months": 0.0})

    try:
        eff_weeks, eff_avg = eff_mod.get_indium_efficiency_weeks(in_data, in_opb)
        all_t, yr, m3 = eff_mod.get_indium_efficiency_averages(in_data, in_opb)
        results.update({"indium_eff_weeks": eff_weeks, "indium_eff_avg": eff_avg,
                        "indium_eff_all_time": all_t, "indium_eff_year": yr, "indium_eff_3months": m3})
        print("✓ Indium production efficiency complete")
    except Exception as e:
        print(f"⚠ Indium production efficiency failed: {e}")
        results.update({"indium_eff_weeks": [], "indium_eff_avg": 0.0,
                        "indium_eff_all_time": 0.0, "indium_eff_year": 0.0, "indium_eff_3months": 0.0})

    try:
        eff_weeks, eff_avg = eff_mod.get_rubidium_efficiency_weeks(rb_data)
        all_t, yr, m3 = eff_mod.get_rubidium_efficiency_averages(rb_data)
        results.update({"rubidium_eff_weeks": eff_weeks, "rubidium_eff_avg": eff_avg,
                        "rubidium_eff_all_time": all_t, "rubidium_eff_year": yr, "rubidium_eff_3months": m3})
        print("✓ Rubidium production efficiency complete")
    except Exception as e:
        print(f"⚠ Rubidium production efficiency failed: {e}")
        results.update({"rubidium_eff_weeks": [], "rubidium_eff_avg": 0.0,
                        "rubidium_eff_all_time": 0.0, "rubidium_eff_year": 0.0, "rubidium_eff_3months": 0.0})

    try:
        eff_weeks, eff_avg = eff_mod.get_iodine_efficiency_weeks(io_data)
        all_t, yr, m3 = eff_mod.get_iodine_efficiency_averages(io_data)
        results.update({"iodine_eff_weeks": eff_weeks, "iodine_eff_avg": eff_avg,
                        "iodine_eff_all_time": all_t, "iodine_eff_year": yr, "iodine_eff_3months": m3})
        print("✓ Iodine production efficiency complete")
    except Exception as e:
        print(f"⚠ Iodine production efficiency failed: {e}")
        results.update({"iodine_eff_weeks": [], "iodine_eff_avg": 0.0,
                        "iodine_eff_all_time": 0.0, "iodine_eff_year": 0.0, "iodine_eff_3months": 0.0})

    # ── Running-week / previous-week isotope data ─────────────────────────────
    results["ga_running"]  = get_since_friday_data(ga_data)
    results["ga_monthly"]  = calculate_monthly_averages(ga_data, use_targetstroom=True)
    results["ga_previous"] = get_previous_week_data(ga_data)

    results["rb_running"]  = get_since_friday_data(rb_data)
    results["rb_monthly"]  = calculate_monthly_averages(rb_data, use_targetstroom=False)
    results["rb_previous"] = get_previous_week_data(rb_data)

    results["in_running"]  = get_since_friday_data(in_data)
    results["in_monthly"]  = calculate_monthly_averages(in_data, use_targetstroom=True)
    results["in_previous"] = get_previous_week_data(in_data)

    results["tl_running"]    = get_since_friday_data(tl_data)
    results["tl_monthly_12"], results["tl_monthly_21"] = \
        calculate_monthly_averages_by_kant(tl_data)
    results["tl_previous"]   = get_previous_week_data(tl_data)

    results["io_running"]  = get_since_friday_data(io_data)
    results["io_monthly"]  = calculate_monthly_averages(io_data, use_targetstroom=False)
    results["io_previous"] = get_previous_week_data(io_data)
    print("✓ Running-week / previous-week data assembled")

    # ── Shift statistics ──────────────────────────────────────────────────────
    last_friday      = get_last_friday()
    prev_friday      = last_friday - timedelta(days=7)
    results["this_week_friday"] = last_friday
    results["last_week_friday"] = prev_friday

    _ploeg_kwargs = dict(
        ploegen_data=ploegen_data, planning_data=planning_data,
        ploegenwissel_date=ploegenwissel_date, spec_settings=SPEC_SETTINGS
    )

    try:
        results["shift_stats_this_week"] = ss_mod.calculate_shift_statistics(
            *_all5, week_start_friday=last_friday, **_ploeg_kwargs)
        results["shift_stats_last_week"] = ss_mod.calculate_shift_statistics(
            *_all5, week_start_friday=prev_friday, **_ploeg_kwargs)
        print("✓ Weekly shift statistics complete")
    except Exception as e:
        print(f"⚠ Weekly shift statistics failed: {e}")
        traceback.print_exc()
        results["shift_stats_this_week"] = {}
        results["shift_stats_last_week"] = {}

    # ── All-time shift statistics for ploegen analysis ────────────────────────
    today         = datetime.now().date()
    default_lb    = today - timedelta(days=180)
    lookback_date = max(ploegenwissel_date, default_lb) if ploegenwissel_date else default_lb

    shift_stats_all_time = {}
    try:
        shift_stats_all_time = ss_mod.calculate_shift_statistics_all_time(
            *_all5, lookback_date=lookback_date, **_ploeg_kwargs)
        print("✓ All-time shift statistics complete")
    except Exception as e:
        print(f"⚠ All-time shift statistics failed: {e}")
        traceback.print_exc()

    # ── Ploegen statistics ────────────────────────────────────────────────────
    results.update({
        "ploeg_6month": {}, "ploeg_3month": {}, "ploeg_monthly": {},
        "ploeg_rolling": {}, "leaderboard": [], "monthly_winner": None,
        "ploeg_production_details": {}, "production_history": {},
    })

    if ploegen_data and planning_data:
        try:
            results["ploeg_6month"], results["ploeg_3month"], results["ploeg_monthly"] = \
                lb_mod.calculate_ploeg_statistics(
                    *_all5, ploegen_data=ploegen_data, planning_data=planning_data,
                    ploegenwissel_date=ploegenwissel_date, spec_settings=SPEC_SETTINGS)
            results["ploeg_rolling"]  = lb_mod.calculate_ploeg_rolling_averages(
                *_all5, ploegen_data=ploegen_data, planning_data=planning_data,
                ploegenwissel_date=ploegenwissel_date, spec_settings=SPEC_SETTINGS)
            results["leaderboard"]    = lb_mod.calculate_ploeg_leaderboard(
                *_all5, ploegen_data=ploegen_data, planning_data=planning_data,
                ploegenwissel_date=ploegenwissel_date, spec_settings=SPEC_SETTINGS)
            results["monthly_winner"] = lb_mod.calculate_last_month_winner(
                *_all5, ploegen_data=ploegen_data, planning_data=planning_data,
                ploegenwissel_date=ploegenwissel_date, spec_settings=SPEC_SETTINGS)
            results["ploeg_production_details"] = lb_mod.collect_ploeg_production_details(
                ga_data, rb_data, in_data, tl_data, io_data,
                ga_opb, in_opb,
                planning_data=planning_data, ploegen_data=ploegen_data,
                spec_settings=SPEC_SETTINGS, ploegenwissel_date=ploegenwissel_date)
            results["production_history"] = lb_mod.build_production_history(
                results["ploeg_production_details"], ploegen_data)
            print("✓ Ploegen statistics, leaderboard, and production history complete")
        except Exception as e:
            print(f"⚠ Ploegen statistics failed: {e}")
            traceback.print_exc()
    else:
        print("⚠ Skipping ploegen statistics (ploegen or planning data missing)")

    # ── Pass-through data ─────────────────────────────────────────────────────
    results["ploegen_data"]           = ploegen_data
    results["iba_storingen_data"]     = iba_storingen
    results["philips_storingen_data"] = philips_storingen
    results["otif_kpi_data"]          = otif_kpi_data
    results["otif_table_data"]        = otif_table_data
    results["vsm_data"]               = vsm_data
    results["planning_html_content"]         = planning_html
    results["productieschema_html_content"]  = prod_html
    results["dosissen_html_content"]         = dosissen_html
    results["heartbeat_data"]         = heartbeat_data
    results["tampering_warning"]      = None
    results["ploegen_data"]           = ploegen_data

    # ── Persist to derived.db ─────────────────────────────────────────────────
    try:
        from collector.derived_db import connect as connect_derived, save_kpis
        derived_db_path = paths.get("derived_db", "data/derived.db")
        derived_conn    = connect_derived(derived_db_path)
        save_kpis(derived_conn, results)
        derived_conn.close()
        print(f"✓ Results written to derived.db ({len(results)} keys)")
    except Exception as e:
        print(f"⚠ Could not write to derived.db: {e}")

    print("=" * 60)
    print("✓ All calculations complete")
    return results


if __name__ == "__main__":
    main()
