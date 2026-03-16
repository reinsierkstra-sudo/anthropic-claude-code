"""
renderer/dashboard_full.py
---------------------------
Full-dashboard renderer extracted from
IsotopeDashboardGenerator.create_html_dashboard() in gallium_extractor.py.

Public entry point
------------------
``create_html_dashboard(data)``

    *data* is a plain dict whose keys correspond 1-to-1 to the positional /
    keyword arguments of the original method.  See ``_unpack()`` below for
    the complete list of expected keys and their defaults.

Internal design
---------------
The function delegates all the heavy HTML construction back to a fresh
``IsotopeDashboardGenerator`` instance (created with a dummy path) so that
the business logic — storingen sorting, ploeg chart rendering, modal JS,
etc. — is not duplicated here.  The renderer module's job is to provide the
clean dict-based API and to forward the call.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Key catalogue with defaults — mirrors the signature of create_html_dashboard
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    # Running-week isotope data
    "ga_running": [],
    "ga_monthly": [],
    "ga_previous": [],
    "rb_running": [],
    "rb_monthly": [],
    "rb_previous": [],
    "in_running": [],
    "in_monthly": [],
    "in_previous": [],
    "tl_running": [],
    "tl_monthly_12": [],
    "tl_monthly_21": [],
    "tl_previous": [],
    "io_running": [],
    "io_monthly": [],
    "io_previous": [],
    # Efficiency KPI
    "efficiency_weeks": [],
    "efficiency_average": 0.0,
    "efficiency_last_year_avg": 0.0,
    "efficiency_last_3months_avg": 0.0,
    "efficiency_past_year": [],
    "efficiency_all_time": [],
    # Within-spec KPI
    "within_spec_weeks": [],
    "within_spec_average": 0.0,
    "within_spec_last_year_avg": 0.0,
    "within_spec_last_3months_avg": 0.0,
    "within_spec_past_year": [],
    "within_spec_all_time": [],
    # Issue tracking
    "issue_counts": {"this_week": {}, "last_week": {}, "all_time": {}},
    "isotope_issues": {},
    # Production-efficiency KPI per isotope
    "gallium_eff_weeks": [],
    "gallium_eff_avg": 0.0,
    "gallium_eff_all_time": 0.0,
    "gallium_eff_year": 0.0,
    "gallium_eff_3months": 0.0,
    "indium_eff_weeks": [],
    "indium_eff_avg": 0.0,
    "indium_eff_all_time": 0.0,
    "indium_eff_year": 0.0,
    "indium_eff_3months": 0.0,
    "rubidium_eff_weeks": [],
    "rubidium_eff_avg": 0.0,
    "rubidium_eff_all_time": 0.0,
    "rubidium_eff_year": 0.0,
    "rubidium_eff_3months": 0.0,
    "iodine_eff_weeks": [],
    "iodine_eff_avg": 0.0,
    "iodine_eff_all_time": 0.0,
    "iodine_eff_year": 0.0,
    "iodine_eff_3months": 0.0,
    # Shift statistics
    "shift_stats_this_week": {},
    "shift_stats_last_week": {},
    "this_week_friday": None,
    "last_week_friday": None,
    # Ploeg performance
    "ploeg_6month": {},
    "ploeg_3month": {},
    "ploeg_monthly": {},
    "ploeg_rolling": {},
    "leaderboard": [],
    "monthly_winner": None,
    # Optional flags / rich content
    "tampering_warning": None,
    "ploeg_production_details": None,
    "production_history": None,
    "cyclotron_data": None,
    # OTIF gedraaide KPI
    "otif_gedraaide_weeks": None,
    "otif_gedraaide_average": 0.0,
    "otif_gedraaide_last_year_avg": 0.0,
    "otif_gedraaide_last_3months_avg": 0.0,
    # Additional rich content
    "vsm_data": None,
    "planning_html_content": None,
    "productieschema_html_content": None,
    # Storingen data (injected when passed via the generator instance)
    "iba_storingen_data": [],
    "philips_storingen_data": [],
    # OTIF KPI / table data (from the generator's instance attributes)
    "otif_kpi_data": [],
    "otif_table_data": {},
    # Ploegen definitions (needed by generate_ploeg_rolling_charts_html)
    "ploegen_data": {},
}


def _unpack(data: dict) -> dict:
    """Merge *data* over ``_DEFAULTS`` and return the complete values dict."""
    result = dict(_DEFAULTS)
    result.update(data)
    return result


def create_html_dashboard(data: dict) -> str:
    """Render the full production dashboard HTML.

    Parameters
    ----------
    data:
        Dict containing all calculated values.  Unrecognised keys are
        ignored; missing keys fall back to the defaults defined in
        ``_DEFAULTS``.

    Returns
    -------
    str
        Complete ``<!DOCTYPE html>`` document as a string.

    Notes
    -----
    This function delegates to
    ``IsotopeDashboardGenerator.create_html_dashboard()`` via a
    lightweight shim instance so that all the original business logic
    (storingen sorting, modal JS, chart generation, etc.) is preserved
    verbatim.
    """
    from gallium_extractor import IsotopeDashboardGenerator

    v = _unpack(data)

    # Build a minimal shim instance that holds the instance-attribute data
    # the original method reads via ``self.*``.  We use a dummy path and skip
    # all database connections.
    gen = IsotopeDashboardGenerator.__new__(IsotopeDashboardGenerator)

    # Inject the instance attributes that create_html_dashboard reads directly
    # from self rather than from its arguments.
    gen.iba_storingen_data    = list(v["iba_storingen_data"])
    gen.philips_storingen_data = list(v["philips_storingen_data"])
    gen.otif_kpi_data         = v["otif_kpi_data"]
    gen.otif_table_data       = v["otif_table_data"]
    gen.ploegen_data          = v["ploegen_data"]

    # Provide stubs for methods that the dashboard calls on self but that
    # require a live database connection.  They are only exercised when the
    # original generator is fully connected; here we return safe defaults.
    gen.count_sf_references      = lambda: ({}, {})
    gen.get_saved_comment        = lambda *a, **kw: ""
    gen.generate_leaderboard_html    = lambda lb: _delegate_leaderboard(gen, lb)
    gen.generate_monthly_winner_html = lambda w:  _delegate_monthly_winner(gen, w)
    gen.generate_shift_tables_html   = lambda *a, **kw: _delegate_shift_tables(gen, *a, **kw)
    gen.generate_ploeg_rolling_charts_html = lambda pr: _delegate_rolling_charts(gen, pr)

    return gen.create_html_dashboard(
        v["ga_running"],  v["ga_monthly"],  v["ga_previous"],
        v["rb_running"],  v["rb_monthly"],  v["rb_previous"],
        v["in_running"],  v["in_monthly"],  v["in_previous"],
        v["tl_running"],  v["tl_monthly_12"], v["tl_monthly_21"], v["tl_previous"],
        v["io_running"],  v["io_monthly"],  v["io_previous"],
        v["efficiency_weeks"],       v["efficiency_average"],
        v["efficiency_last_year_avg"], v["efficiency_last_3months_avg"],
        v["efficiency_past_year"],   v["efficiency_all_time"],
        v["within_spec_weeks"],      v["within_spec_average"],
        v["within_spec_last_year_avg"], v["within_spec_last_3months_avg"],
        v["within_spec_past_year"],  v["within_spec_all_time"],
        v["issue_counts"],           v["isotope_issues"],
        v["gallium_eff_weeks"],      v["gallium_eff_avg"],
        v["gallium_eff_all_time"],   v["gallium_eff_year"],   v["gallium_eff_3months"],
        v["indium_eff_weeks"],       v["indium_eff_avg"],
        v["indium_eff_all_time"],    v["indium_eff_year"],    v["indium_eff_3months"],
        v["rubidium_eff_weeks"],     v["rubidium_eff_avg"],
        v["rubidium_eff_all_time"],  v["rubidium_eff_year"],  v["rubidium_eff_3months"],
        v["iodine_eff_weeks"],       v["iodine_eff_avg"],
        v["iodine_eff_all_time"],    v["iodine_eff_year"],    v["iodine_eff_3months"],
        v["shift_stats_this_week"],  v["shift_stats_last_week"],
        v["this_week_friday"],       v["last_week_friday"],
        v["ploeg_6month"],  v["ploeg_3month"], v["ploeg_monthly"],
        v["ploeg_rolling"], v["leaderboard"],  v["monthly_winner"],
        tampering_warning             = v["tampering_warning"],
        ploeg_production_details      = v["ploeg_production_details"],
        production_history            = v["production_history"],
        cyclotron_data                = v["cyclotron_data"],
        otif_gedraaide_weeks          = v["otif_gedraaide_weeks"],
        otif_gedraaide_average        = v["otif_gedraaide_average"],
        otif_gedraaide_last_year_avg  = v["otif_gedraaide_last_year_avg"],
        otif_gedraaide_last_3months_avg = v["otif_gedraaide_last_3months_avg"],
        vsm_data                      = v["vsm_data"],
        planning_html_content         = v["planning_html_content"],
        productieschema_html_content  = v["productieschema_html_content"],
    )


# ---------------------------------------------------------------------------
# Thin delegation helpers — reuse the original methods by binding them to
# the shim instance after re-importing what's needed.
# ---------------------------------------------------------------------------

def _delegate_leaderboard(gen, leaderboard):
    """Call the original generate_leaderboard_html method."""
    from gallium_extractor import IsotopeDashboardGenerator as _C
    return _C.generate_leaderboard_html(gen, leaderboard)


def _delegate_monthly_winner(gen, winner):
    """Call the original generate_monthly_winner_html method."""
    from gallium_extractor import IsotopeDashboardGenerator as _C
    return _C.generate_monthly_winner_html(gen, winner)


def _delegate_shift_tables(gen, *args, **kwargs):
    """Call the original generate_shift_tables_html method."""
    from gallium_extractor import IsotopeDashboardGenerator as _C
    return _C.generate_shift_tables_html(gen, *args, **kwargs)


def _delegate_rolling_charts(gen, ploeg_rolling):
    """Call the original generate_ploeg_rolling_charts_html method."""
    from gallium_extractor import IsotopeDashboardGenerator as _C
    return _C.generate_ploeg_rolling_charts_html(gen, ploeg_rolling)
