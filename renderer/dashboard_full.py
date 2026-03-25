"""
renderer/dashboard_full.py
---------------------------
Full-dashboard renderer — standalone implementation, no dependency on
gallium_extractor.IsotopeDashboardGenerator.

Public entry point
------------------
``create_html_dashboard(data)``

    *data* is a plain dict whose keys correspond 1-to-1 to the positional /
    keyword arguments of the original method.  See ``_DEFAULTS`` below for
    the complete list of expected keys and their defaults.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from config.spec_settings import (
    get_targetstroom_color,
    get_efficiency_color,
    get_iodine_yield_color,
    get_iodine_output_color,
    get_iodine_targetstroom_color,
)
from renderer.helpers import (
    build_week_table_rows,
    generate_leaderboard_html,
    generate_monthly_winner_html,
    generate_shift_tables_html,
    generate_ploeg_rolling_charts_html,
)
from renderer.gantt import generate_gantt_chart_html


# ---------------------------------------------------------------------------
# Stub for get_saved_comment — no live DB connection in the renderer
# ---------------------------------------------------------------------------

def _get_saved_comment(isotope_name, date, identifier):
    """Return the saved comment for a production record, or empty string."""
    return ""


# ---------------------------------------------------------------------------
# Key catalogue with defaults
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
    # Storingen data
    "iba_storingen_data": [],
    "philips_storingen_data": [],
    # OTIF KPI / table data
    "otif_kpi_data": [],
    "otif_table_data": {},
    # Ploegen definitions
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
    """
    v = _unpack(data)

    # Unpack all values from the dict
    ga_running       = v["ga_running"]
    ga_monthly       = v["ga_monthly"]
    ga_previous      = v["ga_previous"]
    rb_running       = v["rb_running"]
    rb_monthly       = v["rb_monthly"]
    rb_previous      = v["rb_previous"]
    in_running       = v["in_running"]
    in_monthly       = v["in_monthly"]
    in_previous      = v["in_previous"]
    tl_running       = v["tl_running"]
    tl_monthly_12    = v["tl_monthly_12"]
    tl_monthly_21    = v["tl_monthly_21"]
    tl_previous      = v["tl_previous"]
    io_running       = v["io_running"]
    io_monthly       = v["io_monthly"]
    io_previous      = v["io_previous"]

    efficiency_weeks            = v["efficiency_weeks"]
    efficiency_average          = v["efficiency_average"]
    efficiency_last_year_avg    = v["efficiency_last_year_avg"]
    efficiency_last_3months_avg = v["efficiency_last_3months_avg"]
    efficiency_past_year        = v["efficiency_past_year"]
    efficiency_all_time         = v["efficiency_all_time"]

    within_spec_weeks            = v["within_spec_weeks"]
    within_spec_average          = v["within_spec_average"]
    within_spec_last_year_avg    = v["within_spec_last_year_avg"]
    within_spec_last_3months_avg = v["within_spec_last_3months_avg"]
    within_spec_past_year        = v["within_spec_past_year"]
    within_spec_all_time         = v["within_spec_all_time"]

    issue_counts   = v["issue_counts"]
    isotope_issues = v["isotope_issues"]

    gallium_eff_weeks    = v["gallium_eff_weeks"]
    gallium_eff_avg      = v["gallium_eff_avg"]
    gallium_eff_all_time = v["gallium_eff_all_time"]
    gallium_eff_year     = v["gallium_eff_year"]
    gallium_eff_3months  = v["gallium_eff_3months"]

    indium_eff_weeks    = v["indium_eff_weeks"]
    indium_eff_avg      = v["indium_eff_avg"]
    indium_eff_all_time = v["indium_eff_all_time"]
    indium_eff_year     = v["indium_eff_year"]
    indium_eff_3months  = v["indium_eff_3months"]

    rubidium_eff_weeks    = v["rubidium_eff_weeks"]
    rubidium_eff_avg      = v["rubidium_eff_avg"]
    rubidium_eff_all_time = v["rubidium_eff_all_time"]
    rubidium_eff_year     = v["rubidium_eff_year"]
    rubidium_eff_3months  = v["rubidium_eff_3months"]

    iodine_eff_weeks    = v["iodine_eff_weeks"]
    iodine_eff_avg      = v["iodine_eff_avg"]
    iodine_eff_all_time = v["iodine_eff_all_time"]
    iodine_eff_year     = v["iodine_eff_year"]
    iodine_eff_3months  = v["iodine_eff_3months"]

    shift_stats_this_week = v["shift_stats_this_week"]
    shift_stats_last_week = v["shift_stats_last_week"]
    this_week_friday      = v["this_week_friday"]
    last_week_friday      = v["last_week_friday"]

    ploeg_6month    = v["ploeg_6month"]
    ploeg_3month    = v["ploeg_3month"]
    ploeg_monthly   = v["ploeg_monthly"]
    ploeg_rolling   = v["ploeg_rolling"]
    leaderboard     = v["leaderboard"]
    monthly_winner  = v["monthly_winner"]

    tampering_warning        = v["tampering_warning"]
    ploeg_production_details = v["ploeg_production_details"]
    production_history       = v["production_history"]
    cyclotron_data           = v["cyclotron_data"]

    otif_gedraaide_weeks            = v["otif_gedraaide_weeks"]
    otif_gedraaide_average          = v["otif_gedraaide_average"]
    otif_gedraaide_last_year_avg    = v["otif_gedraaide_last_year_avg"]
    otif_gedraaide_last_3months_avg = v["otif_gedraaide_last_3months_avg"]

    vsm_data                    = v["vsm_data"]
    planning_html_content       = v["planning_html_content"]
    productieschema_html_content = v["productieschema_html_content"]

    # Instance-attribute data (passed via dict, not self.*)
    iba_storingen_data    = list(v["iba_storingen_data"])
    philips_storingen_data = list(v["philips_storingen_data"])
    otif_kpi_data         = v["otif_kpi_data"]
    otif_table_data       = v["otif_table_data"]
    ploegen_data          = v["ploegen_data"]

    # ------------------------------------------------------------------
    # Original method body follows — all self.* replaced with standalone
    # ------------------------------------------------------------------
    """Create HTML dashboard with all visualizations"""

    # Create summary table for CURRENT week
    # Separate Thallium by kant
    tl_running_12 = [t for t in tl_running if t.get('kant') == '1.2']
    tl_running_21 = [t for t in tl_running if t.get('kant') == '2.1']

    summary_table_rows = build_week_table_rows(
        ga_running, rb_running, in_running, tl_running_12, tl_running_21, io_running,
        with_onclick=True)

    summary_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid #FF5722;">Lopende week</h2>
        <table>
            <thead>
                <tr style="font-size: 18px; font-weight: bold;">
                    <th>Gallium (µA)</th>
                    <th>Rubidium (% + µA)</th>
                    <th>Indium (µA)</th>
                    <th>Thallium 1.2 (µA)</th>
                    <th>Thallium 2.1 (µA)</th>
                    <th>Iodine (Yield%/Output% + µA)</th>
                </tr>
            </thead>
            <tbody>
                {summary_table_rows if summary_table_rows else '<tr><td colspan="6">No data available</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    # Create summary table for PREVIOUS week
    # Separate Thallium by kant
    tl_previous_12 = [t for t in tl_previous if t.get('kant') == '1.2']
    tl_previous_21 = [t for t in tl_previous if t.get('kant') == '2.1']

    summary_table_rows_prev = build_week_table_rows(
        ga_previous, rb_previous, in_previous, tl_previous_12, tl_previous_21, io_previous,
        with_onclick=True)

    previous_week_summary_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid #9C27B0;">Afgelopen week</h2>
        <table>
            <thead>
                <tr style="font-size: 18px; font-weight: bold;">
                    <th>Gallium (µA)</th>
                    <th>Rubidium (% + µA)</th>
                    <th>Indium (µA)</th>
                    <th>Thallium 1.2 (µA)</th>
                    <th>Thallium 2.1 (µA)</th>
                    <th>Iodine (Yield%/Output% + µA)</th>
                </tr>
            </thead>
            <tbody>
                {summary_table_rows_prev if summary_table_rows_prev else '<tr><td colspan="6">No data available</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    # Create efficiency table at the very top
    efficiency_week_headers = ""
    efficiency_percentage_cells = ""

    for week_data in efficiency_weeks:
        efficiency_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            efficiency_percentage_cells += f"<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-‌%</td>"
        else:
            efficiency_percentage_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"

    efficiency_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Efficiëntie Bronfaraday → Targets</h2>
        <table>
            <thead>
                <tr>
                    {efficiency_week_headers if efficiency_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {efficiency_percentage_cells if efficiency_percentage_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {efficiency_average:.1f}%</span>
            <span style="color: {'#3BB143' if efficiency_last_year_avg >= efficiency_average else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {efficiency_last_year_avg:.1f}%</span>
            <span style="color: {'#3BB143' if efficiency_last_3months_avg >= efficiency_last_year_avg else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {efficiency_last_3months_avg:.1f}%</span>
        </div>
    </div>
    """

    # Create within-spec table
    within_spec_week_headers = ""
    within_spec_percentage_cells = ""

    for week_data in within_spec_weeks:
        within_spec_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            within_spec_percentage_cells += f"<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-‌%</td>"
        else:
            within_spec_percentage_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"

    within_spec_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Success rate (% Binnen Spec)</h2>
        <table>
            <thead>
                <tr>
                    {within_spec_week_headers if within_spec_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {within_spec_percentage_cells if within_spec_percentage_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {within_spec_average:.1f}%</span>
            <span style="color: {'#3BB143' if within_spec_last_year_avg >= within_spec_average else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {within_spec_last_year_avg:.1f}%</span>
            <span style="color: {'#3BB143' if within_spec_last_3months_avg >= within_spec_last_year_avg else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {within_spec_last_3months_avg:.1f}%</span>
        </div>
    </div>
    """

    # Build OTIF gedraaide producties table
    _otif_ged_weeks = otif_gedraaide_weeks or []
    otif_ged_week_headers = ""
    otif_ged_percentage_cells = ""
    for week_data in _otif_ged_weeks:
        otif_ged_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            otif_ged_percentage_cells += f"<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-‌%</td>"
        else:
            otif_ged_percentage_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"

    otif_gedraaide_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">OTIF gedraaide producties</h2>
        <p style="color: grey; font-size: 13px; margin-top: -8px; margin-bottom: 10px;">niet gemaakte producties worden buiten beschouwing gelaten</p>
        <table>
            <thead>
                <tr>
                    {otif_ged_week_headers if otif_ged_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {otif_ged_percentage_cells if otif_ged_percentage_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {otif_gedraaide_average:.1f}%</span>
            <span style="color: {'#3BB143' if otif_gedraaide_last_year_avg >= 97 else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {otif_gedraaide_last_year_avg:.1f}%</span>
            <span style="color: {'#3BB143' if otif_gedraaide_last_3months_avg >= 97 else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {otif_gedraaide_last_3months_avg:.1f}%</span>
        </div>
    </div>
    """

    # Generate Gantt chart HTML (if cyclotron data available)
    gantt_chart_html = ""
    if cyclotron_data:
        gantt_chart_html = generate_gantt_chart_html(cyclotron_data)

    # Create Gallium production efficiency table (mCi/µAh)
    gallium_eff_week_headers = ""
    gallium_eff_value_cells = ""

    for week_data in reversed(gallium_eff_weeks):
        gallium_eff_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        gallium_eff_value_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['efficiency']:.2f}mCi/µAh</td>"

    gallium_production_efficiency_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Gallium Production Efficiency (mCi/µAh)</h2>
        <table>
            <thead>
                <tr>
                    {gallium_eff_week_headers if gallium_eff_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {gallium_eff_value_cells if gallium_eff_value_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {gallium_eff_all_time:.2f}mCi/µAh</span>
            <span style="color: {'#3BB143' if gallium_eff_year >= gallium_eff_all_time else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {gallium_eff_year:.2f}mCi/µAh</span>
            <span style="color: {'#3BB143' if gallium_eff_3months >= gallium_eff_year else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {gallium_eff_3months:.2f}mCi/µAh</span>
        </div>
    </div>
    """

    # Create Indium production efficiency table (mCi/µAh)
    indium_eff_week_headers = ""
    indium_eff_value_cells = ""

    for week_data in reversed(indium_eff_weeks):
        indium_eff_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        indium_eff_value_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['efficiency']:.2f}mCi/µAh</td>"

    indium_production_efficiency_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Indium Production Efficiency (mCi/µAh)</h2>
        <table>
            <thead>
                <tr>
                    {indium_eff_week_headers if indium_eff_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {indium_eff_value_cells if indium_eff_value_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {indium_eff_all_time:.2f}mCi/µAh</span>
            <span style="color: {'#3BB143' if indium_eff_year >= indium_eff_all_time else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {indium_eff_year:.2f}mCi/µAh</span>
            <span style="color: {'#3BB143' if indium_eff_3months >= indium_eff_year else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {indium_eff_3months:.2f}mCi/µAh</span>
        </div>
    </div>
    """

    # Create Rubidium production efficiency table (mCi/µAh)
    rubidium_eff_week_headers = ""
    rubidium_eff_value_cells = ""

    for week_data in reversed(rubidium_eff_weeks):
        rubidium_eff_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        rubidium_eff_value_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['efficiency']:.2f}mCi/µAh</td>"

    rubidium_production_efficiency_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Rubidium Production Efficiency (mCi/µAh)</h2>
        <table>
            <thead>
                <tr>
                    {rubidium_eff_week_headers if rubidium_eff_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {rubidium_eff_value_cells if rubidium_eff_value_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {rubidium_eff_all_time:.2f}mCi/µAh</span>
            <span style="color: {'#3BB143' if rubidium_eff_year >= rubidium_eff_all_time else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {rubidium_eff_year:.2f}mCi/µAh</span>
            <span style="color: {'#3BB143' if rubidium_eff_3months >= rubidium_eff_year else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {rubidium_eff_3months:.2f}mCi/µAh</span>
        </div>
    </div>
    """

    # Create Iodine production efficiency table (mCi/µAh)
    iodine_eff_week_headers = ""
    iodine_eff_value_cells = ""

    for week_data in reversed(iodine_eff_weeks):
        iodine_eff_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        # Display as mCi/µAh with 2 decimal places (matching other isotopes)
        iodine_eff_value_cells += f"<td style='text-align: center; color: {week_data['color']}; font-weight: bold; font-size: 20px;'>{week_data['efficiency']:.2f} mCi/µAh</td>"

    iodine_production_efficiency_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Iodine Production Efficiency (mCi/µAh)</h2>
        <table>
            <thead>
                <tr>
                    {iodine_eff_week_headers if iodine_eff_week_headers else '<th>No data available</th>'}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {iodine_eff_value_cells if iodine_eff_value_cells else '<td>No data available</td>'}
                </tr>
            </tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">All-time average: {iodine_eff_all_time:.2f} mCi/µAh</span>
            <span style="color: {'#3BB143' if iodine_eff_year >= iodine_eff_all_time else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last year average: {iodine_eff_year:.2f} mCi/µAh</span>
            <span style="color: {'#3BB143' if iodine_eff_3months >= iodine_eff_year else '#FF2400'}; font-weight: bold; margin-left: 20px;">Last 3 months average: {iodine_eff_3months:.2f} mCi/µAh</span>
        </div>
    </div>
    """

    # Create IBA Storingen table
    # Get SF code counts and production details from all production data
    sf_counts, sf_productions = ({}, {})

    # Add counts to IBA storingen data and prepare for sorting
    for record in iba_storingen_data:
        storingsnummer = record.get('storingsnummer', '')
        # Extract just the number part from storingsnummer (could be "SF0042", "0042", or "42")
        match = re.search(r'(\d+)', str(storingsnummer))
        if match:
            number_part = match.group(1)
            record['count'] = sf_counts.get(number_part, 0)
        else:
            record['count'] = 0

    # Sort by count (descending), then by date (descending)
    def sort_key(record):
        count = record.get('count', 0)
        datum = record.get('datum', '')
        # Empty dates should sort last within same count
        if not datum:
            datum = '0000-00-00'
        return (count, datum)  # No negation needed with reverse=True
    iba_storingen_data.sort(key=sort_key, reverse=True)

    storingen_table_rows = ""
    for record in iba_storingen_data:
        storingsnummer = record.get('storingsnummer', '-')
        datum = record.get('datum', '-')
        storing = record.get('storing', '-')
        count = record.get('count', 0)

        # Get the number part for SF lookup
        match = re.search(r'(\d+)', str(storingsnummer))
        number_part = match.group(1) if match else ''

        # Make count clickable if > 0
        if count > 0 and number_part:
            count_cell = f'<td style="text-align: center; font-weight: bold; cursor: pointer; color: #662678; text-decoration: underline;" onclick="showSFModal(\'{number_part}\', {count})">{count}</td>'
        else:
            count_cell = f'<td style="text-align: center; font-weight: bold;">{count}</td>'

        storingen_table_rows += f"""
            <tr>
                <td>{storingsnummer}</td>
                <td>{datum}</td>
                {count_cell}
                <td>{storing}</td>
            </tr>
        """

    iba_storingen_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid #9C27B0;">Lopende storingen IBA</h2>
        <table>
            <thead>
                <tr style="font-size: 18px; font-weight: bold;">
                    <th style="width: 12%;">Storingsnummer</th>
                    <th style="width: 12%;">Datum</th>
                    <th style="width: 8%;">Verstoorde producties</th>
                    <th style="width: 68%;">Storing</th>
                </tr>
            </thead>
            <tbody>
                {storingen_table_rows if storingen_table_rows else '<tr><td colspan="4">No data available</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    # Create Philips Storingen table
    # Add counts to Philips storingen data and prepare for sorting
    for record in philips_storingen_data:
        storingsnummer = record.get('storingsnummer', '')
        # Extract just the number part from storingsnummer (could be "SF0042", "0042", or "42")
        match = re.search(r'(\d+)', str(storingsnummer))
        if match:
            number_part = match.group(1)
            record['count'] = sf_counts.get(number_part, 0)
        else:
            record['count'] = 0

    # Sort by count (descending), then by date (descending)
    def sort_key(record):
        count = record.get('count', 0)
        datum = record.get('datum', '')
        # Empty dates should sort last within same count
        if not datum:
            datum = '0000-00-00'
        return (count, datum)  # No negation needed with reverse=True
    philips_storingen_data.sort(key=sort_key, reverse=True)

    philips_storingen_table_rows = ""
    for record in philips_storingen_data:
        storingsnummer = record.get('storingsnummer', '-')
        datum = record.get('datum', '-')
        storing = record.get('storing', '-')
        count = record.get('count', 0)

        # Get the number part for SF lookup
        match = re.search(r'(\d+)', str(storingsnummer))
        number_part = match.group(1) if match else ''

        # Make count clickable if > 0
        if count > 0 and number_part:
            count_cell = f'<td style="text-align: center; font-weight: bold; cursor: pointer; color: #662678; text-decoration: underline;" onclick="showSFModal(\'{number_part}\', {count})">{count}</td>'
        else:
            count_cell = f'<td style="text-align: center; font-weight: bold;">{count}</td>'

        philips_storingen_table_rows += f"""
            <tr>
                <td>{storingsnummer}</td>
                <td>{datum}</td>
                {count_cell}
                <td>{storing}</td>
            </tr>
        """

    philips_storingen_table = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid #9C27B0;">Lopende storingen Philips</h2>
        <table>
            <thead>
                <tr style="font-size: 18px; font-weight: bold;">
                    <th style="width: 12%;">Storingsnummer</th>
                    <th style="width: 12%;">Datum</th>
                    <th style="width: 8%;">Verstoorde producties</th>
                    <th style="width: 68%;">Storing</th>
                </tr>
            </thead>
            <tbody>
                {philips_storingen_table_rows if philips_storingen_table_rows else '<tr><td colspan="4">No data available</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    # ── OTIF Cyclotron section ─────────────────────────────────────────────
    # Scroll preservation + auto-reload JS (always injected, regardless of OTIF data)
    scroll_refresh_js = """
    (function() {
        function saveScrollPositions() {
            sessionStorage.setItem('_scrollY', String(window.pageYOffset));
            var otifTable = document.getElementById('otifTableScroll');
            if (otifTable) {
                sessionStorage.setItem('_otifScrollLeft', String(otifTable.scrollLeft));
                sessionStorage.setItem('_otifScrollSet', '1');
            }
        }
        function restoreScrollPositions() {
            var savedY = sessionStorage.getItem('_scrollY');
            if (savedY !== null) { window.scrollTo(0, parseInt(savedY, 10)); }
            var otifTable = document.getElementById('otifTableScroll');
            if (otifTable) {
                if (sessionStorage.getItem('_otifScrollSet') === '1') {
                    var savedLeft = sessionStorage.getItem('_otifScrollLeft');
                    otifTable.scrollLeft = savedLeft !== null ? parseInt(savedLeft, 10) : otifTable.scrollWidth;
                } else {
                    otifTable.scrollLeft = otifTable.scrollWidth;
                }
            }
        }
        function anyModalOpen() {
            var modalIds = ['ploegModal', 'dosisModal', 'sfModal', 'productionModal', 'dmVsmModal', 'roosterModal', 'productieschemaModal'];
            for (var i = 0; i < modalIds.length; i++) {
                var el = document.getElementById(modalIds[i]);
                if (el && el.style.display !== 'none' && el.style.display !== '') return true;
            }
            return false;
        }
        function scheduleReload() {
            setTimeout(function() {
                if (anyModalOpen()) {
                    // A modal is open — check again in 5 seconds
                    scheduleReload();
                } else {
                    saveScrollPositions();
                    location.reload();
                }
            }, 60000);
        }
        window.addEventListener('DOMContentLoaded', restoreScrollPositions);
        window.addEventListener('beforeunload', saveScrollPositions);
        scheduleReload();
    })();
    """
    otif_section_html = ""
    otif_charts_js = ""
    try:
        if otif_kpi_data or otif_table_data:
            # ── scrollable missed-orders table ────────────────────────────
            all_isotopes_order = ["Gallium", "I-123", "Indium", "Thallium", "Krypton"]

            all_weeks_set = set()
            for _weeks in otif_table_data.values():
                all_weeks_set.update(_weeks.keys())

            def _wkey(w):
                try:
                    y, wn = w.split('W')
                    return (int(y), int(wn))
                except Exception:
                    return (0, 0)

            all_otif_weeks = sorted(all_weeks_set, key=_wkey)

            # Normalize all keys to consistent "YYYYWww" format (no zero-padding)
            # and fill any gaps between first and last week
            if all_otif_weeks:
                def _next_iso_week(yr, wn):
                    d = date.fromisocalendar(yr, wn, 1) + timedelta(weeks=1)
                    iso = d.isocalendar()
                    return iso[0], iso[1]

                # Build normalized lookup: canonical_key -> data (merging any zero/non-zero padded duplicates)
                normalized_table_data = {}
                for _iso, _wk_dict in otif_table_data.items():
                    norm_iso = {}
                    for _k, _v in _wk_dict.items():
                        _tup = _wkey(_k)
                        if _tup == (0, 0):
                            continue
                        _nk = f"{_tup[0]}W{_tup[1]}"
                        norm_iso[_nk] = norm_iso.get(_nk, 0) + _v
                    normalized_table_data[_iso] = norm_iso

                # Build gap-filled week list: from earliest data up to current production week
                valid_tuples = [_wkey(w) for w in all_otif_weeks if _wkey(w) != (0, 0)]
                min_tup = min(valid_tuples)
                # Current production week = ISO week of this week's Thursday
                _today = datetime.now().date()
                _days_since_friday = (_today.weekday() - 4) % 7
                _current_thursday = _today - timedelta(days=_days_since_friday) + timedelta(days=6)
                _cy, _cw, _ = _current_thursday.isocalendar()
                max_tup = max(max(valid_tuples), (_cy, _cw))
                filled = []
                cur = min_tup
                while cur <= max_tup:
                    filled.append(f"{cur[0]}W{cur[1]}")
                    cur = _next_iso_week(*cur)
                all_otif_weeks = filled
            else:
                normalized_table_data = {k: {} for k in otif_table_data}

            # header row
            hdr = ('<th style="position:sticky;left:0;background:linear-gradient(135deg,#662678,#E40D7E);'
                   'z-index:2;min-width:120px;padding:10px;text-align:left;'
                   'border:1px solid #555;color:white;font-weight:bold;">Isotoop</th>')
            for w in all_otif_weeks:
                hdr += (f'<th style="min-width:80px;padding:8px;text-align:center;'
                        f'border:1px solid #555;white-space:nowrap;color:white;font-weight:bold;">{w}</th>')

            # body rows
            tbl_rows = ""
            for idx, isotope in enumerate(all_isotopes_order):
                bg = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
                row_html = (f'<tr style="background-color:{bg};">'
                            f'<td style="position:sticky;left:0;background-color:{bg};'
                            f'font-weight:bold;padding:10px;border:1px solid #ddd;z-index:1;">{isotope}</td>')
                wk_data = normalized_table_data.get(isotope, {})
                for w in all_otif_weeks:
                    val = wk_data.get(w, 0)
                    if val > 0:
                        cs = "padding:8px;text-align:center;border:1px solid #ddd;font-weight:bold;color:#E40D7E;"
                        display = str(val)
                    else:
                        cs = "padding:8px;text-align:center;border:1px solid #ddd;color:#aaa;"
                        display = "-"
                    row_html += f'<td style="{cs}">{display}</td>'
                row_html += '</tr>'
                tbl_rows += row_html

            # totals row
            if all_otif_weeks:
                total_row = ('<tr style="background:linear-gradient(135deg,#662678,#E40D7E);">'
                             '<td style="position:sticky;left:0;background:#662678;'
                             'font-weight:bold;padding:10px;border:1px solid #555;'
                             'color:white;z-index:1;">Totaal</td>')
                for w in all_otif_weeks:
                    week_total = sum(
                        normalized_table_data.get(iso, {}).get(w, 0)
                        for iso in all_isotopes_order
                    )
                    if week_total > 0:
                        cs = "padding:8px;text-align:center;border:1px solid #555;font-weight:bold;color:white;"
                    else:
                        cs = "padding:8px;text-align:center;border:1px solid #555;color:rgba(255,255,255,0.4);"
                    display = str(week_total)
                    total_row += f'<td style="{cs}">{display}</td>'
                total_row += '</tr>'
                tbl_rows += total_row

            if not all_otif_weeks:
                tbl_rows = '<tr><td colspan="2" style="padding:10px;color:#999;">No data available</td></tr>'
                hdr = '<th>Isotoop</th>'

            # ── KPI chart data ────────────────────────────────────────────
            kpi_labels    = [d['week'] for d in otif_kpi_data]
            ga_kpi        = [d.get('gallium')          for d in otif_kpi_data]
            i123_kpi      = [d.get('i123')             for d in otif_kpi_data]
            in_kpi        = [d.get('indium')           for d in otif_kpi_data]
            tl_kpi        = [d.get('thallium')         for d in otif_kpi_data]
            rb_kpi        = [d.get('rubidium_krypton') for d in otif_kpi_data]
            avg_kpi = []
            for d in otif_kpi_data:
                vals = [d.get(k) for k in
                        ('gallium', 'i123', 'indium', 'thallium', 'rubidium_krypton')
                        if d.get(k) is not None]
                avg_kpi.append(round(sum(vals) / len(vals), 1) if vals else None)

            otif_section_html = f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid #9C27B0;">OTIF Cyclotron</h2>

        <h3 style="margin-bottom:10px;">Gemiste orders per isotoop per week</h3>
        <div style="overflow-x:auto;border:1px solid #ddd;border-radius:4px;margin-bottom:30px;" id="otifTableScroll">
            <table style="border-collapse:collapse;min-width:100%;font-size:14px;">
                <thead>
                    <tr style="background:linear-gradient(135deg,#662678,#E40D7E);">
                        {hdr}
                    </tr>
                </thead>
                <tbody>
                    {tbl_rows}
                </tbody>
            </table>
        </div>

        <h3 style="margin-bottom:10px;">OTIF % per isotoop (afgelopen 52 weken)</h3>
        <div class="chart-row-three">
            <div class="section">
                <h3>Gallium</h3>
                <div class="chart-container"><canvas id="otifGaChart"></canvas></div>
            </div>
            <div class="section">
                <h3>I-123</h3>
                <div class="chart-container"><canvas id="otifI123Chart"></canvas></div>
            </div>
            <div class="section">
                <h3>Indium</h3>
                <div class="chart-container"><canvas id="otifInChart"></canvas></div>
            </div>
        </div>
        <div class="chart-row-three">
            <div class="section">
                <h3>Thallium</h3>
                <div class="chart-container"><canvas id="otifTlChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Rubidium / Krypton</h3>
                <div class="chart-container"><canvas id="otifRbChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Gemiddelde (alle isotopen)</h3>
                <div class="chart-container"><canvas id="otifAvgChart"></canvas></div>
            </div>
        </div>
    </div>
    """

            otif_charts_js = f"""
    // ── OTIF KPI Charts ────────────────────────────────────────────────
    (function() {{
        var otifLabels = {json.dumps(kpi_labels)};
        var otifOpts = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: true, position: 'top' }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                y: {{
                    min: 0, max: 100,
                    ticks: {{ callback: function(v) {{ return v + '%'; }} }},
                    title: {{ display: true, text: 'OTIF %' }}
                }},
                x: {{ ticks: {{ maxRotation: 45, minRotation: 45 }} }}
            }}
        }};
        function otifLine(id, label, data, color) {{
            var el = document.getElementById(id);
            if (!el) return;
            new Chart(el, {{
                type: 'line',
                data: {{
                    labels: otifLabels,
                    datasets: [{{
                        label: label,
                        data: data,
                        borderColor: color,
                        backgroundColor: color.replace('1)', '0.15)'),
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        spanGaps: true
                    }}]
                }},
                options: otifOpts
            }});
        }}
        otifLine('otifGaChart',   'Gallium %',          {json.dumps(ga_kpi)},   'rgba(76, 175, 80, 1)');
        otifLine('otifI123Chart', 'I-123 %',            {json.dumps(i123_kpi)}, 'rgba(33, 150, 243, 1)');
        otifLine('otifInChart',   'Indium %',           {json.dumps(in_kpi)},   'rgba(255, 87, 34, 1)');
        otifLine('otifTlChart',   'Thallium %',         {json.dumps(tl_kpi)},   'rgba(156, 39, 176, 1)');
        otifLine('otifRbChart',   'Rubidium/Krypton %', {json.dumps(rb_kpi)},   'rgba(255, 152, 0, 1)');
        otifLine('otifAvgChart',  'Gemiddelde %',       {json.dumps(avg_kpi)},  'rgba(102, 38, 120, 1)');
    }})();
    """
    except Exception as _otif_err:
        print(f"⚠ Warning: Could not generate OTIF section: {_otif_err}")
        traceback.print_exc()

    # Helper function to create table rows for targetstroom-based data with dropdown
    def create_targetstroom_rows(data, isotope_type, isotope_name):
        rows = ""
        for record in data:
            targetstroom = record.get('targetstroom')
            cyclotron = record.get('cyclotron', 'Philips')  # Get cyclotron type, default to Philips
            if targetstroom is not None:
                val = f"{targetstroom:.2f} µA"
                color = get_targetstroom_color(targetstroom, isotope_type, cyclotron)
                should_show_dropdown = (color == "#FF2400")  # Show dropdown if red
            else:
                val = "N/A"
                should_show_dropdown = False

            identifier = record.get('identifier', 'N/A') if record.get('identifier') else 'N/A'
            date = record['date']
            opmerking = record.get('opmerking', '-') if record.get('opmerking') else '-'

            # Create unique ID for dropdown
            dropdown_id = f"{isotope_name}_{date}_{identifier}".replace('.', '_').replace('-', '_').replace(' ', '_')

            # Get saved comment from database
            selected_value = _get_saved_comment(isotope_name, date, identifier)

            dropdown_html = ""
            if should_show_dropdown or selected_value:  # Show if red or has existing comment
                dropdown_html = f"""<select id="{dropdown_id}" onchange="saveComment('{isotope_name}', '{date}', '{identifier}', this.value)" style="width: 100%; padding: 5px;">
                        <option value="">Selecteer reden...</option>
                        <option value="Targetinstallatie storing" {'selected' if selected_value == 'Targetinstallatie storing' else ''}>Targetinstallatie storing</option>
                        <option value="Cyclotron storing" {'selected' if selected_value == 'Cyclotron storing' else ''}>Cyclotron storing</option>
                        <option value="Operator handelingen" {'selected' if selected_value == 'Operator handelingen' else ''}>Operator handelingen</option>
                        <option value="Verstoring RPP" {'selected' if selected_value == 'Verstoring RPP' else ''}>Verstoring RPP</option>
                        <option value="Verstoring onbekend" {'selected' if selected_value == 'Verstoring onbekend' else ''}>Verstoring onbekend</option>
                    </select>"""

            rows += f"""<tr>
                <td>{date}</td>
                <td>{identifier}</td>
                <td>{val}</td>
                <td>{opmerking}</td>
                <td>{dropdown_html}</td>
            </tr>
            """
        return rows if rows else '<tr><td colspan="5">No data available</td></tr>'

    # Helper function to create table rows for efficiency-based data with dropdown
    def create_efficiency_rows(data, col1_name, col2_name, id_name, isotope_name):
        rows = ""
        for record in data:
            eff = f"{record['efficiency']:.2f}%" if record.get('efficiency') is not None else "Missing"
            val1 = f"{record['value1']:.2f}" if record.get('value1') is not None else "N/A"
            val2 = f"{record['value2']:.2f}" if record.get('value2') is not None else "N/A"
            identifier = record.get('identifier', 'N/A') if record.get('identifier') else 'N/A'
            date = record['date']

            # Determine if dropdown should be shown
            color = get_efficiency_color(record.get('efficiency'))
            should_show_dropdown = (color == "#FF2400")  # Show dropdown if red

            # Create unique ID for dropdown
            dropdown_id = f"{isotope_name}_{date}_{identifier}".replace('.', '_').replace('-', '_').replace(' ', '_')

            # Get saved comment from database
            selected_value = _get_saved_comment(isotope_name, date, identifier)

            dropdown_html = ""
            if should_show_dropdown or selected_value:  # Show if red or has existing comment
                dropdown_html = f"""<select id="{dropdown_id}" onchange="saveComment('{isotope_name}', '{date}', '{identifier}', this.value)" style="width: 100%; padding: 5px;">
                        <option value="">Selecteer reden...</option>
                        <option value="Targetinstallatie storing" {'selected' if selected_value == 'Targetinstallatie storing' else ''}>Targetinstallatie storing</option>
                        <option value="Cyclotron storing" {'selected' if selected_value == 'Cyclotron storing' else ''}>Cyclotron storing</option>
                        <option value="Operator handelingen" {'selected' if selected_value == 'Operator handelingen' else ''}>Operator handelingen</option>
                        <option value="Verstoring RPP" {'selected' if selected_value == 'Verstoring RPP' else ''}>Verstoring RPP</option>
                        <option value="Verstoring onbekend" {'selected' if selected_value == 'Verstoring onbekend' else ''}>Verstoring onbekend</option>
                    </select>"""

            rows += f"""<tr>
                <td>{date}</td>
                <td>{identifier}</td>
                <td>{val1}</td>
                <td>{val2}</td>
                <td>{eff}</td>
                <td>{dropdown_html}</td>
            </tr>
            """
        return rows if rows else '<tr><td colspan="6">No data available</td></tr>'

    # Create table rows for each isotope
    ga_rows = create_targetstroom_rows(ga_running, 'gallium', 'Gallium')
    in_rows = create_targetstroom_rows(in_running, 'indium', 'Indium')

    # Thallium with Kant column
    tl_rows = ""
    for record in tl_running:
        targetstroom = record.get('targetstroom')
        rec_date = record['date']
        identifier = record.get('identifier', 'N/A') if record.get('identifier') else 'N/A'
        kant = record.get('kant', '')
        kant_display = '' if kant == 'Unknown' else kant
        opmerking = record.get('opmerking', '-') if record.get('opmerking') else '-'

        if targetstroom is not None:
            val = f"{targetstroom:.2f} µA"
            color = get_targetstroom_color(targetstroom, 'thallium')
            should_show_dropdown = (color == "#FF2400")
        else:
            val = "N/A"
            should_show_dropdown = False

        # Create unique ID for dropdown
        dropdown_id = f"Thallium_{rec_date}_{identifier}".replace('.', '_').replace('-', '_').replace(' ', '_')

        # Get saved comment from database
        selected_value = _get_saved_comment('Thallium', rec_date, identifier)

        dropdown_html = ""
        if should_show_dropdown or selected_value:
            dropdown_html = f"""<select id="{dropdown_id}" onchange="saveComment('Thallium', '{rec_date}', '{identifier}', this.value)" style="width: 100%; padding: 5px;">
                    <option value="">Selecteer reden...</option>
                    <option value="Targetinstallatie storing" {'selected' if selected_value == 'Targetinstallatie storing' else ''}>Targetinstallatie storing</option>
                    <option value="Cyclotron storing" {'selected' if selected_value == 'Cyclotron storing' else ''}>Cyclotron storing</option>
                    <option value="Operator handelingen" {'selected' if selected_value == 'Operator handelingen' else ''}>Operator handelingen</option>
                    <option value="Verstoring RPP" {'selected' if selected_value == 'Verstoring RPP' else ''}>Verstoring RPP</option>
                    <option value="Verstoring onbekend" {'selected' if selected_value == 'Verstoring onbekend' else ''}>Verstoring onbekend</option>
                </select>"""

        tl_rows += f"""<tr>
            <td>{rec_date}</td>
            <td>{identifier}</td>
            <td>{val}</td>
            <td>{kant_display}</td>
            <td>{opmerking}</td>
            <td>{dropdown_html}</td>
        </tr>
        """
    tl_rows = tl_rows if tl_rows else '<tr><td colspan="6">No data available</td></tr>'

    # Rubidium with stroom column
    rb_rows = ""
    for record in rb_running:
        rec_date = record['date']
        eff = f"{record['efficiency']:.2f}%" if record['efficiency'] is not None else "Missing"
        val1 = f"{record['value1']:.2f}" if record['value1'] is not None else "N/A"
        val2 = f"{record['value2']:.2f}" if record['value2'] is not None else "N/A"
        identifier = str(int(float(record.get('identifier')))) if record.get('identifier') is not None else 'N/A'
        stroom = f"{record.get('stroom'):.2f}" if record.get('stroom') is not None else "N/A"
        opmerking = record.get('opmerking', '-') if record.get('opmerking') else '-'

        # Determine if dropdown should be shown
        color = get_efficiency_color(record.get('efficiency'))
        should_show_dropdown = (color == "#FF2400")

        # Create unique ID for dropdown
        dropdown_id = f"Rubidium_{rec_date}_{identifier}".replace('.', '_').replace('-', '_').replace(' ', '_')

        # Get saved comment from database
        selected_value = _get_saved_comment('Rubidium', rec_date, identifier)

        dropdown_html = ""
        if should_show_dropdown or selected_value:
            dropdown_html = f"""<select id="{dropdown_id}" onchange="saveComment('Rubidium', '{rec_date}', '{identifier}', this.value)" style="width: 100%; padding: 5px;">
                    <option value="">Selecteer reden...</option>
                    <option value="Targetinstallatie storing" {'selected' if selected_value == 'Targetinstallatie storing' else ''}>Targetinstallatie storing</option>
                    <option value="Cyclotron storing" {'selected' if selected_value == 'Cyclotron storing' else ''}>Cyclotron storing</option>
                    <option value="Operator handelingen" {'selected' if selected_value == 'Operator handelingen' else ''}>Operator handelingen</option>
                    <option value="Verstoring RPP" {'selected' if selected_value == 'Verstoring RPP' else ''}>Verstoring RPP</option>
                    <option value="Verstoring onbekend" {'selected' if selected_value == 'Verstoring onbekend' else ''}>Verstoring onbekend</option>
                </select>"""

        rb_rows += f"""<tr>
            <td>{rec_date}</td>
            <td>{identifier}</td>
            <td>{val1}</td>
            <td>{val2}</td>
            <td>{stroom}</td>
            <td>{eff}</td>
            <td>{opmerking}</td>
            <td>{dropdown_html}</td>
        </tr>
        """
    rb_rows = rb_rows if rb_rows else '<tr><td colspan="8">No data available</td></tr>'

    # Iodine with BO Targetstroom and targetstroom columns
    io_rows = ""
    for record in io_running:
        rec_date = record['date']
        yield_pct = f"{record['yield_percent']:.1f}%" if record.get('yield_percent') is not None else "Missing"
        output_pct = f"{record['output_percent']:.1f}%" if record.get('output_percent') is not None else "Missing"
        val1 = f"{record['value1']:.2f}" if record['value1'] is not None else "N/A"
        val2 = f"{record['value2']:.2f}" if record['value2'] is not None else "N/A"
        identifier = str(int(float(record.get('identifier')))) if record.get('identifier') is not None and record.get('identifier') != 'TEST_NONE' else 'N/A'
        bo_target = f"{record.get('bo_targetstroom'):.2f}" if record.get('bo_targetstroom') is not None else "N/A"
        target = f"{record.get('targetstroom'):.2f}" if record.get('targetstroom') is not None else "N/A"
        opmerking = record.get('opmerking', '-') if record.get('opmerking') else '-'

        # Determine if dropdown should be shown (using Iodine-specific logic)
        yield_color = get_iodine_yield_color(record.get('yield_percent'))
        output_color = get_iodine_output_color(record.get('output_percent'))
        target_color = get_iodine_targetstroom_color(record.get('targetstroom'))
        should_show_dropdown = (yield_color == "#FF2400" or output_color == "#FF2400" or target_color == "#FF2400")

        # Create unique ID for dropdown
        dropdown_id = f"Iodine_{rec_date}_{identifier}".replace('.', '_').replace('-', '_').replace(' ', '_')

        # Get saved comment from database
        selected_value = _get_saved_comment('Iodine', rec_date, identifier)

        dropdown_html = ""
        if should_show_dropdown or selected_value:
            dropdown_html = f"""<select id="{dropdown_id}" onchange="saveComment('Iodine', '{rec_date}', '{identifier}', this.value)" style="width: 100%; padding: 5px;">
                    <option value="">Selecteer reden...</option>
                    <option value="Targetinstallatie storing" {'selected' if selected_value == 'Targetinstallatie storing' else ''}>Targetinstallatie storing</option>
                    <option value="Cyclotron storing" {'selected' if selected_value == 'Cyclotron storing' else ''}>Cyclotron storing</option>
                    <option value="Operator handelingen" {'selected' if selected_value == 'Operator handelingen' else ''}>Operator handelingen</option>
                    <option value="Verstoring RPP" {'selected' if selected_value == 'Verstoring RPP' else ''}>Verstoring RPP</option>
                    <option value="Verstoring onbekend" {'selected' if selected_value == 'Verstoring onbekend' else ''}>Verstoring onbekend</option>
                </select>"""

        io_rows += f"""<tr>
            <td>{rec_date}</td>
            <td>{identifier}</td>
            <td>{val1}</td>
            <td>{val2}</td>
            <td>{bo_target}</td>
            <td>{target}</td>
            <td>{yield_pct}</td>
            <td>{output_pct}</td>
            <td>{opmerking}</td>
            <td>{dropdown_html}</td>
        </tr>
        """
    io_rows = io_rows if io_rows else '<tr><td colspan="10">No data available</td></tr>'

    # Prepare chart data
    def prepare_efficiency_chart_data(monthly, running):
        monthly_labels = [m['month'] for m in monthly]
        monthly_data = [round(m['average'], 2) for m in monthly]
        running_labels = [p['date'] for p in running]
        running_data = [round(p['efficiency'], 2) if p.get('efficiency') is not None else None for p in running]
        running_identifiers = [str(p.get('identifier', '')) if p.get('identifier') else '' for p in running]
        monthly_max = max(monthly_data) + 5 if monthly_data else 110
        running_max = max([d for d in running_data if d is not None]) + 5 if any(d for d in running_data if d is not None) else 110
        return monthly_labels, monthly_data, running_labels, running_data, running_identifiers, monthly_max, running_max

    def prepare_targetstroom_chart_data(monthly, running, isotope_type):
        """Prepare chart data for targetstroom-based measurements"""
        monthly_labels = [m['month'] for m in monthly]
        monthly_data = [round(m['average'], 2) for m in monthly]
        running_labels = [p['date'] for p in running]
        running_data = [round(p.get('targetstroom'), 2) if p.get('targetstroom') is not None else None for p in running]
        running_identifiers = [str(p.get('identifier', '')) if p.get('identifier') else '' for p in running]

        # Set appropriate max values based on isotope type
        if isotope_type == 'thallium':
            monthly_max = max(monthly_data) + 10 if monthly_data else 190
            running_max = max([d for d in running_data if d is not None]) + 10 if any(d for d in running_data if d is not None) else 190
        else:  # gallium or indium
            monthly_max = max(monthly_data) + 10 if monthly_data else 100
            running_max = max([d for d in running_data if d is not None]) + 10 if any(d for d in running_data if d is not None) else 100

        return monthly_labels, monthly_data, running_labels, running_data, running_identifiers, monthly_max, running_max

    def prepare_rubidium_stroom_data(running):
        labels = [p['date'] for p in running]
        stroom_data = [round(p.get('stroom'), 2) if p.get('stroom') is not None else None for p in running]
        identifiers = [str(p.get('identifier', '')) if p.get('identifier') else '' for p in running]
        max_val = max([d for d in stroom_data if d is not None]) + 50 if any(d for d in stroom_data if d is not None) else 1000
        return labels, stroom_data, identifiers, max_val

    def prepare_iodine_chart_data(monthly, running):
        monthly_labels = [m['month'] for m in monthly]
        monthly_data = [round(m['average'], 2) for m in monthly]
        running_labels = [p['date'] for p in running]
        # Use yield_percent and output_percent instead of efficiency_raw and efficiency
        running_data_yield = [round(p['yield_percent'], 2) if p.get('yield_percent') is not None else None for p in running]
        running_data_output = [round(p['output_percent'], 2) if p.get('output_percent') is not None else None for p in running]
        running_identifiers = [str(p.get('identifier', '')) if p.get('identifier') else '' for p in running]
        monthly_max = max(monthly_data) + 5 if monthly_data else 110
        all_running = [d for d in running_data_yield + running_data_output if d is not None]
        running_max = max(all_running) + 5 if all_running else 110
        return monthly_labels, monthly_data, running_labels, running_data_yield, running_data_output, running_identifiers, monthly_max, running_max

    def prepare_iodine_targetstroom_data(running):
        labels = [p['date'] for p in running]
        bo_target_data = [round(p.get('bo_targetstroom'), 2) if p.get('bo_targetstroom') is not None else None for p in running]
        target_data = [round(p.get('targetstroom'), 2) if p.get('targetstroom') is not None else None for p in running]
        identifiers = [str(p.get('identifier', '')) if p.get('identifier') else '' for p in running]
        all_vals = [d for d in bo_target_data + target_data if d is not None]
        max_val = max(all_vals) + 50 if all_vals else 1000
        return labels, bo_target_data, target_data, identifiers, max_val

    def prepare_thallium_chart_data(monthly_12, monthly_21, running):
        """Prepare chart data for Thallium with kant separation"""
        # Monthly data - combine months from both kant values
        all_months = sorted(set([m['month'] for m in monthly_12] + [m['month'] for m in monthly_21]))
        monthly_labels = all_months

        # Create data arrays for both kant values
        monthly_data_12 = []
        monthly_data_21 = []
        for month in all_months:
            val_12 = next((m['average'] for m in monthly_12 if m['month'] == month), None)
            val_21 = next((m['average'] for m in monthly_21 if m['month'] == month), None)
            monthly_data_12.append(round(val_12, 2) if val_12 is not None else None)
            monthly_data_21.append(round(val_21, 2) if val_21 is not None else None)

        # Running week data
        running_labels = [p['date'] for p in running]
        running_data = [round(p.get('targetstroom'), 2) if p.get('targetstroom') is not None else None for p in running]
        running_identifiers = [str(p.get('identifier', '')) if p.get('identifier') else '' for p in running]
        # Don't show 'Unknown' in charts
        running_kant = [p.get('kant', '') if p.get('kant') != 'Unknown' else '' for p in running]

        # Calculate max values
        all_monthly = [d for d in monthly_data_12 + monthly_data_21 if d is not None]
        monthly_max = max(all_monthly) + 10 if all_monthly else 190
        running_max = max([d for d in running_data if d is not None]) + 10 if any(d for d in running_data if d is not None) else 190

        return monthly_labels, monthly_data_12, monthly_data_21, running_labels, running_data, running_identifiers, running_kant, monthly_max, running_max

    ga_mon_lab, ga_mon_dat, ga_run_lab, ga_run_dat, ga_run_id, ga_mon_max, ga_run_max = prepare_targetstroom_chart_data(ga_monthly, ga_running, 'gallium')
    rb_mon_lab, rb_mon_dat, rb_run_lab, rb_run_dat, rb_run_id, rb_mon_max, rb_run_max = prepare_efficiency_chart_data(rb_monthly, rb_running)
    in_mon_lab, in_mon_dat, in_run_lab, in_run_dat, in_run_id, in_mon_max, in_run_max = prepare_targetstroom_chart_data(in_monthly, in_running, 'indium')
    tl_mon_lab, tl_mon_dat_12, tl_mon_dat_21, tl_run_lab, tl_run_dat, tl_run_id, tl_run_kant, tl_mon_max, tl_run_max = prepare_thallium_chart_data(tl_monthly_12, tl_monthly_21, tl_running)
    io_mon_lab, io_mon_dat, io_run_lab, io_run_dat_yield, io_run_dat_output, io_run_id, io_mon_max, io_run_max = prepare_iodine_chart_data(io_monthly, io_running)

    # Additional chart data
    rb_stroom_lab, rb_stroom_dat, rb_stroom_id, rb_stroom_max = prepare_rubidium_stroom_data(rb_running)
    io_target_lab, io_bo_target_dat, io_target_dat, io_target_id, io_target_max = prepare_iodine_targetstroom_data(io_running)

    # Efficiency chart data
    eff_past_year_labels = [d['date'] for d in efficiency_past_year]
    eff_past_year_data = [round(d['efficiency'], 2) for d in efficiency_past_year]
    eff_past_year_max = max(eff_past_year_data) + 5 if eff_past_year_data else 30

    eff_all_time_labels = [d['date'] for d in efficiency_all_time]
    eff_all_time_data = [round(d['efficiency'], 2) for d in efficiency_all_time]
    eff_all_time_max = max(eff_all_time_data) + 5 if eff_all_time_data else 30

    # Within-spec chart data
    ws_past_year_labels = [d['date_str'] for d in within_spec_past_year]
    ws_past_year_data = [round(d['percentage'], 2) for d in within_spec_past_year]
    ws_past_year_max = 105  # Fixed max at 105%

    ws_all_time_labels = [d['date_str'] for d in within_spec_all_time]
    ws_all_time_data = [round(d['percentage'], 2) for d in within_spec_all_time]
    ws_all_time_max = 105  # Fixed max at 105%

    # Issue tracking chart data
    issue_categories = ['Targetinstallatie storing', 'Cyclotron storing', 'Operator handelingen', 'Verstoring RPP', 'Verstoring onbekend']

    issues_this_week_data = [issue_counts['this_week'].get(cat, 0) for cat in issue_categories]
    issues_last_week_data = [issue_counts['last_week'].get(cat, 0) for cat in issue_categories]
    issues_all_time_data = [issue_counts['all_time'].get(cat, 0) for cat in issue_categories]

    # Isotope comparison data
    isotope_names = list(isotope_issues.keys()) if isotope_issues else []
    isotope_counts = list(isotope_issues.values()) if isotope_issues else []

    # Build Productieschema srcdoc for embedding
    if productieschema_html_content:
        _ps_srcdoc = productieschema_html_content.replace('&', '&amp;').replace('"', '&quot;')
        productieschema_modal_content = f'<iframe srcdoc="{_ps_srcdoc}" style="width:100%;height:100%;border:none;" sandbox="allow-scripts allow-same-origin"></iframe>'
    else:
        productieschema_modal_content = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;font-size:18px;font-family:Arial,sans-serif;">⚠️ Productieschema HTML kon niet worden geladen. Controleer of het W:-station beschikbaar is.</div>'

    # Build Rooster en targetvoorraad srcdoc for embedding
    if planning_html_content:
        rooster_srcdoc = planning_html_content.replace('&', '&amp;').replace('"', '&quot;')
        rooster_modal_content = f'<iframe srcdoc="{rooster_srcdoc}" style="width:100%;height:100%;border:none;" sandbox="allow-scripts allow-same-origin"></iframe>'
    else:
        rooster_modal_content = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;font-size:18px;font-family:Arial,sans-serif;">⚠️ planning.html kon niet worden geladen. Controleer of het W:-station beschikbaar is.</div>'

    # Build VSM table HTML for the DM VSM modal
    if vsm_data and isinstance(vsm_data, dict) and vsm_data.get('rows'):
        _vsm_rows = vsm_data['rows']
        _vsm_week_avg = vsm_data.get('week_avg_otif')
        _vsm_header = (
            '<thead><tr>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:left;white-space:nowrap;">Datum</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Tl1</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Tl2</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Tl3</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Tl4</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Tl5</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Ga</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">In</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Rb</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">Rb</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">I123</th>'
            '<th style="background:#1a5276;color:white;padding:8px 12px;text-align:center;">OTIF%</th>'
            '</tr></thead>'
        )

        def _vsm_cell(val, target=None):
            if val is None:
                return '<td style="padding:7px 12px;text-align:center;color:#aaa;">—</td>'
            pct = (val / target * 100) if target else None
            if pct is not None and pct < 95:
                # Below target: red background, white bold text
                return f'<td style="padding:7px 12px;text-align:center;background:#c0392b;color:white;font-weight:bold;">{val}</td>'
            # At or above target: no fill
            return f'<td style="padding:7px 12px;text-align:center;">{val}</td>'

        def _vsm_otif_cell(val):
            if val is None:
                return '<td style="padding:7px 12px;text-align:center;color:#aaa;">—</td>'
            if val >= 97:
                return f'<td style="padding:7px 12px;text-align:center;font-weight:bold;background:#d4efdf;">{val:.1f}%</td>'
            else:
                return f'<td style="padding:7px 12px;text-align:center;font-weight:bold;background:#c0392b;color:white;">{val:.1f}%</td>'

        _vsm_body_rows = []
        for r in _vsm_rows:
            row_html = (
                f'<tr>'
                f'<td style="padding:7px 12px;white-space:nowrap;font-weight:bold;">{r["date"]}</td>'
                + _vsm_cell(r['tl1'], 170) + _vsm_cell(r['tl2'], 170)
                + _vsm_cell(r['tl3'], 170) + _vsm_cell(r['tl4'], 170)
                + _vsm_cell(r['tl5'], 170)
                + _vsm_cell(r['ga'], 80)
                + _vsm_cell(r['in_'], 80)
                + _vsm_cell(r['rb1'], 70) + _vsm_cell(r['rb2'], 70)
                + _vsm_cell(r['i123'], 100)
                + _vsm_otif_cell(r['otif'])
                + '</tr>'
            )
            _vsm_body_rows.append(row_html)

        # Week average row
        if _vsm_week_avg is not None:
            _avg_bg = '#d4efdf' if _vsm_week_avg >= 95 else ('#fef9e7' if _vsm_week_avg >= 80 else '#fadbd8')
            _vsm_body_rows.append(
                f'<tr style="border-top:2px solid #1a5276;">' +
                f'<td style="padding:7px 12px;font-weight:bold;background:#eaf4fc;">Otif week tot nu</td>' +
                '<td colspan="10" style="padding:7px 12px;background:#eaf4fc;"></td>' +
                f'<td style="padding:7px 12px;text-align:center;font-weight:bold;background:{_avg_bg};">{_vsm_week_avg:.1f}%</td></tr>'
            )

        vsm_table_html = (
            '<table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:14px;">' +
            _vsm_header +
            '<tbody>' + ''.join(_vsm_body_rows) + '</tbody>' +
            '</table>'
        )
    else:
        vsm_table_html = '<p style="color:#888;text-align:center;">VSM data niet beschikbaar.</p>'


    html = f"""<!DOCTYPE html>
    <!--
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                          ⚠️  WARNING  ⚠️                            ║
    ║                                                                      ║
    ║  DO NOT EDIT THIS FILE MANUALLY!                                    ║
    ║                                                                      ║
    ║  Manual changes will be OVERWRITTEN on next update!                 ║
    ║                                                                      ║
    ║  This file is protected with:                                       ║
    ║  - Read-only permissions                                            ║
    ║  - SHA256 integrity checking                                        ║
    ║                                                                      ║
    ║  Last generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                            ║
    ╚══════════════════════════════════════════════════════════════════════╝
    -->
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Isotope Efficiency Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }}
    .container {{ max-width: 95%; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
    .header-left {{ flex-grow: 1; }}
    .header-right {{ flex-shrink: 0; }}
    .header-right img {{ max-height: 160px; max-width: 400px; }}
    h1 {{ color: #333; margin-bottom: 10px; font-family: 'ISOCPEUR', 'Courier New', Courier, monospace; letter-spacing: 0.05em; font-size: 3em;  }}
    .timestamp {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
    .isotope-section {{ margin-bottom: 60px; padding: 20px; background: #f9f9f9; border-radius: 8px; }}
    .isotope-section h2 {{ color: #3875BA; border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px; margin-bottom: 20px; font-family: 'ISOCPEUR', 'Courier New', Courier, monospace; letter-spacing: 0.05em; font-size: 2em;}}
    .section {{ margin-bottom: 40px; }}
    .section h2 {{ color: #3875BA; border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px; margin-bottom: 20px; font-family: 'ISOCPEUR', 'Courier New', Courier, monospace; letter-spacing: 0.05em; font-size: 2em; }}
    h3 {{ color: #444; margin-bottom: 15px; border-bottom: 2px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
    thead {{ background: linear-gradient(to right, #662678, #E40D7E); }}
    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
    th {{ color: white; font-weight: 600; background: transparent; }}
    tr:hover {{ background-color: #f5f5f5; }}
    .chart-container {{ position: relative; height: 400px; margin-top: 20px; }}
    .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 20px; }}
    .chart-row-three {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 20px; }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
    }}
    </style>
    </head>
    <body>
    <div class="container">
    <div class="header">
        <div class="header-left">
            <h1>Productie Dashboard</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        <div class="header-right">
            <img src="logo.png" alt="Logo">
        </div>
    </div>

    <!-- DOSISOVERZICHT + DM VSM BUTTONS -->
    <div style="text-align: center; margin-bottom: 30px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
        <button onclick="openDosisModal()" style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 15px 30px; font-size: 18px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transition: transform 0.2s;">
            📊 Dosisoverzicht
        </button>
        <button onclick="openDmVsmModal()" style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 15px 30px; font-size: 18px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transition: transform 0.2s;">
            🗺️ DM VSM
        </button>
        <button onclick="openRoosterModal()" style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 15px 30px; font-size: 18px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transition: transform 0.2s;">
            📅 Rooster en targetvoorraad
        </button>
        <button onclick="openProductieschemaModal()" style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 15px 30px; font-size: 18px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transition: transform 0.2s;">
            🏭 Productieschema
        </button>
    </div>

    <!-- DOSISOVERZICHT MODAL -->
    <div id="dosisModal" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.8);">
        <div style="position: relative; background-color: white; margin: 2% auto; padding: 0; width: 90%; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
            <div style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 20px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; align-items: center;">
                <h2 style="margin: 0; color: white; border: none; padding: 0;">Dosisoverzicht</h2>
                <span onclick="closeDosisModal()" style="cursor: pointer; font-size: 32px; font-weight: bold; color: white;">&times;</span>
            </div>
            <div style="padding: 20px; text-align: center;">
                <img src="dosisoverzicht.png" alt="Dosisoverzicht" style="max-width: 100%; height: auto; border-radius: 5px;">
            </div>
        </div>
    </div>

    <!-- DM VSM MODAL -->
    <div id="dmVsmModal" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.8);">
        <div style="position: relative; background-color: white; margin: 2% auto; padding: 0; width: 90%; max-width: 1100px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
            <div style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 20px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; align-items: center;">
                <h2 style="margin: 0; color: white; border: none; padding: 0;">Daily Management Value Stream Map</h2>
                <span onclick="closeDmVsmModal()" style="cursor: pointer; font-size: 32px; font-weight: bold; color: white;">&times;</span>
            </div>
            <div style="padding: 20px; overflow-x: auto;">
                {vsm_table_html}
            </div>
        </div>
    </div>

    <!-- ROOSTER EN TARGETVOORRAAD MODAL (full-screen) -->
    <div id="roosterModal" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.9); flex-direction: column;">
        <div style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
            <h2 style="margin: 0; color: white; border: none; padding: 0; font-size: 22px;">📅 Rooster en targetvoorraad</h2>
            <span onclick="closeRoosterModal()" style="cursor: pointer; font-size: 36px; font-weight: bold; color: white; line-height: 1;">&times;</span>
        </div>
        <div style="flex: 1; overflow: hidden; background: white;">
            {rooster_modal_content}
        </div>
    </div>

    <!-- PRODUCTIESCHEMA MODAL (full-screen) -->
    <div id="productieschemaModal" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.9); flex-direction: column;">
        <div style="background: linear-gradient(135deg, #662678, #E40D7E); color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
            <h2 style="margin: 0; color: white; border: none; padding: 0; font-size: 22px;">🏭 Productieschema</h2>
            <span onclick="closeProductieschemaModal()" style="cursor: pointer; font-size: 36px; font-weight: bold; color: white; line-height: 1;">&times;</span>
        </div>
        <div style="flex: 1; overflow: hidden; background: white;">
            {productieschema_modal_content}
        </div>
    </div>

    <!-- TAMPERING WARNING BANNER -->
    {'<div style="background: #FF2400; color: white; padding: 20px; margin-bottom: 30px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; border: 5px solid #8B0000; animation: pulse 2s infinite;">' + 
     '<div style="font-size: 48px; margin-bottom: 10px;">⚠️ WARNING ⚠️</div>' + 
     '<div>' + tampering_warning + '</div>' + 
     '<div style="font-size: 16px; margin-top: 10px;">Manual changes have been detected and this file will be regenerated.</div>' + 
     '</div>' if tampering_warning else ''}

    {efficiency_table}

    {within_spec_table}

    {otif_gedraaide_table}

    {gantt_chart_html}

    {summary_table}

    {previous_week_summary_table}

    {iba_storingen_table}

    {philips_storingen_table}

    {otif_section_html}

    <!-- GALLIUM SECTION -->
    <div class="isotope-section">
        <h2>Gallium (Ga-67)</h2>
        <div class="section">
            <h3>Lopende week</h3>
            <table>
                <thead><tr><th>Date</th><th>BO nummer</th><th>Targetstroom (µA)</th><th>Opmerkingen</th><th>Reden voor afwijking</th></tr></thead>
                <tbody>{ga_rows}</tbody>
            </table>
        </div>
        <div class="chart-row">
            <div class="section">
                <h3>Maandelijkse gemiddeldes</h3>
                <div class="chart-container"><canvas id="gaMonthlyChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week stroom</h3>
                <div class="chart-container"><canvas id="gaRunningChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- RUBIDIUM SECTION -->
    <div class="isotope-section">
        <h2>Rubidium (Rb-81)</h2>
        <div class="section">
            <h3>Lopende week</h3>
            <table>
                <thead><tr><th>Date</th><th>BO nummer</th><th>Activiteit (MBq)</th><th>Benodigde (mCi)</th><th>Stroom (µA)</th><th>Efficiency (%)</th><th>Opmerkingen</th><th>Reden voor afwijking</th></tr></thead>
                <tbody>{rb_rows}</tbody>
            </table>
        </div>
        <div class="chart-row-three">
            <div class="section">
                <h3>Maandelijkse gemiddeldes</h3>
                <div class="chart-container"><canvas id="rbMonthlyChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week</h3>
                <div class="chart-container"><canvas id="rbRunningChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week stroom</h3>
                <div class="chart-container"><canvas id="rbStroomChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- INDIUM SECTION -->
    <div class="isotope-section">
        <h2>Indium (In-111)</h2>
        <div class="section">
            <h3>Lopende week</h3>
            <table>
                <thead><tr><th>Date</th><th>BO nummer</th><th>Targetstroom (µA)</th><th>Opmerkingen</th><th>Reden voor afwijking</th></tr></thead>
                <tbody>{in_rows}</tbody>
            </table>
        </div>
        <div class="chart-row">
            <div class="section">
                <h3>Maandelijkse gemiddeldes</h3>
                <div class="chart-container"><canvas id="inMonthlyChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week stroom</h3>
                <div class="chart-container"><canvas id="inRunningChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- THALLIUM SECTION -->
    <div class="isotope-section">
        <h2>Thallium (Tl-201)</h2>
        <div class="section">
            <h3>Lopende week</h3>
            <table>
                <thead><tr><th>Date</th><th>BO nummer</th><th>Targetstroom (µA)</th><th>Kant</th><th>Opmerkingen</th><th>Reden voor afwijking</th></tr></thead>
                <tbody>{tl_rows}</tbody>
            </table>
        </div>
        <div class="chart-row">
            <div class="section">
                <h3>Maandelijkse gemiddeldes</h3>
                <div class="chart-container"><canvas id="tlMonthlyChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week stroom</h3>
                <div class="chart-container"><canvas id="tlRunningChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- IODINE SECTION -->
    <div class="isotope-section">
        <h2>Iodine (I-123)</h2>
        <div class="section">
            <h3>Lopende week</h3>
            <table>
                <thead><tr><th>Date</th><th>BO nummer</th><th>Meting D1 (MBq)</th><th>Meting Waste (MBq)</th><th>BO Targetstroom (µA)</th><th>Targetstroom (µA)</th><th>Yield%</th><th>Output%</th><th>Opmerkingen</th><th>Reden voor afwijking</th></tr></thead>
                <tbody>{io_rows}</tbody>
            </table>
        </div>
        <div class="chart-row-three">
            <div class="section">
                <h3>Maandelijkse gemiddeldes</h3>
                <div class="chart-container"><canvas id="ioMonthlyChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week opbrengst</h3>
                <div class="chart-container"><canvas id="ioRunningChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Lopende week stroom</h3>
                <div class="chart-container"><canvas id="ioTargetstrooomChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- EFFICIENCY CHARTS SECTION -->
    <div class="isotope-section">
        <h2>Efficiëntie trends Bronfaraday → Targets</h2>
        <div class="chart-row">
            <div class="section">
                <h3>Past Year</h3>
                <div class="chart-container"><canvas id="efficiencyPastYearChart"></canvas></div>
            </div>
            <div class="section">
                <h3>All Time</h3>
                <div class="chart-container"><canvas id="efficiencyAllTimeChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- WITHIN SPEC CHARTS SECTION -->
    <div class="isotope-section">
        <h2>Success Rate Trends</h2>
        <div class="chart-row">
            <div class="section">
                <h3>Past Year</h3>
                <div class="chart-container"><canvas id="withinSpecPastYearChart"></canvas></div>
            </div>
            <div class="section">
                <h3>All Time</h3>
                <div class="chart-container"><canvas id="withinSpecAllTimeChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- ISSUE TRACKING SECTION
    <div class="isotope-section">
        <h2>Productieverstoringenanalyse</h2>
        <div class="chart-row-three">
            <div class="section">
                <h3>This Week Issues</h3>
                <div class="chart-container"><canvas id="issuesThisWeekChart"></canvas></div>
            </div>
            <div class="section">
                <h3>Last Week Issues</h3>
                <div class="chart-container"><canvas id="issuesLastWeekChart"></canvas></div>
            </div>
            <div class="section">
                <h3>All Time Issues</h3>
                <div class="chart-container"><canvas id="issuesAllTimeChart"></canvas></div>
            </div>
        </div>
    </div>

    ISOTOPE COMPARISON SECTION
    <div class="isotope-section">
        <h2>Verstoringen per isotoop</h2>
        <div class="section">
            <div class="chart-container"><canvas id="isotopeComparisonChart"></canvas></div>
        </div>
    </div> -->

    <!-- GALLIUM PRODUCTION EFFICIENCY SECTION -->
    {gallium_production_efficiency_table}

    <!-- INDIUM PRODUCTION EFFICIENCY SECTION -->
    {indium_production_efficiency_table}

    <!-- RUBIDIUM PRODUCTION EFFICIENCY SECTION -->
    {rubidium_production_efficiency_table}

    <!-- IODINE PRODUCTION EFFICIENCY SECTION -->
    {iodine_production_efficiency_table}

    <!-- PASSWORD PROTECTION REMOVED - PLOEG SECTIONS NOW FREELY ACCESSIBLE -->
    <div id="password-prompt" style="display: none;">
        <!-- Password prompt hidden -->
    </div>

    <!-- PLOEG CONTENT (NOW FREELY ACCESSIBLE) -->
    <div id="ploeg-content" style="display: block;">
        <!-- PLOEG LEADERBOARD -->
        {generate_leaderboard_html(leaderboard)}

        <!-- MONTHLY WINNER -->
        {generate_monthly_winner_html(monthly_winner)}

        <!-- PLOEG PERFORMANCE SECTION -->
        {generate_shift_tables_html(shift_stats_this_week, shift_stats_last_week, this_week_friday, last_week_friday, ploeg_6month, ploeg_3month, ploeg_monthly, ploegen_data)}

        <!-- PLOEG ROLLING AVERAGE CHARTS -->
        {generate_ploeg_rolling_charts_html(ploeg_rolling, ploegen_data)}
    </div>
    </div>

    <script>
    // Password protection removed - ploeg sections now freely accessible
    </script>

    <script>
    // Function to save comment (stores temporarily, syncs to database on next page generation)
    function saveComment(isotope, date, boNumber, commentType) {{
        // Save to localStorage for immediate feedback
        const key = `comment_${{isotope}}_${{date}}_${{boNumber}}`;

        // Make AJAX call to save to database
        fetch('/save_comment', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify({{
                isotope_type: isotope,
                production_date: date,
                bo_number: boNumber,
                comment_type: commentType,
                created_at: new Date().toISOString()
            }})
        }})
        .then(response => {{
            if (response.ok) {{
                // Show success feedback
                const select = document.getElementById(`${{isotope}}_${{date}}_${{boNumber}}`.replace(/\\./g, '_').replace(/-/g, '_').replace(/ /g, '_'));
                if (select) {{
                    select.style.borderColor = '#28a745';
                    setTimeout(() => {{ select.style.borderColor = '#ddd'; }}, 1000);
                }}

                // Also save to localStorage as backup
                if (commentType === '') {{
                    localStorage.removeItem(key);
                }} else {{
                    localStorage.setItem(key, commentType);
                }}
            }}
        }})
        .catch(error => {{
            console.error('Error saving comment:', error);
            // Fall back to localStorage only
            if (commentType === '') {{
                localStorage.removeItem(key);
            }} else {{
                localStorage.setItem(key, commentType);
            }}
        }});
    }}

    const createOptions = (maxValue) => ({{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ 
            legend: {{ display: true, position: 'top' }},
            tooltip: {{
                callbacks: {{
                    afterLabel: function(context) {{
                        const identifiers = context.chart.data.identifiers;
                        if (identifiers && identifiers[context.dataIndex]) {{
                            return 'ID: ' + identifiers[context.dataIndex];
                        }}
                        return '';
                    }}
                }}
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: true,
                min: 0,
                max: maxValue,
                ticks: {{ callback: function(value) {{ return value + '%'; }} }},
                title: {{ display: true, text: 'Efficiency (%)' }}
            }}
        }}
    }});

    const createTargetstrooomOptions = (maxValue) => ({{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ 
            legend: {{ display: true, position: 'top' }},
            tooltip: {{
                callbacks: {{
                    afterLabel: function(context) {{
                        const identifiers = context.chart.data.identifiers;
                        if (identifiers && identifiers[context.dataIndex]) {{
                            return 'ID: ' + identifiers[context.dataIndex];
                        }}
                        return '';
                    }}
                }}
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: true,
                min: 0,
                max: maxValue,
                ticks: {{ callback: function(value) {{ return value + ' µA'; }} }},
                title: {{ display: true, text: 'Targetstroom (µA)' }}
            }}
        }}
    }});

    const referenceLines = {{
        id: 'referenceLines',
        afterDraw: (chart) => {{
            const ctx = chart.ctx;
            const yAxis = chart.scales.y;
            const xAxis = chart.scales.x;
            ctx.save();
            ctx.strokeStyle = 'rgba(255, 159, 64, 0.8)';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            [95, 100, 105].forEach(value => {{
                const y = yAxis.getPixelForValue(value);
                ctx.beginPath();
                ctx.moveTo(xAxis.left, y);
                ctx.lineTo(xAxis.right, y);
                ctx.stroke();
                ctx.fillStyle = 'rgba(255, 159, 64, 0.8)';
                ctx.font = '12px Arial';
                ctx.fillText(value + '%', xAxis.right + 5, y + 4);
            }});
            ctx.restore();
        }}
    }};

    // Reference lines for Gallium and Indium (75-85 µA)
    const referenceLinesGaIn = {{
        id: 'referenceLinesGaIn',
        afterDraw: (chart) => {{
            const ctx = chart.ctx;
            const yAxis = chart.scales.y;
            const xAxis = chart.scales.x;
            ctx.save();
            ctx.strokeStyle = 'rgba(76, 175, 80, 0.8)';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            [75, 85].forEach(value => {{
                const y = yAxis.getPixelForValue(value);
                ctx.beginPath();
                ctx.moveTo(xAxis.left, y);
                ctx.lineTo(xAxis.right, y);
                ctx.stroke();
                ctx.fillStyle = 'rgba(76, 175, 80, 0.8)';
                ctx.font = '12px Arial';
                ctx.fillText(value + ' µA', xAxis.right + 5, y + 4);
            }});
            ctx.restore();
        }}
    }};

    // Reference lines for Thallium (165-175 µA)
    const referenceLinesTl = {{
        id: 'referenceLinesTl',
        afterDraw: (chart) => {{
            const ctx = chart.ctx;
            const yAxis = chart.scales.y;
            const xAxis = chart.scales.x;
            ctx.save();
            ctx.strokeStyle = 'rgba(233, 30, 99, 0.8)';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            [165, 175].forEach(value => {{
                const y = yAxis.getPixelForValue(value);
                ctx.beginPath();
                ctx.moveTo(xAxis.left, y);
                ctx.lineTo(xAxis.right, y);
                ctx.stroke();
                ctx.fillStyle = 'rgba(233, 30, 99, 0.8)';
                ctx.font = '12px Arial';
                ctx.fillText(value + ' µA', xAxis.right + 5, y + 4);
            }});
            ctx.restore();
        }}
    }};

    // Gallium Charts - now showing targetstroom in µA
    new Chart(document.getElementById('gaMonthlyChart'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(ga_mon_lab)}, datasets: [{{ label: 'Monthly Avg (µA)', data: {json.dumps(ga_mon_dat)}, backgroundColor: 'rgba(76, 175, 80, 0.6)' }}] }},
        options: createTargetstrooomOptions({ga_mon_max}),
        plugins: [referenceLinesGaIn]
    }});
    new Chart(document.getElementById('gaRunningChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(ga_run_lab)}, 
            datasets: [{{ label: 'Targetstroom (µA)', data: {json.dumps(ga_run_dat)}, backgroundColor: 'rgba(33, 150, 243, 0.6)' }}],
            identifiers: {json.dumps(ga_run_id)}
        }},
        options: createTargetstrooomOptions({ga_run_max}),
        plugins: [referenceLinesGaIn]
    }});

    // Rubidium Charts
    new Chart(document.getElementById('rbMonthlyChart'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(rb_mon_lab)}, datasets: [{{ label: 'Monthly Avg', data: {json.dumps(rb_mon_dat)}, backgroundColor: 'rgba(156, 39, 176, 0.6)' }}] }},
        options: createOptions({rb_mon_max}),
        plugins: [referenceLines]
    }});
    new Chart(document.getElementById('rbRunningChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(rb_run_lab)}, 
            datasets: [{{ label: 'Production', data: {json.dumps(rb_run_dat)}, backgroundColor: 'rgba(255, 87, 34, 0.6)' }}],
            identifiers: {json.dumps(rb_run_id)}
        }},
        options: createOptions({rb_run_max}),
        plugins: [referenceLines]
    }});
    new Chart(document.getElementById('rbStroomChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(rb_stroom_lab)}, 
            datasets: [{{ label: 'Stroom (µA)', data: {json.dumps(rb_stroom_dat)}, backgroundColor: 'rgba(255, 152, 0, 0.6)' }}],
            identifiers: {json.dumps(rb_stroom_id)}
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        afterLabel: function(context) {{
                            const identifiers = context.chart.data.identifiers;
                            if (identifiers && identifiers[context.dataIndex]) {{
                                return 'BO: ' + identifiers[context.dataIndex];
                            }}
                            return '';
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    min: 0,
                    max: {rb_stroom_max},
                    title: {{ display: true, text: 'Stroom (mAh)' }}
                }}
            }}
        }}
    }});

    // Indium Charts - now showing targetstroom in µA
    new Chart(document.getElementById('inMonthlyChart'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(in_mon_lab)}, datasets: [{{ label: 'Monthly Avg (µA)', data: {json.dumps(in_mon_dat)}, backgroundColor: 'rgba(63, 81, 181, 0.6)' }}] }},
        options: createTargetstrooomOptions({in_mon_max}),
        plugins: [referenceLinesGaIn]
    }});
    new Chart(document.getElementById('inRunningChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(in_run_lab)}, 
            datasets: [{{ label: 'Targetstroom (µA)', data: {json.dumps(in_run_dat)}, backgroundColor: 'rgba(0, 150, 136, 0.6)' }}],
            identifiers: {json.dumps(in_run_id)}
        }},
        options: createTargetstrooomOptions({in_run_max}),
        plugins: [referenceLinesGaIn]
    }});

    // Thallium Charts - now showing targetstroom in µA with kant separation
    new Chart(document.getElementById('tlMonthlyChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(tl_mon_lab)}, 
            datasets: [
                {{ label: 'Monthly Avg 1.2 (µA)', data: {json.dumps(tl_mon_dat_12)}, backgroundColor: 'rgba(233, 30, 99, 0.6)' }},
                {{ label: 'Monthly Avg 2.1 (µA)', data: {json.dumps(tl_mon_dat_21)}, backgroundColor: 'rgba(156, 39, 176, 0.6)' }}
            ]
        }},
        options: createTargetstrooomOptions({tl_mon_max}),
        plugins: [referenceLinesTl]
    }});
    new Chart(document.getElementById('tlRunningChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(tl_run_lab)}, 
            datasets: [{{ label: 'Targetstroom (µA)', data: {json.dumps(tl_run_dat)}, backgroundColor: 'rgba(255, 193, 7, 0.6)' }}],
            identifiers: {json.dumps(tl_run_id)},
            kant: {json.dumps(tl_run_kant)}
        }},
        options: {{
            ...createTargetstrooomOptions({tl_run_max}),
            plugins: {{
                ...createTargetstrooomOptions({tl_run_max}).plugins,
                tooltip: {{
                    callbacks: {{
                        afterLabel: function(context) {{
                            const identifiers = context.chart.data.identifiers;
                            const kant = context.chart.data.kant;
                            let result = '';
                            if (identifiers && identifiers[context.dataIndex]) {{
                                result += 'BO: ' + identifiers[context.dataIndex];
                            }}
                            if (kant && kant[context.dataIndex]) {{
                                result += '\\nKant: ' + kant[context.dataIndex];
                            }}
                            return result;
                        }}
                    }}
                }}
            }},
            scales: {{
                ...createTargetstrooomOptions({tl_run_max}).scales,
                x: {{
                    ticks: {{
                        callback: function(value, index) {{
                            const kant = this.chart.data.kant;
                            const label = this.chart.data.labels[index];
                            return kant && kant[index] ? [label, kant[index]] : label;
                        }}
                    }}
                }}
            }}
        }},
        plugins: [referenceLinesTl]
    }});

    // Iodine Charts - with grouped bars for running week
    new Chart(document.getElementById('ioMonthlyChart'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(io_mon_lab)}, datasets: [{{ label: 'Monthly Avg', data: {json.dumps(io_mon_dat)}, backgroundColor: 'rgba(121, 85, 72, 0.6)' }}] }},
        options: createOptions({io_mon_max}),
        plugins: [referenceLines]
    }});
    new Chart(document.getElementById('ioRunningChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(io_run_lab)}, 
            datasets: [
                {{ label: 'Yield%', data: {json.dumps(io_run_dat_yield)}, backgroundColor: 'rgba(96, 125, 139, 0.6)' }},
                {{ label: 'Output%', data: {json.dumps(io_run_dat_output)}, backgroundColor: 'rgba(121, 85, 72, 0.6)' }}
            ],
            identifiers: {json.dumps(io_run_id)}
        }},
        options: {{
            ...createOptions({io_run_max}),
            scales: {{
                ...createOptions({io_run_max}).scales,
                x: {{
                    stacked: false
                }}
            }}
        }},
        plugins: [referenceLines]
    }});
    new Chart(document.getElementById('ioTargetstrooomChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(io_target_lab)}, 
            datasets: [
                {{ label: 'BO Targetstroom (µA)', data: {json.dumps(io_bo_target_dat)}, backgroundColor: 'rgba(63, 81, 181, 0.6)' }},
                {{ label: 'Targetstroom (µA)', data: {json.dumps(io_target_dat)}, backgroundColor: 'rgba(0, 150, 136, 0.6)' }}
            ],
            identifiers: {json.dumps(io_target_id)}
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        afterLabel: function(context) {{
                            const identifiers = context.chart.data.identifiers;
                            if (identifiers && identifiers[context.dataIndex]) {{
                                return 'BO: ' + identifiers[context.dataIndex];
                            }}
                            return '';
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    min: 0,
                    max: {io_target_max},
                    title: {{ display: true, text: 'Targetstroom (mAh)' }}
                }},
                x: {{
                    stacked: false
                }}
            }}
        }}
    }});

    // Efficiency Charts
    new Chart(document.getElementById('efficiencyPastYearChart'), {{
        type: 'line',
        data: {{ 
            labels: {json.dumps(eff_past_year_labels)}, 
            datasets: [{{ 
                label: 'Efficiency (%)', 
                data: {json.dumps(eff_past_year_data)}, 
                backgroundColor: 'rgba(102, 38, 120, 0.2)',
                borderColor: 'rgba(102, 38, 120, 1)',
                borderWidth: 2,
                fill: true
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    min: 0,
                    max: {eff_past_year_max},
                    ticks: {{ callback: function(value) {{ return value + '%'; }} }},
                    title: {{ display: true, text: 'Efficiency (%)' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    new Chart(document.getElementById('efficiencyAllTimeChart'), {{
        type: 'line',
        data: {{ 
            labels: {json.dumps(eff_all_time_labels)}, 
            datasets: [{{ 
                label: 'Efficiency (%)', 
                data: {json.dumps(eff_all_time_data)}, 
                backgroundColor: 'rgba(228, 13, 126, 0.2)',
                borderColor: 'rgba(228, 13, 126, 1)',
                borderWidth: 2,
                fill: true
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    min: 0,
                    max: {eff_all_time_max},
                    ticks: {{ callback: function(value) {{ return value + '%'; }} }},
                    title: {{ display: true, text: 'Efficiency (%)' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    // Within-Spec Charts
    new Chart(document.getElementById('withinSpecPastYearChart'), {{
        type: 'line',
        data: {{ 
            labels: {json.dumps(ws_past_year_labels)}, 
            datasets: [{{ 
                label: 'Success Rate (%)', 
                data: {json.dumps(ws_past_year_data)}, 
                backgroundColor: 'rgba(102, 38, 120, 0.2)',
                borderColor: 'rgba(102, 38, 120, 1)',
                borderWidth: 2,
                fill: true
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    min: 0,
                    max: {ws_past_year_max},
                    ticks: {{ callback: function(value) {{ return value + '%'; }} }},
                    title: {{ display: true, text: 'Success Rate (%)' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    new Chart(document.getElementById('withinSpecAllTimeChart'), {{
        type: 'line',
        data: {{ 
            labels: {json.dumps(ws_all_time_labels)}, 
            datasets: [{{ 
                label: 'Success Rate (%)', 
                data: {json.dumps(ws_all_time_data)}, 
                backgroundColor: 'rgba(228, 13, 126, 0.2)',
                borderColor: 'rgba(228, 13, 126, 1)',
                borderWidth: 2,
                fill: true
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    min: 0,
                    max: {ws_all_time_max},
                    ticks: {{ callback: function(value) {{ return value + '%'; }} }},
                    title: {{ display: true, text: 'Success Rate (%)' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    // Issue Tracking Bar Charts
    new Chart(document.getElementById('issuesThisWeekChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(issue_categories)}, 
            datasets: [{{ 
                label: 'Count', 
                data: {json.dumps(issues_this_week_data)}, 
                backgroundColor: 'rgba(255, 36, 0, 0.6)',
                borderColor: 'rgba(255, 36, 0, 1)',
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: false }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    ticks: {{ stepSize: 1 }},
                    title: {{ display: true, text: 'Number of Issues' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    new Chart(document.getElementById('issuesLastWeekChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(issue_categories)}, 
            datasets: [{{ 
                label: 'Count', 
                data: {json.dumps(issues_last_week_data)}, 
                backgroundColor: 'rgba(255, 152, 0, 0.6)',
                borderColor: 'rgba(255, 152, 0, 1)',
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: false }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    ticks: {{ stepSize: 1 }},
                    title: {{ display: true, text: 'Number of Issues' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    new Chart(document.getElementById('issuesAllTimeChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(issue_categories)}, 
            datasets: [{{ 
                label: 'Count', 
                data: {json.dumps(issues_all_time_data)}, 
                backgroundColor: 'rgba(102, 38, 120, 0.6)',
                borderColor: 'rgba(102, 38, 120, 1)',
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: false }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    ticks: {{ stepSize: 1 }},
                    title: {{ display: true, text: 'Number of Issues' }}
                }},
                x: {{
                    ticks: {{
                        maxRotation: 45,
                        minRotation: 45
                    }}
                }}
            }}
        }}
    }});

    // Isotope Comparison Chart
    new Chart(document.getElementById('isotopeComparisonChart'), {{
        type: 'bar',
        data: {{ 
            labels: {json.dumps(isotope_names)}, 
            datasets: [{{ 
                label: 'Total Issues', 
                data: {json.dumps(isotope_counts)}, 
                backgroundColor: 'rgba(228, 13, 126, 0.6)',
                borderColor: 'rgba(228, 13, 126, 1)',
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ 
                legend: {{ display: false }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    ticks: {{ stepSize: 1 }},
                    title: {{ display: true, text: 'Number of Issues' }}
                }}
            }}
        }}
    }});
    </script>

    <!-- PRODUCTION HISTORY MODAL -->
    <div id="productionModal" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.7);">
    <div style="background-color: #fefefe; margin: 5% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 800px; border-radius: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 15px;">
            <h2 id="productionModalTitle" style="margin: 0; background: linear-gradient(135deg, #662678, #E40D7E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">Production History</h2>
            <span onclick="closeProductionModal()" style="font-size: 32px; font-weight: bold; cursor: pointer; color: #aaa;">&times;</span>
        </div>
        <div id="productionModalContent" style="max-height: 500px; overflow-y: auto;"></div>
    </div>
    </div>

    <!-- PLOEG PRODUCTION DETAILS MODAL -->
    <div id="ploegModal" style="display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.6);">
    <div style="background-color: #fefefe; margin: 2% auto; padding: 20px; border: 1px solid #888; width: 90%; max-width: 1400px; border-radius: 10px; max-height: 90vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 15px;">
            <h2 id="modalTitle" style="margin: 0; background: linear-gradient(135deg, #662678, #E40D7E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">Ploeg Details</h2>
            <div style="display: flex; align-items: center; gap: 12px;">
                <button onclick="printPloegModal()" style="padding: 8px 18px; font-size: 14px; cursor: pointer; background: #444; color: white; border: none; border-radius: 5px;">🖨️ Print</button>
                <span onclick="closePloegModal()" style="font-size: 32px; font-weight: bold; cursor: pointer; color: #aaa;">&times;</span>
            </div>
        </div>

        <!-- Time Filter Buttons -->
        <div style="text-align: center; margin-bottom: 20px;">
            <button onclick="filterPloegData('week')" id="filterWeek" style="margin: 0 5px; padding: 10px 20px; font-size: 14px; cursor: pointer; background: #662678; color: white; border: none; border-radius: 5px;">1 Week</button>
            <button onclick="filterPloegData('month')" id="filterMonth" style="margin: 0 5px; padding: 10px 20px; font-size: 14px; cursor: pointer; background: #662678; color: white; border: none; border-radius: 5px;">Past 30 Days</button>
            <button onclick="filterPloegData('3months')" id="filter3Months" style="margin: 0 5px; padding: 10px 20px; font-size: 14px; cursor: pointer; background: #662678; color: white; border: none; border-radius: 5px;">Past 3 Months</button>
            <button onclick="filterPloegData('6months')" id="filter6Months" style="margin: 0 5px; padding: 10px 20px; font-size: 14px; cursor: pointer; background: #E40D7E; color: white; border: none; border-radius: 5px; font-weight: bold;">Past 6 Months</button>
        </div>

        <!-- Ploeg% Filter -->
        <div style="text-align: center; margin-bottom: 25px; display: flex; align-items: center; justify-content: center; gap: 10px;">
            <label style="font-size: 14px; color: #444;">Min. Ploeg%:</label>
            <input type="number" id="ploegPctInput" value="50" min="0" max="100" step="1"
                style="width: 70px; padding: 6px 8px; font-size: 14px; border: 2px solid #662678; border-radius: 5px; text-align: center;"
                oninput="applyPloegPctFilter()" />
            <span style="font-size: 14px; color: #444;">%</span>
            <button id="ploegPctToggle" onclick="togglePloegPctFilter()"
                style="padding: 6px 16px; font-size: 14px; cursor: pointer; background: #E40D7E; color: white; border: none; border-radius: 5px; font-weight: bold;">
                ON
            </button>
            <span id="ploegPctStatus" style="font-size: 13px; color: #666;"></span>
        </div>

        <!-- Content will be inserted here -->
        <div id="modalContent"></div>
    </div>
    </div>

    <!-- SF PRODUCTIONS MODAL -->
    <div id="sfModal" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.7);">
    <div style="background-color: #fefefe; margin: 5% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 900px; border-radius: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 15px;">
            <h2 id="sfModalTitle" style="margin: 0; background: linear-gradient(135deg, #662678, #E40D7E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">Affected Productions</h2>
            <span onclick="closeSFModal()" style="font-size: 32px; font-weight: bold; cursor: pointer; color: #aaa;">&times;</span>
        </div>
        <div id="sfModalContent" style="max-height: 500px; overflow-y: auto;"></div>
    </div>
    </div>

    <!-- Production Data as JSON -->
    <script>
    const ploegProductionData = """ + json.dumps(ploeg_production_details if ploeg_production_details else {}, default=str) + """;
    const productionHistory = """ + json.dumps(production_history if production_history else {}, default=str) + """;
    const sfProductionData = """ + json.dumps(sf_productions if sf_productions else {}, default=str) + """;
    let currentPloegNumber = null;
    let currentFilter = '6months';
    let ploegPctFilterEnabled = true;
    let ploegPctFilterValue = 50;

    function togglePloegPctFilter() {
        ploegPctFilterEnabled = !ploegPctFilterEnabled;
        const btn = document.getElementById('ploegPctToggle');
        const input = document.getElementById('ploegPctInput');
        if (ploegPctFilterEnabled) {
            btn.textContent = 'ON';
            btn.style.background = '#E40D7E';
            input.disabled = false;
            input.style.opacity = '1';
        } else {
            btn.textContent = 'OFF';
            btn.style.background = '#999';
            input.disabled = true;
            input.style.opacity = '0.5';
        }
        updatePloegPctStatus();
        displayPloegProductions(window._lastByIsotope || {});
    }

    function applyPloegPctFilter() {
        ploegPctFilterValue = parseFloat(document.getElementById('ploegPctInput').value) || 0;
        updatePloegPctStatus();
        displayPloegProductions(window._lastByIsotope || {});
    }

    function updatePloegPctStatus() {
        const el = document.getElementById('ploegPctStatus');
        if (ploegPctFilterEnabled) {
            el.textContent = 'Showing only productions where this ploeg contributed ≥ ' + ploegPctFilterValue + '%';
            el.style.color = '#662678';
        } else {
            el.textContent = 'Showing all productions regardless of ploeg%';
            el.style.color = '#999';
        }
    }

    function showPloegDetails(ploegNumber) {
        currentPloegNumber = ploegNumber;
        const modal = document.getElementById('ploegModal');
        modal.style.display = 'block';

        // Save to localStorage for persistence across page refreshes
        localStorage.setItem('modalOpen', 'true');
        localStorage.setItem('modalPloegNumber', ploegNumber);
        localStorage.setItem('modalFilter', currentFilter || '6months');

        // Get ploeg name
        const ploegName = getPloegName(ploegNumber);
        document.getElementById('modalTitle').innerHTML = 'Production Details: ' + ploegName;

        // Filter and display data
        filterPloegData('6months');
        updatePloegPctStatus();
    }

    function closePloegModal() {
        document.getElementById('ploegModal').style.display = 'none';
        // Clear localStorage when modal is closed
        localStorage.removeItem('modalOpen');
        localStorage.removeItem('modalPloegNumber');
        localStorage.removeItem('modalFilter');
    }

    function getPloegName(ploegNumber) {
        // Try to find ploeg name from leaderboard or tables
        const tables = document.querySelectorAll('table');
        for (let table of tables) {
            const rows = table.querySelectorAll('tr');
            for (let row of rows) {
                const link = row.querySelector('a[onclick*="' + ploegNumber + '"]');
                if (link) {
                    return link.textContent.trim();
                }
            }
        }
        return 'Ploeg ' + ploegNumber;
    }

    function filterPloegData(period) {
        currentFilter = period;

        // Save filter to localStorage for persistence
        localStorage.setItem('modalFilter', period);

        // Update button styles
        document.getElementById('filterWeek').style.background = '#662678';
        document.getElementById('filterWeek').style.fontWeight = 'normal';
        document.getElementById('filterMonth').style.background = '#662678';
        document.getElementById('filterMonth').style.fontWeight = 'normal';
        document.getElementById('filter3Months').style.background = '#662678';
        document.getElementById('filter3Months').style.fontWeight = 'normal';
        document.getElementById('filter6Months').style.background = '#662678';
        document.getElementById('filter6Months').style.fontWeight = 'normal';

        const button = document.getElementById('filter' + period.charAt(0).toUpperCase() + period.slice(1).replace('months', 'Months'));
        button.style.background = '#E40D7E';
        button.style.fontWeight = 'bold';

        // Calculate cutoff date
        const now = new Date();
        let cutoffDate;
        switch(period) {
            case 'week':
                cutoffDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            case 'month':
                cutoffDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                break;
            case '3months':
                cutoffDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                break;
            case '6months':
                cutoffDate = new Date(now.getTime() - 180 * 24 * 60 * 60 * 1000);
                break;
        }

        // Get productions for this ploeg
        const productions = ploegProductionData[currentPloegNumber] || [];

        // Filter by date
        const filtered = productions.filter(prod => {
            const prodDate = new Date(prod.date);
            return prodDate >= cutoffDate;
        });

        // Group by isotope
        const byIsotope = {
            gallium: [],
            rubidium: [],
            indium: [],
            thallium: [],
            iodine: []
        };

        filtered.forEach(prod => {
            if (byIsotope[prod.isotope]) {
                byIsotope[prod.isotope].push(prod);
            }
        });

        // Sort each isotope by date (newest first)
        for (let isotope in byIsotope) {
            byIsotope[isotope].sort((a, b) => new Date(b.date) - new Date(a.date));
        }

        // Cache for re-use when ploeg% filter is toggled without re-fetching
        window._lastByIsotope = byIsotope;
        updatePloegPctStatus();

        // Generate HTML
        displayPloegProductions(byIsotope);
    }

    function displayPloegProductions(byIsotope) {
        const content = document.getElementById('modalContent');
        let html = '';

        // Spec midpoints per isotope/cyclotron
        const MIDPOINTS = {
            gallium:  { iba: 135, philips: 80 },
            indium:   { iba: 135, philips: 80 },
            thallium: { all: 170 },
            iodine:   {}  // uses bo_targetstroom per production
            // rubidium: efficiency %, not µA — excluded
        };

        // Apply ploeg% filter per isotope group
        function applyPctFilter(prods) {
            if (!ploegPctFilterEnabled) return prods;
            // Filter BEFORE merging — sum proportions per BO, then check threshold
            const boTotals = new Map();
            prods.forEach(p => {
                const k = p.data['bo_nummer'] != null ? String(Math.round(p.data['bo_nummer'])) : '__none__';
                boTotals.set(k, (boTotals.get(k) || 0) + p.proportion);
            });
            return prods.filter(p => {
                const k = p.data['bo_nummer'] != null ? String(Math.round(p.data['bo_nummer'])) : '__none__';
                return boTotals.get(k) >= ploegPctFilterValue;
            });
        }

        // Merge by BO (same logic as generateIsotopeTable) for accurate counting
        function mergeByBO(prods) {
            const map = new Map();
            prods.forEach(prod => {
                const k = prod.data['bo_nummer'] != null ? String(Math.round(prod.data['bo_nummer'])) : '__none__';
                if (map.has(k)) {
                    map.get(k).proportion += prod.proportion;
                } else {
                    map.set(k, { ...prod, proportion: prod.proportion });
                }
            });
            return Array.from(map.values());
        }

        // Calculate missed µAh for one isotope's filtered+merged productions
        function missedUAhForIsotope(merged, isotopeType) {
            if (!(isotopeType in MIDPOINTS)) return { total: 0, failCount: 0, totalCount: 0 };
            let total = 0;
            let failCount = 0;
            let totalCount = 0;
            merged.forEach(prod => {
                totalCount++;
                if (prod.in_spec) return;
                failCount++;
                const actual = parseFloat(prod.data['targetstroom']);
                const duur   = parseFloat(prod.data['duur']);
                if (isNaN(actual) || actual === -999 || isNaN(duur) || duur <= 0) return;
                let midpoint;
                if (isotopeType === 'gallium' || isotopeType === 'indium') {
                    const cyc = String(prod.data['cyclotron'] || '').toUpperCase();
                    midpoint = cyc.startsWith('IBA') ? MIDPOINTS[isotopeType].iba : MIDPOINTS[isotopeType].philips;
                } else if (isotopeType === 'iodine') {
                    // Use the per-production BO target, not a fixed midpoint
                    const boTarget = prod.data['bo_targetstroom'];
                    if (boTarget == null || boTarget === -999 || isNaN(parseFloat(boTarget))) return;
                    midpoint = parseFloat(boTarget);
                } else {
                    midpoint = MIDPOINTS[isotopeType].all;
                }
                total += Math.abs(actual - midpoint) * duur;
            });
            return { total, failCount, totalCount };
        }

        // Build filtered sets
        const filtered = {
            gallium:  byIsotope.gallium.length  > 0 ? applyPctFilter(byIsotope.gallium)  : [],
            rubidium: byIsotope.rubidium.length > 0 ? applyPctFilter(byIsotope.rubidium) : [],
            indium:   byIsotope.indium.length   > 0 ? applyPctFilter(byIsotope.indium)   : [],
            thallium: byIsotope.thallium.length > 0 ? applyPctFilter(byIsotope.thallium) : [],
            iodine:   byIsotope.iodine.length   > 0 ? applyPctFilter(byIsotope.iodine)   : []
        };

        // Compute missed µAh per isotope and totals
        const statsByIsotope = {};
        let totalMissedUAh = 0;
        let totalFailCount = 0;
        let totalProdCount = 0;
        for (const iso of ['gallium', 'indium', 'thallium', 'iodine']) {
            if (filtered[iso].length > 0) {
                const merged = mergeByBO(filtered[iso]);
                const result = missedUAhForIsotope(merged, iso);
                statsByIsotope[iso] = result;
                totalMissedUAh += result.total;
                totalFailCount += result.failCount;
                totalProdCount += result.totalCount;
            }
        }

        const totalAvgPerProd = totalProdCount > 0 ? totalMissedUAh / totalProdCount : 0;
        const summaryColor = totalMissedUAh === 0 ? '#3BB143' : '#E40D7E';

        // Per-isotope detail rows for both metrics
        let totalRow = [];
        let avgRow = [];
        for (const [iso, s] of Object.entries(statsByIsotope)) {
            if (s.total > 0) {
                const label = iso.charAt(0).toUpperCase() + iso.slice(1);
                totalRow.push(label + ': ' + s.total.toFixed(1) + ' µAh');
                const avg = s.totalCount > 0 ? s.total / s.totalCount : 0;
                avgRow.push(label + ': ' + avg.toFixed(1) + ' µAh/prod (' + s.failCount + '/' + s.totalCount + ' failed)');
            }
        }
        const totalDetail = totalRow.length > 0 ? totalRow.join(' &nbsp;|&nbsp; ') : '';
        const avgDetail   = avgRow.length   > 0 ? avgRow.join(' &nbsp;|&nbsp; ')   : '';

        html += `<div style="background: #f8f8f8; border-left: 5px solid ${summaryColor}; padding: 14px 18px; margin-bottom: 20px; border-radius: 4px;">
            <div style="display: flex; align-items: baseline; gap: 16px; margin-bottom: 6px; flex-wrap: wrap;">
                <span style="font-size: 15px; font-weight: bold; color: ${summaryColor}; white-space: nowrap;">Total missed µAh: ${totalMissedUAh.toFixed(1)} µAh</span>
                <span style="font-size: 13px; color: #666;">${totalDetail}</span>
            </div>
            <div style="display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;">
                <span style="font-size: 15px; font-weight: bold; color: ${summaryColor}; white-space: nowrap;">Avg missed µAh per production: ${totalAvgPerProd.toFixed(1)} µAh/prod</span>
                <span style="font-size: 13px; color: #666;">${avgDetail}</span>
            </div>
        </div>`;

        // Build table HTML
        let tableHtml = '';
        if (filtered.gallium.length > 0)  tableHtml += generateIsotopeTable('Gallium',  filtered.gallium,  'gallium');
        if (filtered.rubidium.length > 0) tableHtml += generateIsotopeTable('Rubidium', filtered.rubidium, 'rubidium');
        if (filtered.indium.length > 0)   tableHtml += generateIsotopeTable('Indium',   filtered.indium,   'indium');
        if (filtered.thallium.length > 0) tableHtml += generateIsotopeTable('Thallium', filtered.thallium, 'thallium');
        if (filtered.iodine.length > 0)   tableHtml += generateIsotopeTable('Iodine',   filtered.iodine,   'iodine');

        if (tableHtml === '') {
            content.innerHTML = '<p style="text-align: center; color: #666; font-size: 18px; margin: 40px 0;">No productions found for this time period.</p>';
            return;
        }

        content.innerHTML = html + tableHtml;
    }

    function printPloegModal() {
        const title = document.getElementById('modalTitle').innerHTML;
        const content = document.getElementById('modalContent').innerHTML;
        const periodLabels = { week: '1 Week', month: 'Past 30 Days', '3months': 'Past 3 Months', '6months': 'Past 6 Months' };
        const periodLabel = periodLabels[currentFilter] || currentFilter;
        const win = window.open('', '_blank');
        win.document.write(`<!DOCTYPE html><html><head><title>${title.replace(/<[^>]+>/g,'')}</title>
        <style>
            body { font-family: Segoe UI, sans-serif; padding: 20px; font-size: 12px; }
            h1 { font-size: 18px; margin-bottom: 4px; }
            .period { color: #666; margin-bottom: 16px; font-size: 13px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th { background: #662678; color: white; padding: 6px 8px; text-align: left; font-size: 11px; }
            td { padding: 5px 8px; border-bottom: 1px solid #ddd; }
            tr[style*="ffaaaa"] td { background-color: #ffaaaa; }
            h3 { margin: 16px 0 6px; font-size: 14px; border-bottom: 2px solid #662678; padding-bottom: 4px; }
            @media print { button { display: none; } }
        </style></head><body>
        <h1>${title.replace(/<[^>]+>/g,'')}</h1>
        <div class="period">Period: ${periodLabel}</div>
        ${content}
        <script>window.onload = function(){ window.print(); }</` + `script>
        </body></html>`);
        win.document.close();
    }

    function generateIsotopeTable(isotopeName, productions, isotopeType) {
        let html = '<div style="margin-bottom: 40px;"><h3 style="color: #662678; border-bottom: 2px solid #E40D7E; padding-bottom: 10px;">' + isotopeName + ' (' + productions.length + ' productions)</h3>';
        html += '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 13px;"><thead><tr style="background: linear-gradient(135deg, #662678, #E40D7E); color: white;">';

        // Headers based on isotope type - Order: Shift | Date | BO | Main Metric | Duur | Opmerking | Specific | Ploeg% | Result
        if (isotopeType === 'gallium') {
            html += '<th style="padding: 8px;">Shift</th><th>Date</th><th>BO nummer</th><th>Targetstroom (µA)</th><th>Duur (h)</th><th>Opmerking</th><th>Cyclotron</th><th>Ploeg %</th><th>Result</th>';
        } else if (isotopeType === 'rubidium') {
            html += '<th style="padding: 8px;">Shift</th><th>Date</th><th>BO nummer</th><th>Stroom (µA)</th><th>Duur (h)</th><th>Opmerking</th><th>Efficiency (%)</th><th>Ploeg %</th><th>Result</th>';
        } else if (isotopeType === 'indium') {
            html += '<th style="padding: 8px;">Shift</th><th>Date</th><th>BO nummer</th><th>Targetstroom (µA)</th><th>Duur (h)</th><th>Opmerking</th><th>Bestralingspositie</th><th>Ploeg %</th><th>Result</th>';
        } else if (isotopeType === 'thallium') {
            html += '<th style="padding: 8px;">Shift</th><th>Date</th><th>BO nummer</th><th>Targetstroom (µA)</th><th>Duur (h)</th><th>Opmerking</th><th>Kant</th><th>Ploeg %</th><th>Result</th>';
        } else if (isotopeType === 'iodine') {
            html += '<th style="padding: 8px;">Shift</th><th>Date</th><th>BO nummer</th><th>BO Target (µA)</th><th>Actual Stroom (µA)</th><th>Duur (h)</th><th>Opmerking</th><th>Meting D1 (MBq)</th><th>Verwacht (MBq)</th><th>Yield %</th><th>Output %</th><th>Ploeg %</th><th>Result</th>';
        }

        html += '</tr></thead><tbody>';

        // Merge rows with the same BO nummer — sum proportions, collect shifts
        const mergedMap = new Map();
        productions.forEach(prod => {
            const boKey = prod.data['bo_nummer'] != null ? String(Math.round(prod.data['bo_nummer'])) : '__none__';
            if (mergedMap.has(boKey)) {
                const existing = mergedMap.get(boKey);
                existing.proportion += prod.proportion;
                if (prod.shift && !existing.shifts.includes(prod.shift)) {
                    existing.shifts.push(prod.shift);
                }
            } else {
                mergedMap.set(boKey, {
                    ...prod,
                    proportion: prod.proportion,
                    shifts: prod.shift ? [prod.shift] : []
                });
            }
        });

        // Rows
        mergedMap.forEach(prod => {
            const bgColor = prod.in_spec ? '#ffffff' : '#ffaaaa';
            const result = prod.in_spec ? '✅ PASS' : '❌ FAIL';
            const shiftDisplay = prod.shifts.length > 0 ? prod.shifts.join('+') : '-';

            html += '<tr style="background-color: ' + bgColor + '; border-bottom: 1px solid #ddd;">';

            if (isotopeType === 'gallium') {
                html += '<td style="padding: 8px;">' + shiftDisplay + '</td>';
                html += '<td>' + formatDate(prod.date) + '</td>';
                html += '<td>' + formatBONumber(prod.data['bo_nummer']) + '</td>';
                html += '<td>' + formatValue(prod.data['targetstroom']) + '</td>';
                html += '<td>' + formatValue(prod.data['duur']) + '</td>';
                html += '<td>' + formatValue(prod.data['opmerking']) + '</td>';
                html += '<td>' + formatValue(prod.data['cyclotron']) + '</td>';
                html += '<td style="font-weight: bold;">' + prod.proportion.toFixed(1) + '%</td>';
                html += '<td style="font-weight: bold;">' + result + '</td>';
            } else if (isotopeType === 'rubidium') {
                html += '<td style="padding: 8px;">' + shiftDisplay + '</td>';
                html += '<td>' + formatDate(prod.date) + '</td>';
                html += '<td>' + formatBONumber(prod.data['bo_nummer']) + '</td>';
                html += '<td>' + formatValue(prod.data['stroom']) + '</td>';
                html += '<td>' + formatValue(prod.data['duur']) + '</td>';
                html += '<td>' + formatValue(prod.data['opmerking']) + '</td>';
                html += '<td>' + formatValue(prod.data['efficiency']) + '</td>';
                html += '<td style="font-weight: bold;">' + prod.proportion.toFixed(1) + '%</td>';
                html += '<td style="font-weight: bold;">' + result + '</td>';
            } else if (isotopeType === 'indium') {
                html += '<td style="padding: 8px;">' + shiftDisplay + '</td>';
                html += '<td>' + formatDate(prod.date) + '</td>';
                html += '<td>' + formatBONumber(prod.data['bo_nummer']) + '</td>';
                html += '<td>' + formatValue(prod.data['targetstroom']) + '</td>';
                html += '<td>' + formatValue(prod.data['duur']) + '</td>';
                html += '<td>' + formatValue(prod.data['opmerking']) + '</td>';
                html += '<td>' + formatValue(prod.data['bestralingspositie']) + '</td>';
                html += '<td style="font-weight: bold;">' + prod.proportion.toFixed(1) + '%</td>';
                html += '<td style="font-weight: bold;">' + result + '</td>';
            } else if (isotopeType === 'thallium') {
                html += '<td style="padding: 8px;">' + shiftDisplay + '</td>';
                html += '<td>' + formatDate(prod.date) + '</td>';
                html += '<td>' + formatBONumber(prod.data['bo_nummer']) + '</td>';
                html += '<td>' + formatValue(prod.data['targetstroom']) + '</td>';
                html += '<td>' + formatValue(prod.data['duur']) + '</td>';
                html += '<td>' + formatValue(prod.data['opmerking']) + '</td>';
                html += '<td>' + formatValue(prod.data['kant']) + '</td>';
                html += '<td style="font-weight: bold;">' + prod.proportion.toFixed(1) + '%</td>';
                html += '<td style="font-weight: bold;">' + result + '</td>';
            } else if (isotopeType === 'iodine') {
                html += '<td style="padding: 8px;">' + shiftDisplay + '</td>';
                html += '<td>' + formatDate(prod.date) + '</td>';
                html += '<td>' + formatBONumber(prod.data['bo_nummer']) + '</td>';
                const boTarget = prod.data['bo_targetstroom'];
                html += '<td style="font-weight:bold;">' + (boTarget != null && boTarget !== -999 ? parseFloat(boTarget).toFixed(1) : '-') + '</td>';
                html += '<td>' + formatValue(prod.data['targetstroom']) + '</td>';
                html += '<td>' + formatValue(prod.data['duur']) + '</td>';
                html += '<td>' + formatValue(prod.data['opmerking']) + '</td>';
                html += '<td>' + formatValue(prod.data['meting_d1']) + '</td>';
                html += '<td>' + formatValue(prod.data['verwacht']) + '</td>';
                html += '<td>' + formatValue(prod.data['yield_percent']) + '</td>';
                html += '<td>' + formatValue(prod.data['output_percent']) + '</td>';
                html += '<td style="font-weight: bold;">' + prod.proportion.toFixed(1) + '%</td>';
                html += '<td style="font-weight: bold;">' + result + '</td>';
            }

            html += '</tr>';
        });

        html += '</tbody></table></div></div>';
        return html;
    }

    function formatDate(dateStr) {{
        if (!dateStr) return '-';
        try {{
            // Parse the date string (format: YYYY-MM-DD HH:MM)
            const date = new Date(dateStr);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes;
        }} catch (e) {{
            return dateStr;
        }}
    }}

    function formatBONumber(value) {{
        if (value === null || value === undefined || value === '') return '-';
        // Format BO numbers as integers (no decimals)
        if (typeof value === 'number') return Math.round(value).toString();
        return value;
    }}

    function formatDuration(value) {{
        // Format duration from HH.MM format to HH:MM display
        // e.g., 9.05 → "9:05", 12.30 → "12:30"
        if (value === null || value === undefined || value === '') return '-';

        const str = String(value);
        if (str.includes('.')) {{
            const parts = str.split('.');
            const hours = parts[0];
            const minutes = parts[1].padStart(2, '0'); // Ensure 2 digits
            return hours + ':' + minutes;
        }}
        return str + ':00'; // If no decimal, assume whole hours
    }}

    function formatDurationFromDecimal(value) {{
        // Format duration from decimal hours to HH:MM display
        // e.g., 10.5 → "10:30", 9.0833 → "9:05", 7.75 → "7:45"
        if (value === null || value === undefined || value === '') return '-';

        const hours = Math.floor(value);
        const minutes = Math.round((value - hours) * 60);
        return hours + ':' + String(minutes).padStart(2, '0');
    }}

    function formatValue(value) {{
        if (value === null || value === undefined || value === '') return '-';
        if (typeof value === 'number') return value.toFixed(2);
        return value;
    }}

    // Close modal when clicking outside
    window.onclick = function(event) {
        const ploegModal = document.getElementById('ploegModal');
        if (event.target == ploegModal) {
            closePloegModal();
        }

        const dosisModal = document.getElementById('dosisModal');
        if (event.target == dosisModal) {
            closeDosisModal();
        }

        const sfModal = document.getElementById('sfModal');
        if (event.target == sfModal) {
            closeSFModal();
        }
    }

    // Restore modal state from localStorage on page load (for persistence across 60-second updates)
    window.addEventListener('DOMContentLoaded', function() {
        const modalOpen = localStorage.getItem('modalOpen');
        if (modalOpen === 'true') {
            const ploegNumber = localStorage.getItem('modalPloegNumber');
            const filter = localStorage.getItem('modalFilter') || '6months';

            if (ploegNumber) {
                // Restore modal with same ploeg and filter
                currentPloegNumber = parseInt(ploegNumber);
                currentFilter = filter;
                const modal = document.getElementById('ploegModal');
                modal.style.display = 'block';

                // Get ploeg name
                const ploegName = getPloegName(currentPloegNumber);
                document.getElementById('modalTitle').innerHTML = 'Production Details: ' + ploegName;

                // Filter and display data with saved filter
                filterPloegData(filter);
            }
        }
    });

    // Production History modal functions
    function showProductionHistory(boNummer, date, isotope) {
        const modal = document.getElementById('productionModal');
        const titleEl = document.getElementById('productionModalTitle');
        const contentEl = document.getElementById('productionModalContent');

        // Set title
        titleEl.innerHTML = `Production History: BO ${boNummer} (${isotope})`;

        // Get production history
        const history = productionHistory[boNummer];

        if (!history || !history.shifts || history.shifts.length === 0) {
            contentEl.innerHTML = '<p style="text-align: center; padding: 20px;">No shift history available for this production.</p>';
            modal.style.display = 'block';

            // Save state
            localStorage.setItem('productionModalOpen', 'true');
            localStorage.setItem('productionModalBO', boNummer);
            localStorage.setItem('productionModalIsotope', isotope);
            return;
        }

        // Calculate production window: Use stored BOB/EOB if available
        const shifts = history.shifts;
        const prodData = history.production_data || {};
        const bobTime = prodData.bob_time || (shifts.length > 0 ? shifts[0].date : '-');
        const eobTime = prodData.eob_time || (shifts.length > 0 ? shifts[shifts.length - 1].date : '-');

        // Build production window info box
        let productionWindow = '';
        if (history.production_data) {
            productionWindow = `<div style="background-color: #f0f0f0; padding: 15px; margin-bottom: 20px; border-left: 4px solid #662678; border-radius: 4px;">
                <div style="font-weight: bold; margin-bottom: 8px; color: #662678; font-size: 16px;">Production Window</div>
                <div style="font-size: 14px; line-height: 1.6;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span><strong>BOB (Start):</strong></span>
                        <span style="color: #3BB143; font-weight: bold;">${bobTime}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span><strong>EOB (End):</strong></span>
                        <span style="color: #E40D7E; font-weight: bold;">${eobTime}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span><strong>Duration:</strong></span>
                        <span>${formatDurationFromDecimal(prodData.duur)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span><strong>Target Current:</strong></span>
                        <span>${prodData.targetstroom || '-'}</span>
                    </div>
                </div>
            </div>`;
        }

        // Build table
        let html = productionWindow + `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: linear-gradient(135deg, #662678, #E40D7E); color: white;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Date/Time</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd;">Shift</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Ploeg</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd;">Contribution</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Shifts should already be sorted chronologically from Python
        for (let i = 0; i < shifts.length; i++) {
            const shift = shifts[i];
            const shiftColor = {
                'OD': '#3BB143',  // Green for morning
                'MD': '#FFA500',  // Orange for afternoon
                'ND': '#4169E1'   // Blue for night
            }[shift.shift] || '#000000';

            // Format proportion as percentage
            const proportion = shift.proportion ? Math.round(shift.proportion) : 0;
            const proportionColor = proportion >= 50 ? '#3BB143' : (proportion >= 25 ? '#FFA500' : '#FF2400');

            // Add visual indicator for first (BOB) and last (EOB) entries
            let timeLabel = shift.date;
            if (i === 0) {
                timeLabel = `<strong style="color: #3BB143;">▶</strong> ${shift.date}`;
            } else if (i === shifts.length - 1) {
                timeLabel = `<strong style="color: #E40D7E;">◼</strong> ${shift.date}`;
            }

            html += `
                <tr style="background-color: ${i % 2 === 0 ? '#f9f9f9' : '#ffffff'};">
                    <td style="padding: 10px; border: 1px solid #ddd; font-size: 14px;">${timeLabel}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                        <span style="font-weight: bold; color: ${shiftColor}; font-size: 16px;">${shift.shift}</span>
                    </td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-size: 14px;">${shift.ploeg_name}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                        <span style="font-weight: bold; color: ${proportionColor}; font-size: 16px;">${proportion}%</span>
                    </td>
                </tr>
            `;
        }

        html += '</tbody></table>';

        contentEl.innerHTML = html;
        modal.style.display = 'block';

        // Save state for persistence
        localStorage.setItem('productionModalOpen', 'true');
        localStorage.setItem('productionModalBO', boNummer);
        localStorage.setItem('productionModalIsotope', isotope);
    }

    function closeProductionModal() {
        document.getElementById('productionModal').style.display = 'none';
        localStorage.setItem('productionModalOpen', 'false');
    }

    // Restore production modal on page load
    window.addEventListener('DOMContentLoaded', function() {
        const modalOpen = localStorage.getItem('productionModalOpen');
        if (modalOpen === 'true') {
            const boNummer = localStorage.getItem('productionModalBO');
            const isotope = localStorage.getItem('productionModalIsotope');
            if (boNummer && isotope) {
                showProductionHistory(boNummer, '', isotope);
            }
        }
    });

    // Close production modal when clicking outside
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('productionModal');
        if (event.target == modal) {
            closeProductionModal();
        }
    });

    // Dosisoverzicht modal functions
    function openDosisModal() {{
        document.getElementById('dosisModal').style.display = 'block';
        localStorage.setItem('dosisModalOpen', 'true');
    }}

    function closeDosisModal() {{
        document.getElementById('dosisModal').style.display = 'none';
        localStorage.setItem('dosisModalOpen', 'false');
    }}

    // Restore modal state on page load
    window.addEventListener('load', function() {{
        if (localStorage.getItem('dosisModalOpen') === 'true') {{
            document.getElementById('dosisModal').style.display = 'block';
        }}
        if (localStorage.getItem('dmVsmModalOpen') === 'true') {{
            document.getElementById('dmVsmModal').style.display = 'block';
        }}
    }});

    // DM VSM modal functions
    function openDmVsmModal() {{
        document.getElementById('dmVsmModal').style.display = 'block';
        localStorage.setItem('dmVsmModalOpen', 'true');
    }}

    function closeDmVsmModal() {{
        document.getElementById('dmVsmModal').style.display = 'none';
        localStorage.setItem('dmVsmModalOpen', 'false');
    }}

    // Close DM VSM modal on outside click
    window.addEventListener('click', function(event) {{
        var dmVsmModal = document.getElementById('dmVsmModal');
        if (event.target == dmVsmModal) {{
            closeDmVsmModal();
        }}
    }});

    // Rooster en targetvoorraad modal functions
    function openRoosterModal() {{
        var m = document.getElementById('roosterModal');
        m.style.display = 'flex';
        localStorage.setItem('roosterModalOpen', 'true');
    }}

    function closeRoosterModal() {{
        var m = document.getElementById('roosterModal');
        m.style.display = 'none';
        localStorage.setItem('roosterModalOpen', 'false');
    }}

    // Restore rooster modal state on page load
    window.addEventListener('load', function() {{
        if (localStorage.getItem('roosterModalOpen') === 'true') {{
            document.getElementById('roosterModal').style.display = 'flex';
        }}
    }});

    // Close rooster modal on outside click
    window.addEventListener('click', function(event) {{
        var roosterModal = document.getElementById('roosterModal');
        if (event.target == roosterModal) {{
            closeRoosterModal();
        }}
    }});

    // Productieschema modal functions
    function openProductieschemaModal() {{
        document.getElementById('productieschemaModal').style.display = 'flex';
        localStorage.setItem('productieschemaModalOpen', 'true');
    }}

    function closeProductieschemaModal() {{
        document.getElementById('productieschemaModal').style.display = 'none';
        localStorage.setItem('productieschemaModalOpen', 'false');
    }}

    // Restore productieschema modal state on page load
    window.addEventListener('load', function() {{
        if (localStorage.getItem('productieschemaModalOpen') === 'true') {{
            document.getElementById('productieschemaModal').style.display = 'flex';
        }}
    }});

    // Close productieschema modal on outside click
    window.addEventListener('click', function(event) {{
        var productieschemaModal = document.getElementById('productieschemaModal');
        if (event.target == productieschemaModal) {{
            closeProductieschemaModal();
        }}
    }});


    // SF Modal functions
    function showSFModal(sfCode, count) {{
        const modal = document.getElementById('sfModal');
        const titleEl = document.getElementById('sfModalTitle');
        const contentEl = document.getElementById('sfModalContent');

        titleEl.innerHTML = 'Affected productions: ' + count;

        // Get productions for this SF code
        const productions = sfProductionData[sfCode] || [];

        if (productions.length === 0) {{
            contentEl.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">No productions found for this SF code.</p>';
            modal.style.display = 'block';
            return;
        }}

        // Sort by date descending
        productions.sort((a, b) => {{
            if (a.date > b.date) return -1;
            if (a.date < b.date) return 1;
            return 0;
        }});

        // Build table
        let html = '<table style="width: 100%; border-collapse: collapse;">';
        html += '<thead>';
        html += '<tr style="background: linear-gradient(135deg, #662678, #E40D7E); color: white;">';
        html += '<th style="padding: 10px; text-align: left; border: 1px solid #ddd;">BO Number</th>';
        html += '<th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Isotope</th>';
        html += '<th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Date</th>';
        html += '<th style="padding: 10px; text-align: center; border: 1px solid #ddd;">Value</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody>';

        for (let i = 0; i < productions.length; i++) {{
            const prod = productions[i];
            const bgColor = i % 2 === 0 ? '#f9f9f9' : '#ffffff';
            const value = prod.unit ? prod.value + prod.unit : prod.value;

            // Format date to only show YYYY-MM-DD (remove time if present)
            let dateStr = prod.date;
            if (dateStr && dateStr.includes(' ')) {{
                dateStr = dateStr.split(' ')[0];
            }}
            if (dateStr && dateStr.includes('T')) {{
                dateStr = dateStr.split('T')[0];
            }}

            html += '<tr style="background-color: ' + bgColor + ';">';
            html += '<td style="padding: 10px; border: 1px solid #ddd; font-size: 14px;">' + prod.bo_nummer + '</td>';
            html += '<td style="padding: 10px; border: 1px solid #ddd; font-size: 14px;">' + prod.isotope + '</td>';
            html += '<td style="padding: 10px; border: 1px solid #ddd; font-size: 14px;">' + dateStr + '</td>';
            html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 14px; font-weight: bold;">' + value + '</td>';
            html += '</tr>';
        }}

        html += '</tbody></table>';

        contentEl.innerHTML = html;
        modal.style.display = 'block';

        // Save state for persistence
        localStorage.setItem('sfModalOpen', 'true');
        localStorage.setItem('sfModalCode', sfCode);
        localStorage.setItem('sfModalCount', count);
    }}

    function closeSFModal() {{
        document.getElementById('sfModal').style.display = 'none';
        localStorage.setItem('sfModalOpen', 'false');
    }}

    // Restore SF modal on page load
    window.addEventListener('DOMContentLoaded', function() {{
        const sfModalOpen = localStorage.getItem('sfModalOpen');
        if (sfModalOpen === 'true') {{
            const sfCode = localStorage.getItem('sfModalCode');
            const count = localStorage.getItem('sfModalCount');
            if (sfCode && count) {{
                showSFModal(sfCode, parseInt(count));
            }}
        }}
    }});

    <!-- __OTIF_JS__ -->
    </script>

    </body>
    </html>"""

    # Inject OTIF JS and scroll/refresh JS via replace (avoids f-string brace escaping issues)
    html = html.replace('<meta http-equiv="refresh" content="60">', '')
    html = html.replace('<!-- __OTIF_JS__ -->', scroll_refresh_js + otif_charts_js)

    return html
