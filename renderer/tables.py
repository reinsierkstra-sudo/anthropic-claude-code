"""
renderer/tables.py
------------------
Reusable HTML table-building helpers extracted from the
IsotopeDashboardGenerator class in gallium_extractor.py.

All functions are pure: they accept data arguments and return HTML
strings.  No class state is required.

SPEC_SETTINGS is imported from the top-level gallium_extractor module
so that colour-threshold logic stays in one canonical location.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Spec settings — imported from the source module so thresholds live in one
# place.  The ``try`` block allows this module to be imported even when the
# monolithic source is not on sys.path (e.g. in unit tests).
# ---------------------------------------------------------------------------
try:
    from gallium_extractor import SPEC_SETTINGS, _fmt_bo
except ImportError:
    # Fallback defaults — keep in sync with gallium_extractor.py
    SPEC_SETTINGS: dict = {}

    def _fmt_bo(bo):
        """Format a BO number: strip trailing .0 and dashes."""
        if bo is None:
            return None
        if str(bo).replace('.', '').replace('-', '').isdigit():
            return str(int(float(bo)))
        return bo


# ---------------------------------------------------------------------------
# Colour helpers (mirrors the @staticmethod colour helpers on the class)
# ---------------------------------------------------------------------------

def _get_efficiency_color(efficiency) -> str:
    """Return green / red hex colour for Rubidium efficiency value."""
    if efficiency is None:
        return '#000000'
    spec = SPEC_SETTINGS.get('rubidium', {})
    mn, mx = spec.get('min', 95), spec.get('max', 105)
    return '#3BB143' if mn <= round(efficiency) <= mx else '#FF2400'


def _get_rb_stroom_color(stroom) -> str:
    """Return colour for Rubidium stroom value (67–72 µA = green)."""
    return '#3BB143' if stroom is not None and 67 <= stroom <= 72 else '#FF2400'


def _get_targetstroom_color(targetstroom, isotope_type: str, cyclotron=None) -> str:
    """Return green / red hex colour for a targetstroom measurement."""
    if targetstroom is None:
        return '#000000'
    ts = round(targetstroom)
    if isotope_type == 'thallium':
        spec = SPEC_SETTINGS.get('thallium', {})
    elif isotope_type in ('gallium', 'indium'):
        key = 'iba' if (cyclotron and str(cyclotron).upper().startswith('IBA')) else 'philips'
        spec = SPEC_SETTINGS.get(isotope_type, {}).get(key, {})
    else:
        return '#000000'
    mn, mx = spec.get('min', 0), spec.get('max', 9999)
    return '#3BB143' if mn <= ts <= mx else '#FF2400'


def _get_iodine_yield_color(yield_percent) -> str:
    """Green if yield >= minimum threshold, else red."""
    if yield_percent is None:
        return '#000000'
    threshold = (
        SPEC_SETTINGS.get('iodine', {})
        .get('chart_colors', {})
        .get('yield', {})
        .get('min', 80)
    )
    return '#3BB143' if yield_percent >= threshold else '#FF2400'


def _get_iodine_output_color(output_percent) -> str:
    """Green if output is within spec, else red."""
    if output_percent is None:
        return '#000000'
    spec = (
        SPEC_SETTINGS.get('iodine', {})
        .get('within_spec', {})
        .get('output', {})
    )
    mn, mx = spec.get('min', 78), spec.get('max', 114.9)
    return '#3BB143' if mn <= output_percent <= mx else '#FF2400'


def _get_iodine_targetstroom_color(targetstroom) -> str:
    """Green if iodine targetstroom is within spec, else red."""
    if targetstroom is None:
        return '#000000'
    spec = (
        SPEC_SETTINGS.get('iodine', {})
        .get('within_spec', {})
        .get('targetstroom', {})
    )
    mn, mx = spec.get('min', 96), spec.get('max', 124)
    return '#3BB143' if mn <= targetstroom <= mx else '#FF2400'


def _get_iodine_color(record: dict) -> str:
    """Aggregate colour for an Iodine record (output + targetstroom + yield)."""
    output = record.get('output_percent')
    yield_pct = record.get('yield_percent')
    targetstroom = record.get('targetstroom')
    spec = SPEC_SETTINGS.get('iodine', {}).get('within_spec', {})
    out_spec = spec.get('output', {})
    ts_spec = spec.get('targetstroom', {})

    output_ok = (
        out_spec.get('min', 78) <= output <= out_spec.get('max', 114.9)
        if output is not None else False
    )
    targetstroom_ok = (
        ts_spec.get('min', 96) <= targetstroom <= ts_spec.get('max', 124)
        if targetstroom is not None else False
    )
    yield_threshold = (
        SPEC_SETTINGS.get('iodine', {})
        .get('chart_colors', {})
        .get('yield', {})
        .get('min', 80)
    )
    yield_good = yield_pct >= yield_threshold if yield_pct is not None else False

    if output_ok and targetstroom_ok:
        return '#3BB143' if yield_good else '#FFA500'
    return '#FF2400'


# ---------------------------------------------------------------------------
# Cell formatters — mirrors the _fmt_* instance methods on the class
# ---------------------------------------------------------------------------

def _fmt_targetstroom_cell(
    record: dict | None,
    isotope_type: str,
    isotope_label: str,
    with_onclick: bool = False,
) -> str:
    """Format a targetstroom (µA) table cell as HTML.

    *isotope_type* is the lowercase string used for colour look-up
    (e.g. ``'gallium'``).  *isotope_label* is the display name used in
    the ``showProductionHistory`` JS call (e.g. ``'Gallium'``).
    """
    if record is None or record.get('targetstroom') is None:
        return ''
    bo = record.get('identifier', '')
    date = record.get('date', '')
    bo_fmt = _fmt_bo(bo)
    color = _get_targetstroom_color(
        record['targetstroom'], isotope_type, record.get('cyclotron')
    )
    val = f"{round(record['targetstroom'])}µA"
    if with_onclick:
        bo_span = (
            f"<span onclick=\"showProductionHistory('{bo}', '{date}', '{isotope_label}')\" "
            f"style='color: black; font-size: 15px; font-weight: bold; cursor: pointer; "
            f"text-decoration: underline;'>{bo_fmt}</span>"
        )
    else:
        bo_span = f"<span style='color: black; font-size: 15px; font-weight: bold;'>{bo_fmt}</span>"
    return f"{bo_span} <span style='color: {color}; font-weight: bold; font-size: 25px;'>{val}</span>"


def _fmt_rb_cell(record: dict | None, with_onclick: bool = False) -> str:
    """Format a Rubidium table cell as HTML: 'BO XX% XXµA'."""
    if record is None or record.get('efficiency') is None:
        return ''
    bo = record.get('identifier', '')
    rec_date = record.get('date', '')
    bo_fmt = _fmt_bo(bo)
    eff_color = _get_efficiency_color(record['efficiency'])
    stroom = record.get('stroom')
    stroom_color = _get_rb_stroom_color(stroom)
    stroom_str = f"{round(stroom)}µA" if stroom is not None else 'N/A'
    if with_onclick:
        bo_span = (
            f"<span onclick=\"showProductionHistory('{bo}', '{rec_date}', 'Rubidium')\" "
            f"style='color: black; font-size: 15px; font-weight: bold; cursor: pointer; "
            f"text-decoration: underline;'>{bo_fmt}</span>"
        )
    else:
        bo_span = f"<span style='color: black; font-size: 15px; font-weight: bold;'>{bo_fmt}</span>"
    return (
        f"{bo_span} "
        f"<span style='color: {eff_color}; font-weight: bold; font-size: 25px;'>"
        f"{round(record['efficiency'])}%</span> "
        f"<span style='color: {stroom_color}; font-weight: bold; font-size: 25px;'>{stroom_str}</span>"
    )


def _fmt_io_cell(record: dict | None, with_onclick: bool = False) -> str:
    """Format an Iodine table cell as HTML."""
    if record is None:
        return ''
    bo = record.get('identifier', '')
    date = record.get('date', '')
    bo_fmt = _fmt_bo(bo)
    if with_onclick:
        bo_span = (
            f"<span onclick=\"showProductionHistory('{bo}', '{date}', 'Iodine')\" "
            f"style='color: black; font-size: 15px; font-weight: bold; cursor: pointer; "
            f"text-decoration: underline;'>{bo_fmt}</span>"
        )
        yield_color  = _get_iodine_yield_color(record.get('yield_percent'))
        output_color = _get_iodine_output_color(record.get('output_percent'))
        target_color = _get_iodine_targetstroom_color(record.get('targetstroom'))
        io_yield  = f"{round(record['yield_percent'], 1)}%"  if record.get('yield_percent')  is not None else "N/A"
        io_output = f"{round(record['output_percent'], 1)}%" if record.get('output_percent') is not None else "N/A"
        io_target = (
            f"{round(record['targetstroom'])}µA"
            if record.get('targetstroom') is not None
            else "N/A"
        )
        return (
            f"{bo_span} "
            f"<span style='color: {yield_color}; font-weight: bold; font-size: 25px;'>{io_yield}</span>"
            f"<span style='color: black; font-weight: bold; font-size: 25px;'>/</span>"
            f"<span style='color: {output_color}; font-weight: bold; font-size: 25px;'>{io_output}</span>"
            f"  <span style='color: {target_color}; font-weight: bold; font-size: 25px;'>{io_target}</span>"
        )
    else:
        bo_span = f"<span style='color: black; font-size: 15px; font-weight: bold;'>{bo_fmt}</span>"
        io_color = _get_iodine_color(record)
        io_yield  = round(record['yield_percent'])  if record.get('yield_percent')  else '-'
        io_output = round(record['output_percent']) if record.get('output_percent') else '-'
        io_target = round(record['targetstroom'])   if record.get('targetstroom')   else '-'
        return (
            f"{bo_span} <span style='color: {io_color}; font-weight: bold; font-size: 25px;'>"
            f"{io_yield}%/{io_output}% + {io_target}µA</span>"
        )


# ---------------------------------------------------------------------------
# Weekly summary row builder
# ---------------------------------------------------------------------------

def _build_week_table_rows(
    ga: list,
    rb: list,
    in_: list,
    tl_12: list,
    tl_21: list,
    io: list,
    *,
    with_onclick: bool = False,
) -> str:
    """Build ``<tr>`` rows for a week's production summary table.

    Returns an HTML string of zero or more ``<tr>`` elements, or an
    empty string when all input lists are empty.
    """
    if not any([ga, rb, in_, tl_12, tl_21, io]):
        return ''
    rows = ''
    n = max(len(ga), len(rb), len(in_), len(tl_12), len(tl_21), len(io))
    for i in range(n):
        ga_val   = _fmt_targetstroom_cell(ga[i]    if i < len(ga)    else None, 'gallium',  'Gallium',  with_onclick)
        rb_val   = _fmt_rb_cell          (rb[i]    if i < len(rb)    else None,                          with_onclick)
        in_val   = _fmt_targetstroom_cell(in_[i]   if i < len(in_)   else None, 'indium',   'Indium',   with_onclick)
        tl12_val = _fmt_targetstroom_cell(tl_12[i] if i < len(tl_12) else None, 'thallium', 'Thallium', with_onclick)
        tl21_val = _fmt_targetstroom_cell(tl_21[i] if i < len(tl_21) else None, 'thallium', 'Thallium', with_onclick)
        io_val   = _fmt_io_cell          (io[i]    if i < len(io)    else None,                          with_onclick)
        rows += (
            f'<tr><td>{ga_val}</td><td>{rb_val}</td><td>{in_val}</td>'
            f'<td>{tl12_val}</td><td>{tl21_val}</td><td>{io_val}</td></tr>'
        )
    return rows


# ---------------------------------------------------------------------------
# KPI summary tables (efficiency / within-spec / OTIF)
# ---------------------------------------------------------------------------

def build_efficiency_table(
    efficiency_weeks: list,
    efficiency_average: float,
    efficiency_last_year_avg: float,
    efficiency_last_3months_avg: float,
) -> str:
    """Return the HTML ``<div class="section">`` block for the efficiency KPI table.

    *efficiency_weeks* is a list of dicts with keys ``week``,
    ``percentage``, ``color``, and optionally ``no_data``.
    """
    week_headers = ""
    pct_cells = ""
    for week_data in efficiency_weeks:
        week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            pct_cells += (
                "<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-\u200c%</td>"
            )
        else:
            pct_cells += (
                f"<td style='text-align: center; color: {week_data['color']}; "
                f"font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"
            )

    ly_color = '#3BB143' if efficiency_last_year_avg >= efficiency_average else '#FF2400'
    l3m_color = '#3BB143' if efficiency_last_3months_avg >= efficiency_last_year_avg else '#FF2400'

    return f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Effici\u00ebntie Bronfaraday \u2192 Targets</h2>
            <table>
                <thead>
                    <tr>
                        {week_headers if week_headers else '<th>No data available</th>'}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {pct_cells if pct_cells else '<td>No data available</td>'}
                    </tr>
                </tbody>
            </table>
            <div style="text-align: center; margin-top: 10px; font-size: 16px;">
                <span style="color: black; font-weight: bold;">All-time average: {efficiency_average:.1f}%</span>
                <span style="color: {ly_color}; font-weight: bold; margin-left: 20px;">Last year average: {efficiency_last_year_avg:.1f}%</span>
                <span style="color: {l3m_color}; font-weight: bold; margin-left: 20px;">Last 3 months average: {efficiency_last_3months_avg:.1f}%</span>
            </div>
        </div>
        """


