"""
renderer/dashboard_truncated.py
---------------------------------
Truncated-dashboard renderer — standalone implementation, no dependency on
gallium_extractor.IsotopeDashboardGenerator.

Public entry point
------------------
``create_truncated_dashboard(data)``

    *data* is a plain dict whose keys correspond 1-to-1 to the positional /
    keyword arguments of the original method.  See ``_DEFAULTS`` below for
    the complete list of expected keys and their defaults.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from renderer.helpers import build_week_table_rows


# ---------------------------------------------------------------------------
# Key catalogue with defaults
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
    # VSM data (not rendered in truncated version but kept for signature compat)
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
    v = _unpack(data)

    ga_running  = v["ga_running"]
    ga_previous = v["ga_previous"]
    rb_running  = v["rb_running"]
    rb_previous = v["rb_previous"]
    in_running  = v["in_running"]
    in_previous = v["in_previous"]
    tl_running  = v["tl_running"]
    tl_previous = v["tl_previous"]
    io_running  = v["io_running"]
    io_previous = v["io_previous"]

    efficiency_weeks            = v["efficiency_weeks"]
    efficiency_average          = v["efficiency_average"]
    efficiency_last_year_avg    = v["efficiency_last_year_avg"]
    efficiency_last_3months_avg = v["efficiency_last_3months_avg"]

    within_spec_weeks            = v["within_spec_weeks"]
    within_spec_average          = v["within_spec_average"]
    within_spec_last_year_avg    = v["within_spec_last_year_avg"]
    within_spec_last_3months_avg = v["within_spec_last_3months_avg"]

    tampering_warning = v["tampering_warning"]

    otif_gedraaide_weeks            = v["otif_gedraaide_weeks"] or []
    otif_gedraaide_average          = v["otif_gedraaide_average"]
    otif_gedraaide_last_year_avg    = v["otif_gedraaide_last_year_avg"]
    otif_gedraaide_last_3months_avg = v["otif_gedraaide_last_3months_avg"]

    # ── Efficiency table ────────────────────────────────────────────────────
    efficiency_week_headers    = ""
    efficiency_percentage_cells = ""

    for week_data in efficiency_weeks:
        efficiency_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            efficiency_percentage_cells += (
                "<td style='text-align: center; color: #aaa; font-weight: bold; "
                "font-size: 20px;'>--.-\u200c%</td>"
            )
        else:
            efficiency_percentage_cells += (
                f"<td style='text-align: center; color: {week_data['color']}; "
                f"font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"
            )

    efficiency_table = f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Effici\u00ebntie Bronfaraday \u2192 Targets</h2>
            <table>
                <thead>
                    <tr>
                        {efficiency_week_headers if efficiency_week_headers else "<th>No data available</th>"}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {efficiency_percentage_cells if efficiency_percentage_cells else "<td>No data available</td>"}
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

    # ── Within-spec table ───────────────────────────────────────────────────
    within_spec_week_headers    = ""
    within_spec_percentage_cells = ""

    for week_data in within_spec_weeks:
        within_spec_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            within_spec_percentage_cells += (
                "<td style='text-align: center; color: #aaa; font-weight: bold; "
                "font-size: 20px;'>--.-\u200c%</td>"
            )
        else:
            within_spec_percentage_cells += (
                f"<td style='text-align: center; color: {week_data['color']}; "
                f"font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"
            )

    within_spec_table = f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Success rate (% Binnen Spec)</h2>
            <table>
                <thead>
                    <tr>
                        {within_spec_week_headers if within_spec_week_headers else "<th>No data available</th>"}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {within_spec_percentage_cells if within_spec_percentage_cells else "<td>No data available</td>"}
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

    # ── OTIF gedraaide producties table ─────────────────────────────────────
    otif_ged_week_headers    = ""
    otif_ged_percentage_cells = ""

    for week_data in otif_gedraaide_weeks:
        otif_ged_week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            otif_ged_percentage_cells += (
                "<td style='text-align: center; color: #aaa; font-weight: bold; "
                "font-size: 20px;'>--.-\u200c%</td>"
            )
        else:
            otif_ged_percentage_cells += (
                f"<td style='text-align: center; color: {week_data['color']}; "
                f"font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"
            )

    otif_gedraaide_table = f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">OTIF gedraaide producties</h2>
            <p style="color: grey; font-size: 13px; margin-top: -8px; margin-bottom: 10px;">niet gemaakte producties worden buiten beschouwing gelaten</p>
            <table>
                <thead>
                    <tr>
                        {otif_ged_week_headers if otif_ged_week_headers else "<th>No data available</th>"}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {otif_ged_percentage_cells if otif_ged_percentage_cells else "<td>No data available</td>"}
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

    # ── Current-week summary table ───────────────────────────────────────────
    tl_running_12 = [t for t in tl_running if t.get('kant') == '1.2']
    tl_running_21 = [t for t in tl_running if t.get('kant') == '2.1']

    summary_table_rows = build_week_table_rows(
        ga_running, rb_running, in_running, tl_running_12, tl_running_21, io_running)

    summary_table = f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid #FF5722;">Lopende week</h2>
            <table>
                <thead>
                    <tr style="font-size: 18px; font-weight: bold;">
                        <th>Gallium (\u00b5A)</th>
                        <th>Rubidium (% + \u00b5A)</th>
                        <th>Indium (\u00b5A)</th>
                        <th>Thallium 1.2 (\u00b5A)</th>
                        <th>Thallium 2.1 (\u00b5A)</th>
                        <th>Iodine (Yield%/Output% + \u00b5A)</th>
                    </tr>
                </thead>
                <tbody>
                    {summary_table_rows if summary_table_rows else '<tr><td colspan="6">No data available</td></tr>'}
                </tbody>
            </table>
        </div>
        """

    # ── Previous-week summary table ──────────────────────────────────────────
    tl_previous_12 = [t for t in tl_previous if t.get('kant') == '1.2']
    tl_previous_21 = [t for t in tl_previous if t.get('kant') == '2.1']

    summary_table_rows_prev = build_week_table_rows(
        ga_previous, rb_previous, in_previous, tl_previous_12, tl_previous_21, io_previous)

    previous_week_summary_table = f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid #9C27B0;">Afgelopen week</h2>
            <table>
                <thead>
                    <tr style="font-size: 18px; font-weight: bold;">
                        <th>Gallium (\u00b5A)</th>
                        <th>Rubidium (% + \u00b5A)</th>
                        <th>Indium (\u00b5A)</th>
                        <th>Thallium 1.2 (\u00b5A)</th>
                        <th>Thallium 2.1 (\u00b5A)</th>
                        <th>Iodine (Yield%/Output% + \u00b5A)</th>
                    </tr>
                </thead>
                <tbody>
                    {summary_table_rows_prev if summary_table_rows_prev else '<tr><td colspan="6">No data available</td></tr>'}
                </tbody>
            </table>
        </div>
        """

    # ── Assemble HTML ────────────────────────────────────────────────────────
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    tampering_banner = ""
    if tampering_warning:
        tampering_banner = (
            '<div style="background: #FF2400; color: white; padding: 20px; margin-bottom: 30px; '
            'border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; '
            'border: 5px solid #8B0000; animation: pulse 2s infinite;">'
            '<div style="font-size: 48px; margin-bottom: 10px;">\u26a0\ufe0f WARNING \u26a0\ufe0f</div>'
            f'<div>{tampering_warning}</div>'
            '<div style="font-size: 16px; margin-top: 10px;">Manual changes have been detected '
            'and this file will be regenerated.</div>'
            '</div>'
        )

    html = f"""<!DOCTYPE html>
<!--
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551                          \u26a0\ufe0f  WARNING  \u26a0\ufe0f                            \u2551
\u2551                                                                      \u2551
\u2551  DO NOT EDIT THIS FILE MANUALLY!                                    \u2551
\u2551                                                                      \u2551
\u2551  Manual changes will be OVERWRITTEN on next update!                 \u2551
\u2551                                                                      \u2551
\u2551  This file is protected with:                                       \u2551
\u2551  - Read-only permissions                                            \u2551
\u2551  - SHA256 integrity checking                                        \u2551
\u2551                                                                      \u2551
\u2551  Last generated: {now_str}                            \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
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
                <div class="timestamp">Generated: {now_str}</div>
            </div>
            <div class="header-right">
                <img src="logo.png" alt="Logo">
            </div>
        </div>

        {tampering_banner}

        {efficiency_table}

        {within_spec_table}

        {otif_gedraaide_table}

        {summary_table}

        {previous_week_summary_table}

    </div>
</body>
</html>"""

    return html
