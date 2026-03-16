"""
renderer/dashboard_truncated.py
---------------------------------
Truncated-dashboard renderer extracted from
IsotopeDashboardGenerator.create_truncated_html_dashboard() in
gallium_extractor.py.

Public entry point
------------------
``create_truncated_dashboard(data)``

    *data* is a plain dict whose keys correspond 1-to-1 to the positional /
    keyword arguments of the original method.  See ``_DEFAULTS`` below for
    the complete list of expected keys and their defaults.

The function delegates back to a lightweight shim instance of
``IsotopeDashboardGenerator`` so that all original HTML is reproduced
verbatim.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Key catalogue with defaults — mirrors the signature of
# create_truncated_html_dashboard
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    # Running and previous-week isotope data
    "ga_running": [],
    "ga_previous": [],
    "rb_running": [],
    "rb_previous": [],
    "in_running": [],
    "in_previous": [],
    "tl_running": [],
    "tl_previous": [],
    "io_running": [],
    "io_previous": [],
    # Efficiency KPI
    "efficiency_weeks": [],
    "efficiency_average": 0.0,
    "efficiency_last_year_avg": 0.0,
    "efficiency_last_3months_avg": 0.0,
    # Within-spec KPI
    "within_spec_weeks": [],
    "within_spec_average": 0.0,
    "within_spec_last_year_avg": 0.0,
    "within_spec_last_3months_avg": 0.0,
    # Shift statistics (used internally, defaults to empty)
    "shift_stats_this_week": {},
    "shift_stats_last_week": {},
    "this_week_friday": None,
    "last_week_friday": None,
    # Optional
    "tampering_warning": None,
    # OTIF gedraaide KPI
    "otif_gedraaide_weeks": None,
    "otif_gedraaide_average": 0.0,
    "otif_gedraaide_last_year_avg": 0.0,
    "otif_gedraaide_last_3months_avg": 0.0,
    # VSM data (not rendered in truncated version but forwarded for signature compat)
    "vsm_data": None,
}


def _unpack(data: dict) -> dict:
    """Merge *data* over ``_DEFAULTS`` and return the complete values dict."""
    result = dict(_DEFAULTS)
    result.update(data)
    return result


def create_truncated_dashboard(data: dict) -> str:
    """Render the truncated production dashboard HTML.

    Parameters
    ----------
    data:
        Dict containing all calculated values.  Unrecognised keys are
        ignored; missing keys fall back to the defaults defined in
        ``_DEFAULTS``.

    Returns
    -------
    str
        Complete ``<!DOCTYPE html>`` document as a string.  Contains only
        the KPI summary tables and the current/previous-week production
        tables — no isotope detail sections or chart sections.
    """
    from gallium_extractor import IsotopeDashboardGenerator

    v = _unpack(data)

    # Build a minimal shim instance — no database connections needed.
    gen = IsotopeDashboardGenerator.__new__(IsotopeDashboardGenerator)

    return gen.create_truncated_html_dashboard(
        v["ga_running"],   v["ga_previous"],
        v["rb_running"],   v["rb_previous"],
        v["in_running"],   v["in_previous"],
        v["tl_running"],   v["tl_previous"],
        v["io_running"],   v["io_previous"],
        v["efficiency_weeks"],        v["efficiency_average"],
        v["efficiency_last_year_avg"], v["efficiency_last_3months_avg"],
        v["within_spec_weeks"],       v["within_spec_average"],
        v["within_spec_last_year_avg"], v["within_spec_last_3months_avg"],
        v["shift_stats_this_week"],   v["shift_stats_last_week"],
        v["this_week_friday"],        v["last_week_friday"],
        tampering_warning               = v["tampering_warning"],
        otif_gedraaide_weeks            = v["otif_gedraaide_weeks"],
        otif_gedraaide_average          = v["otif_gedraaide_average"],
        otif_gedraaide_last_year_avg    = v["otif_gedraaide_last_year_avg"],
        otif_gedraaide_last_3months_avg = v["otif_gedraaide_last_3months_avg"],
        vsm_data                        = v["vsm_data"],
    )