def build_within_spec_table(
    within_spec_weeks: list,
    within_spec_average: float,
    within_spec_last_year_avg: float,
    within_spec_last_3months_avg: float,
) -> str:
    """Return the HTML block for the within-spec (success-rate) KPI table.

    *within_spec_weeks* is a list of dicts with keys ``week``,
    ``percentage``, ``color``, and optionally ``no_data``.
    """
    week_headers = ""
    pct_cells = ""
    for week_data in within_spec_weeks:
        week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            pct_cells += (
                "<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-\u200c%</td>"
            )
        else:
            pct_cells += (
                f"<td style='text-align: center; color: {week_data['color']}; "
                f"font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"
            )

    ly_color = '#3BB143' if within_spec_last_year_avg >= within_spec_average else '#FF2400'
    l3m_color = '#3BB143' if within_spec_last_3months_avg >= within_spec_last_year_avg else '#FF2400'

    return f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Success rate (% Binnen Spec)</h2>
            <table>
                <thead>
                    <tr>
                        {week_headers if week_headers else '<th>No data available</th>'}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {pct_cells if pct_cells else '<td>No data available</td>'}
                    </tr>
                </tbody>
            </table>
            <div style="text-align: center; margin-top: 10px; font-size: 16px;">
                <span style="color: black; font-weight: bold;">All-time average: {within_spec_average:.1f}%</span>
                <span style="color: {ly_color}; font-weight: bold; margin-left: 20px;">Last year average: {within_spec_last_year_avg:.1f}%</span>
                <span style="color: {l3m_color}; font-weight: bold; margin-left: 20px;">Last 3 months average: {within_spec_last_3months_avg:.1f}%</span>
            </div>
        </div>
        """


def build_otif_gedraaide_table(
    otif_gedraaide_weeks: list | None,
    otif_gedraaide_average: float,
    otif_gedraaide_last_year_avg: float,
    otif_gedraaide_last_3months_avg: float,
) -> str:
    """Return the HTML block for the OTIF gedraaide-producties KPI table.

    *otif_gedraaide_weeks* is a list of dicts with keys ``week``,
    ``percentage``, ``color``, and optionally ``no_data``.
    """
    weeks = otif_gedraaide_weeks or []
    week_headers = ""
    pct_cells = ""
    for week_data in weeks:
        week_headers += f"<th style='text-align: center;'>Week {week_data['week']}</th>"
        if week_data.get('no_data'):
            pct_cells += (
                "<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-\u200c%</td>"
            )
        else:
            pct_cells += (
                f"<td style='text-align: center; color: {week_data['color']}; "
                f"font-weight: bold; font-size: 20px;'>{week_data['percentage']:.1f}%</td>"
            )

    ly_color  = '#3BB143' if otif_gedraaide_last_year_avg  >= 97 else '#FF2400'
    l3m_color = '#3BB143' if otif_gedraaide_last_3months_avg >= 97 else '#FF2400'

    return f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">OTIF gedraaide producties</h2>
            <p style="color: grey; font-size: 13px; margin-top: -8px; margin-bottom: 10px;">niet gemaakte producties worden buiten beschouwing gelaten</p>
            <table>
                <thead>
                    <tr>
                        {week_headers if week_headers else '<th>No data available</th>'}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {pct_cells if pct_cells else '<td>No data available</td>'}
                    </tr>
                </tbody>
            </table>
            <div style="text-align: center; margin-top: 10px; font-size: 16px;">
                <span style="color: black; font-weight: bold;">All-time average: {otif_gedraaide_average:.1f}%</span>
                <span style="color: {ly_color}; font-weight: bold; margin-left: 20px;">Last year average: {otif_gedraaide_last_year_avg:.1f}%</span>
                <span style="color: {l3m_color}; font-weight: bold; margin-left: 20px;">Last 3 months average: {otif_gedraaide_last_3months_avg:.1f}%</span>
            </div>
        </div>
        """


