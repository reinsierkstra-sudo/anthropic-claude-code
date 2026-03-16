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

The script reuses the calculator methods on ``IsotopeDashboardGenerator``
which already operate on the in-memory data populated by the collector.
In the full pipeline, ``run_renderer`` reads the results returned here.

Returns
-------
dict
    A flat dictionary of all calculated values ready to be passed to
    ``renderer.dashboard_full.create_html_dashboard()`` or
    ``renderer.dashboard_truncated.create_truncated_dashboard()``.
"""

import traceback
from datetime import datetime, timedelta

from config.loader import load_settings, get_spec_settings


def main() -> dict:
    """Run all calculators and return the results dict.

    The function connects to the SQLite database, reloads the raw isotope
    records into a generator instance (to reuse the calculator methods),
    then runs every KPI calculator and returns the aggregated data.

    Prints ``✓`` / ``⚠`` status lines for each calculation stage.
    """
    cfg = load_settings()
    paths = cfg.get("paths", {})
    sqlite_db = paths.get("sqlite_db", "isotope_data.db")

    from gallium_extractor import IsotopeDashboardGenerator

    # Reuse the generator's calculator methods; we just need SQLite loaded.
    generator = IsotopeDashboardGenerator(
        access_db_path             = paths.get("access_db", ""),
        sqlite_db_path             = sqlite_db,
        proces_db_path             = paths.get("proces_db"),
        storingen_db_path          = paths.get("storingen_db"),
        philips_storingen_db_path  = paths.get("philips_storingen_db"),
        ploegen_excel_path         = paths.get("ploegen_excel"),
        planning_excel_path        = paths.get("planning_excel"),
        vsm_excel_path             = paths.get("vsm_excel"),
        planning_html_path         = paths.get("planning_html"),
        productieschema_html_path  = paths.get("productieschema_html"),
    )

    print("=" * 60)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] run_calculator — KPI calculations")
    print("=" * 60)

    if not generator.connect_sqlite():
        print("✗ Could not connect to SQLite — aborting.")
        return {}

    # Reload raw data from SQLite so calculators have data to work with.
    try:
        generator.load_data_from_sqlite()
        print("✓ Loaded raw data from SQLite")
    except Exception as e:
        print(f"⚠ Could not reload data from SQLite: {e}")

    results: dict = {}

    # ── Efficiency KPI ────────────────────────────────────────────────────
    try:
        results["efficiency_weeks"], results["efficiency_average"] = generator.get_efficiency_weeks()
        results["efficiency_last_year_avg"]    = generator.get_efficiency_last_year_average()
        results["efficiency_last_3months_avg"] = generator.get_efficiency_last_3months_average()
        results["efficiency_past_year"]        = generator.get_efficiency_past_year()
        results["efficiency_all_time"]         = generator.get_efficiency_all_time()
        print("✓ Efficiency calculations complete")
    except Exception as e:
        print(f"⚠ Efficiency calculations failed: {e}")
        results.update({
            "efficiency_weeks": [], "efficiency_average": 0.0,
            "efficiency_last_year_avg": 0.0, "efficiency_last_3months_avg": 0.0,
            "efficiency_past_year": [], "efficiency_all_time": [],
        })

    # ── Within-spec KPI ───────────────────────────────────────────────────
    try:
        results["within_spec_weeks"], results["within_spec_average"] = generator.get_within_spec_weeks()
        results["within_spec_last_year_avg"]    = generator.get_within_spec_last_year_average()
        results["within_spec_last_3months_avg"] = generator.get_within_spec_last_3months_average()
        results["within_spec_past_year"]        = generator.get_within_spec_past_year()
        results["within_spec_all_time"]         = generator.get_within_spec_all_time()
        print("✓ Within-spec calculations complete")
    except Exception as e:
        print(f"⚠ Within-spec calculations failed: {e}")
        results.update({
            "within_spec_weeks": [], "within_spec_average": 0.0,
            "within_spec_last_year_avg": 0.0, "within_spec_last_3months_avg": 0.0,
            "within_spec_past_year": [], "within_spec_all_time": [],
        })

    # ── OTIF gedraaide producties ─────────────────────────────────────────
    try:
        results["otif_gedraaide_weeks"], results["otif_gedraaide_average"] = generator.get_otif_gedraaide_weeks()
        results["otif_gedraaide_last_year_avg"]    = generator.get_otif_gedraaide_last_year_average()
        results["otif_gedraaide_last_3months_avg"] = generator.get_otif_gedraaide_last_3months_average()
        print("✓ OTIF gedraaide producties calculations complete")
    except Exception as e:
        print(f"⚠ OTIF gedraaide calculations failed: {e}")
        results.update({
            "otif_gedraaide_weeks": [], "otif_gedraaide_average": 0.0,
            "otif_gedraaide_last_year_avg": 0.0, "otif_gedraaide_last_3months_avg": 0.0,
        })

    # ── Issue counts ──────────────────────────────────────────────────────
    try:
        results["issue_counts"]   = generator.get_issue_counts()
        results["isotope_issues"] = generator.get_isotope_issue_counts()
        print("✓ Issue counts complete")
    except Exception as e:
        print(f"⚠ Issue counts failed: {e}")
        results.update({
            "issue_counts": {"this_week": {}, "last_week": {}, "all_time": {}},
            "isotope_issues": {},
        })

    # ── Production efficiency per isotope (mCi/µAh) ───────────────────────
    for iso in ("gallium", "indium", "rubidium", "iodine"):
        try:
            eff_weeks, eff_avg = getattr(generator, f"get_{iso}_efficiency_weeks")()
            eff_all, eff_year, eff_3m = getattr(generator, f"get_{iso}_efficiency_averages")()
            results[f"{iso}_eff_weeks"]    = eff_weeks
            results[f"{iso}_eff_avg"]      = eff_avg
            results[f"{iso}_eff_all_time"] = eff_all
            results[f"{iso}_eff_year"]     = eff_year
            results[f"{iso}_eff_3months"]  = eff_3m
            print(f"✓ {iso.capitalize()} production efficiency complete")
        except Exception as e:
            print(f"⚠ {iso.capitalize()} production efficiency failed: {e}")
            for suffix in ("eff_weeks", "eff_avg", "eff_all_time", "eff_year", "eff_3months"):
                results[f"{iso}_{suffix}"] = [] if suffix == "eff_weeks" else 0.0

    # ── Running-week / previous-week isotope data ─────────────────────────
    results["ga_running"]  = generator.get_since_friday_data(generator.gallium_data)
    results["ga_monthly"]  = generator.calculate_monthly_averages(generator.gallium_data, use_targetstroom=True)
    results["ga_previous"] = generator.get_previous_week_data(generator.gallium_data)

    results["rb_running"]  = generator.get_since_friday_data(generator.rubidium_data)
    results["rb_monthly"]  = generator.calculate_monthly_averages(generator.rubidium_data, use_targetstroom=False)
    results["rb_previous"] = generator.get_previous_week_data(generator.rubidium_data)

    results["in_running"]  = generator.get_since_friday_data(generator.indium_data)
    results["in_monthly"]  = generator.calculate_monthly_averages(generator.indium_data, use_targetstroom=True)
    results["in_previous"] = generator.get_previous_week_data(generator.indium_data)

    results["tl_running"]    = generator.get_since_friday_data(generator.thallium_data)
    results["tl_monthly_12"], results["tl_monthly_21"] = generator.calculate_monthly_averages_by_kant(generator.thallium_data)
    results["tl_previous"]   = generator.get_previous_week_data(generator.thallium_data)

    results["io_running"]  = generator.get_since_friday_data(generator.iodine_data)
    results["io_monthly"]  = generator.calculate_monthly_averages(generator.iodine_data, use_targetstroom=False)
    results["io_previous"] = generator.get_previous_week_data(generator.iodine_data)
    print("✓ Running-week / previous-week data assembled")

    # ── Shift statistics ──────────────────────────────────────────────────
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7
    this_week_friday = today - timedelta(days=days_since_friday)
    last_week_friday = this_week_friday - timedelta(days=7)
    results["this_week_friday"] = this_week_friday
    results["last_week_friday"] = last_week_friday

    try:
        results["shift_stats_this_week"] = generator.calculate_shift_statistics(this_week_friday)
        results["shift_stats_last_week"] = generator.calculate_shift_statistics(last_week_friday)
        print("✓ Weekly shift statistics complete")
    except Exception as e:
        print(f"⚠ Weekly shift statistics failed: {e}")
        traceback.print_exc()
        results["shift_stats_this_week"] = {}
        results["shift_stats_last_week"] = {}

    # ── All-time shift statistics for ploegen analysis ────────────────────
    default_lookback = today - timedelta(days=180)
    lookback_date = max(generator.ploegenwissel_date, default_lookback) if generator.ploegenwissel_date else default_lookback

    try:
        shift_stats_all_time = generator.calculate_shift_statistics_all_time(lookback_date)
        print("✓ All-time shift statistics complete")
    except Exception as e:
        print(f"⚠ All-time shift statistics failed: {e}")
        traceback.print_exc()
        shift_stats_all_time = {}

    # ── Ploegen statistics ────────────────────────────────────────────────
    results.update({
        "ploeg_6month": {}, "ploeg_3month": {}, "ploeg_monthly": {},
        "ploeg_rolling": {}, "leaderboard": [], "monthly_winner": None,
        "ploeg_production_details": {}, "production_history": {},
    })
    try:
        if generator.load_ploegen_definitions() and generator.load_planning_data():
            results["ploeg_6month"], results["ploeg_3month"], results["ploeg_monthly"] = \
                generator.calculate_ploeg_statistics(shift_stats_all_time)
            results["ploeg_rolling"]   = generator.calculate_ploeg_rolling_averages(shift_stats_all_time)
            results["leaderboard"]     = generator.calculate_ploeg_leaderboard(shift_stats_all_time)
            results["monthly_winner"]  = generator.calculate_last_month_winner(shift_stats_all_time)
            results["ploeg_production_details"] = generator.collect_ploeg_production_details()
            results["production_history"] = generator.build_production_history(results["ploeg_production_details"])
            print("✓ Ploegen statistics, leaderboard, and production history complete")
        else:
            print("⚠ Skipping ploegen statistics (loading errors)")
    except Exception as e:
        print(f"⚠ Ploegen statistics failed: {e}")
        traceback.print_exc()

    # Expose ploegen_data so the dashboard renderer can resolve ploeg names
    results["ploegen_data"] = generator.ploegen_data

    # Storingen data for the full dashboard renderer
    results["iba_storingen_data"]     = generator.iba_storingen_data
    results["philips_storingen_data"] = generator.philips_storingen_data

    # OTIF table / KPI chart data
    results["otif_kpi_data"]   = generator.otif_kpi_data
    results["otif_table_data"] = generator.otif_table_data

    generator.close()

    # ── Persist to derived.db ─────────────────────────────────────────────
    try:
        from collector.derived_db import connect as connect_derived, save_kpis
        derived_db_path = paths.get("derived_db", "data/derived.db")
        derived_conn = connect_derived(derived_db_path)
        save_kpis(derived_conn, results)
        derived_conn.close()
        print(f"✓ Results written to derived.db ({len(results)} keys)")
    except Exception as e:
        print(f"⚠ Could not write to derived.db: {e}")

    print("✓ All calculations complete")
    return results


if __name__ == "__main__":
    main()