# ---------------------------------------------------------------------------
# Leaderboard table
# ---------------------------------------------------------------------------

def generate_leaderboard_html(leaderboard: list) -> str:
    """Return the HTML ``<div class="section">`` block for the ploeg leaderboard.

    *leaderboard* is a list of dicts with keys ``name``, ``ploeg_number``,
    ``total``, ``in_spec``, ``percentage``.  Returns an empty string when
    *leaderboard* is empty.
    """
    if not leaderboard:
        return ""

    trophies = {1: "\U0001f947", 2: "\U0001f948", 3: "\U0001f949"}

    avg_percentage = sum(p['percentage'] for p in leaderboard) / len(leaderboard)

    rows = ""
    for idx, ploeg in enumerate(leaderboard, start=1):
        trophy = trophies.get(idx, "")
        if ploeg['percentage'] > avg_percentage + 2:
            color = "#3BB143"
        elif ploeg['percentage'] < avg_percentage - 2:
            color = "#FF2400"
        else:
            color = "#000000"

        rows += f"""                    <tr>
                        <td style='text-align: center; font-size: 24px;'>{trophy if trophy else idx}</td>
                        <td style='text-align: left; font-weight: bold;'>
                            <a href='#' onclick='showPloegDetails({ploeg['ploeg_number']}); return false;' style='color: #662678; text-decoration: none; cursor: pointer;'>
                                {ploeg['name']}
                            </a>
                        </td>
                        <td style='text-align: center;'>{ploeg['total']:.1f}</td>
                        <td style='text-align: center;'>{ploeg['in_spec']:.1f}</td>
                        <td style='text-align: center; color: {color}; font-weight: bold; font-size: 18px;'>{ploeg['percentage']:.1f}%</td>
                    </tr>
"""

    return f"""
        <div class="section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Ploeg Performance Leaderboard (Last 30 Days)</h2>
            <table>
                <thead>
                    <tr>
                        <th style='text-align: center;'>Rank</th>
                        <th style='text-align: left;'>Ploeg</th>
                        <th style='text-align: center;'>Productions</th>
                        <th style='text-align: center;'>In Spec</th>
                        <th style='text-align: center;'>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
{rows}                </tbody>
        </table>
        <div style="text-align: center; margin-top: 20px; font-size: 14px; color: #666; line-height: 1.6;">
            Producties worden proportioneel toegekend op basis van uren per ploeg.<br>
            Bron is bestralingendatabase &amp; P&amp;C
        </div>
        </div>
"""
