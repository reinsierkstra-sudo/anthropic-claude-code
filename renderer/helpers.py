"""
renderer/helpers.py
-------------------
Standalone HTML formatting helpers extracted from IsotopeDashboardGenerator.

Provides
--------
- Cell formatters: ``fmt_targetstroom_cell``, ``fmt_rb_cell``, ``fmt_io_cell``
- Row/table builders: ``build_week_table_rows``, ``generate_ploegen_table_html``
- Ploeg HTML: ``generate_shift_tables_html``, ``generate_leaderboard_html``,
  ``generate_monthly_winner_html``, ``generate_ploeg_rolling_charts_html``
- Utility: ``fmt_bo``, ``fmt_date_str``, ``fmt_kpi_table``
"""

from datetime import datetime, timedelta

from config.spec_settings import (
    get_targetstroom_color,
    get_efficiency_color,
    get_rb_stroom_color,
    get_iodine_yield_color,
    get_iodine_output_color,
    get_iodine_targetstroom_color,
    get_iodine_color,
    get_ploeg_color,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def fmt_bo(bo) -> str:
    """Format a BO number: strip trailing .0 and dashes, return integer string."""
    if bo is None:
        return ''
    if str(bo).replace('.', '').replace('-', '').isdigit():
        return str(int(float(bo)))
    return str(bo)


def fmt_date_str(d) -> str:
    """Format a date-like value as ``YYYY-MM-DD``, or empty string."""
    if d is None:
        return ''
    if isinstance(d, datetime):
        return d.strftime('%Y-%m-%d')
    if hasattr(d, 'strftime'):
        return d.strftime('%Y-%m-%d')
    return str(d)


# ---------------------------------------------------------------------------
# Cell formatters
# ---------------------------------------------------------------------------

def fmt_targetstroom_cell(record, isotope_type: str, isotope_label: str,
                           with_onclick: bool = False) -> str:
    """Format a targetstroom (µA) table cell as HTML."""
    if record is None or record.get('targetstroom') is None:
        return ''
    bo       = record.get('identifier', '')
    date_val = fmt_date_str(record.get('date', ''))
    bo_fmt   = fmt_bo(bo)
    color    = get_targetstroom_color(record['targetstroom'], isotope_type,
                                      record.get('cyclotron'))
    val      = f"{round(record['targetstroom'])}µA"
    if with_onclick:
        bo_span = (
            f"<span onclick=\"showProductionHistory('{bo}', '{date_val}', '{isotope_label}')\" "
            f"style='color: black; font-size: 15px; font-weight: bold; cursor: pointer; "
            f"text-decoration: underline;'>{bo_fmt}</span>"
        )
    else:
        bo_span = f"<span style='color: black; font-size: 15px; font-weight: bold;'>{bo_fmt}</span>"
    return f"{bo_span} <span style='color: {color}; font-weight: bold; font-size: 25px;'>{val}</span>"


def fmt_rb_cell(record, with_onclick: bool = False) -> str:
    """Format a Rubidium table cell as HTML: ``BO XX% XXµA``."""
    if record is None or record.get('efficiency') is None:
        return ''
    bo        = record.get('identifier', '')
    rec_date  = fmt_date_str(record.get('date', ''))
    bo_fmt    = fmt_bo(bo)
    eff_color = get_efficiency_color(record['efficiency'])
    stroom    = record.get('stroom')
    stroom_color = get_rb_stroom_color(stroom)
    stroom_str   = f"{round(stroom)}µA" if stroom is not None else 'N/A'
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


def fmt_io_cell(record, with_onclick: bool = False) -> str:
    """Format an Iodine table cell as HTML."""
    if record is None:
        return ''
    bo       = record.get('identifier', '')
    date_val = fmt_date_str(record.get('date', ''))
    bo_fmt   = fmt_bo(bo)
    if with_onclick:
        bo_span = (
            f"<span onclick=\"showProductionHistory('{bo}', '{date_val}', 'Iodine')\" "
            f"style='color: black; font-size: 15px; font-weight: bold; cursor: pointer; "
            f"text-decoration: underline;'>{bo_fmt}</span>"
        )
        yield_color  = get_iodine_yield_color(record.get('yield_percent'))
        output_color = get_iodine_output_color(record.get('output_percent'))
        target_color = get_iodine_targetstroom_color(record.get('targetstroom'))
        io_yield  = f"{round(record['yield_percent'], 1)}%"  if record.get('yield_percent')  is not None else "N/A"
        io_output = f"{round(record['output_percent'], 1)}%" if record.get('output_percent') is not None else "N/A"
        io_target = (f"{round(record['targetstroom'])}µA"
                     if record.get('targetstroom') is not None else "N/A")
        return (
            f"{bo_span} "
            f"<span style='color: {yield_color}; font-weight: bold; font-size: 25px;'>{io_yield}</span>"
            f"<span style='color: black; font-weight: bold; font-size: 25px;'>/</span>"
            f"<span style='color: {output_color}; font-weight: bold; font-size: 25px;'>{io_output}</span>"
            f"  <span style='color: {target_color}; font-weight: bold; font-size: 25px;'>{io_target}</span>"
        )
    else:
        bo_span   = f"<span style='color: black; font-size: 15px; font-weight: bold;'>{bo_fmt}</span>"
        io_color  = get_iodine_color(record)
        io_yield  = round(record['yield_percent'])  if record.get('yield_percent')  else '-'
        io_output = round(record['output_percent']) if record.get('output_percent') else '-'
        io_target = round(record['targetstroom'])   if record.get('targetstroom')   else '-'
        return (
            f"{bo_span} <span style='color: {io_color}; font-weight: bold; font-size: 25px;'>"
            f"{io_yield}%/{io_output}% + {io_target}µA</span>"
        )


# ---------------------------------------------------------------------------
# Week table row builder
# ---------------------------------------------------------------------------

def build_week_table_rows(ga, rb, in_, tl_12, tl_21, io,
                          with_onclick: bool = False) -> str:
    """Build ``<tr>`` rows for a week's production summary table."""
    if not any([ga, rb, in_, tl_12, tl_21, io]):
        return ''
    rows = ''
    n = max(len(ga), len(rb), len(in_), len(tl_12), len(tl_21), len(io))
    for i in range(n):
        ga_val   = fmt_targetstroom_cell(ga[i]    if i < len(ga)    else None, 'gallium',  'Gallium',  with_onclick)
        rb_val   = fmt_rb_cell          (rb[i]    if i < len(rb)    else None,                         with_onclick)
        in_val   = fmt_targetstroom_cell(in_[i]   if i < len(in_)   else None, 'indium',   'Indium',   with_onclick)
        tl12_val = fmt_targetstroom_cell(tl_12[i] if i < len(tl_12) else None, 'thallium', 'Thallium', with_onclick)
        tl21_val = fmt_targetstroom_cell(tl_21[i] if i < len(tl_21) else None, 'thallium', 'Thallium', with_onclick)
        io_val   = fmt_io_cell          (io[i]    if i < len(io)    else None,                         with_onclick)
        rows += (f'<tr><td>{ga_val}</td><td>{rb_val}</td><td>{in_val}</td>'
                 f'<td>{tl12_val}</td><td>{tl21_val}</td><td>{io_val}</td></tr>')
    return rows


# ---------------------------------------------------------------------------
# KPI table builder (efficiency / within-spec / OTIF)
# ---------------------------------------------------------------------------

def fmt_kpi_table(title: str, weeks: list, all_time_avg: float,
                  last_year_avg: float, last_3months_avg: float,
                  avg_label: str = 'All-time average',
                  subtitle: str = '') -> str:
    """Build a KPI table section (efficiency / within-spec / OTIF)."""
    headers = ''
    cells   = ''
    for w in weeks:
        headers += f"<th style='text-align: center;'>Week {w['week']}</th>"
        if w.get('no_data'):
            cells += "<td style='text-align: center; color: #aaa; font-weight: bold; font-size: 20px;'>--.-\u200c%</td>"
        else:
            cells += (f"<td style='text-align: center; color: {w['color']}; "
                      f"font-weight: bold; font-size: 20px;'>{w['percentage']:.1f}%</td>")

    year_color   = '#3BB143' if last_year_avg >= all_time_avg   else '#FF2400'
    m3_color     = '#3BB143' if last_3months_avg >= last_year_avg else '#FF2400'

    subtitle_html = (f"<p style='color: grey; font-size: 13px; margin-top: -8px; "
                     f"margin-bottom: 10px;'>{subtitle}</p>") if subtitle else ''

    return f"""
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">{title}</h2>
        {subtitle_html}
        <table>
            <thead><tr>{headers if headers else '<th>No data available</th>'}</tr></thead>
            <tbody><tr>{cells  if cells   else '<td>No data available</td>'}</tr></tbody>
        </table>
        <div style="text-align: center; margin-top: 10px; font-size: 16px;">
            <span style="color: black; font-weight: bold;">{avg_label}: {all_time_avg:.1f}%</span>
            <span style="color: {year_color}; font-weight: bold; margin-left: 20px;">Last year average: {last_year_avg:.1f}%</span>
            <span style="color: {m3_color}; font-weight: bold; margin-left: 20px;">Last 3 months average: {last_3months_avg:.1f}%</span>
        </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Ploeg HTML generators
# ---------------------------------------------------------------------------

def generate_ploegen_table_html(ploeg_6month: dict, ploeg_3month: dict,
                                 ploeg_monthly: dict, ploegen_data: dict) -> str:
    """Generate the Ploeg Performance table HTML."""
    def _avg(d):
        total    = sum(v['total']   for v in d.values())
        in_spec  = sum(v['in_spec'] for v in d.values())
        return (in_spec / total * 100) if total > 0 else 0

    m6_avg  = _avg(ploeg_6month)
    m3_avg  = _avg(ploeg_3month)
    mo_avg  = _avg(ploeg_monthly)

    html = """
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Ploeg Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Ploeg</th>
                    <th>6-Month Average</th>
                    <th>3-Month Average</th>
                    <th>Monthly Average</th>
                </tr>
            </thead>
            <tbody>
"""
    all_ploegen = sorted(set(list(ploeg_6month) + list(ploeg_3month) + list(ploeg_monthly)))
    for pn in all_ploegen:
        name = next((d['ploeg_name'] for d in ploegen_data.values()
                     if d.get('ploeg_number') == int(pn)), f"Ploeg {pn}")
        m6s  = ploeg_6month.get(pn,  {'total': 0, 'in_spec': 0})
        m3s  = ploeg_3month.get(pn,  {'total': 0, 'in_spec': 0})
        mos  = ploeg_monthly.get(pn, {'total': 0, 'in_spec': 0})
        m6p  = (m6s['in_spec'] / m6s['total'] * 100)  if m6s['total']  > 0 else 0
        m3p  = (m3s['in_spec'] / m3s['total'] * 100)  if m3s['total']  > 0 else 0
        mop  = (mos['in_spec'] / mos['total'] * 100)  if mos['total']  > 0 else 0
        html += (
            f"                <tr>"
            f"<td style='font-weight: bold;'>"
            f"<a href='#' onclick='showPloegDetails({pn}); return false;' "
            f"style='color: #662678; text-decoration: none; cursor: pointer;'>{name}</a></td>"
            f"<td style='color: {get_ploeg_color(m6p, m6_avg)}; font-weight: bold;'>{m6p:.1f}%</td>"
            f"<td style='color: {get_ploeg_color(m3p, m3_avg)}; font-weight: bold;'>{m3p:.1f}%</td>"
            f"<td style='color: {get_ploeg_color(mop, mo_avg)}; font-weight: bold;'>{mop:.1f}%</td>"
            f"</tr>\n"
        )
    html += (
        f"                <tr style='border-top: 2px solid #000;'>"
        f"<td style='font-weight: bold;'>Average</td>"
        f"<td style='font-weight: bold;'>{m6_avg:.1f}%</td>"
        f"<td style='font-weight: bold;'>{m3_avg:.1f}%</td>"
        f"<td style='font-weight: bold;'>{mo_avg:.1f}%</td>"
        f"</tr>\n"
        "            </tbody>\n        </table>\n    </div>\n"
    )
    return html


def generate_shift_tables_html(shift_stats_this_week, shift_stats_last_week,
                                this_week_friday, last_week_friday,
                                ploeg_6month, ploeg_3month, ploeg_monthly,
                                ploegen_data) -> str:
    """Generate HTML tables for shift analysis — only ploegen table."""
    if ploeg_6month or ploeg_3month or ploeg_monthly:
        return generate_ploegen_table_html(ploeg_6month, ploeg_3month, ploeg_monthly, ploegen_data)
    return ''


def generate_leaderboard_html(leaderboard: list) -> str:
    """Generate HTML for the ploeg performance leaderboard."""
    if not leaderboard:
        return ''
    trophies = {1: '🥇', 2: '🥈', 3: '🥉'}
    avg_pct  = sum(p['percentage'] for p in leaderboard) / len(leaderboard) if leaderboard else 0

    html = """
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
"""
    for idx, ploeg in enumerate(leaderboard, start=1):
        trophy = trophies.get(idx, '')
        color  = ('#3BB143' if ploeg['percentage'] > avg_pct + 2
                  else ('#FF2400' if ploeg['percentage'] < avg_pct - 2 else '#000000'))
        html += (
            f"                <tr>"
            f"<td style='text-align: center; font-size: 24px;'>{trophy if trophy else idx}</td>"
            f"<td style='text-align: left; font-weight: bold;'>"
            f"<a href='#' onclick='showPloegDetails({ploeg['ploeg_number']}); return false;' "
            f"style='color: #662678; text-decoration: none; cursor: pointer;'>{ploeg['name']}</a></td>"
            f"<td style='text-align: center;'>{ploeg['total']:.1f}</td>"
            f"<td style='text-align: center;'>{ploeg['in_spec']:.1f}</td>"
            f"<td style='text-align: center; color: {color}; font-weight: bold; font-size: 18px;'>"
            f"{ploeg['percentage']:.1f}%</td>"
            f"</tr>\n"
        )
    html += """            </tbody>
        </table>
        <div style="text-align: center; margin-top: 20px; font-size: 14px; color: #666; line-height: 1.6;">
            Producties worden proportioneel toegekend op basis van uren per ploeg.<br>
            Bron is bestralingendatabase &amp; P&amp;C
        </div>
    </div>
"""
    return html


def generate_monthly_winner_html(winner: dict) -> str:
    """Generate HTML for last month's winning ploeg."""
    if not winner:
        return ''
    return f"""
    <div class="section" style="text-align: center; background: linear-gradient(135deg, #662678 0%, #E40D7E 100%); padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; justify-content: center; gap: 30px; margin-bottom: 20px;">
            <span style="font-size: 84px; line-height: 1;">🏆</span>
            <h2 style="border-bottom: none; margin: 0; font-size: 42px; color: #FFFFFF;">{winner['month']} {winner['year']} Champion</h2>
            <span style="font-size: 84px; line-height: 1;">🏆</span>
        </div>
        <div style="font-size: 32px; font-weight: bold; color: #FFFFFF; margin: 20px 0;">{winner['name']}</div>
        <div style="font-size: 24px; color: #FFFFFF; margin: 10px 0;">
            Success Rate: <span style="font-weight: bold;">{winner['percentage']:.1f}%</span>
        </div>
        <div style="font-size: 18px; color: #FFD700; margin: 5px 0;">
            {winner['in_spec']:.1f} / {winner['total']:.1f} productions within spec
        </div>
    </div>
"""


def generate_ploeg_rolling_charts_html(ploeg_rolling: dict, ploegen_data: dict) -> str:
    """Generate HTML for ploeg 30-day rolling average charts."""
    if not ploeg_rolling:
        return ''
    html = """
    <div class="section">
        <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Ploeg Performance - 30-Day Rolling Average</h2>
"""
    for pn in sorted(ploeg_rolling):
        name = next((d['ploeg_name'] for d in ploegen_data.values()
                     if d.get('ploeg_number') == int(pn)), f"Ploeg {pn}")
        chart_id = f"ploegRollingChart{pn}"
        html += (
            f"        <div style='margin-bottom: 60px; page-break-inside: avoid;'>"
            f"<h3 style='color: #662678; margin-bottom: 20px; margin-top: 20px;'>{name}</h3>"
            f"<div style='position: relative; height: 400px; margin-bottom: 40px;'>"
            f"<canvas id='{chart_id}'></canvas></div></div>\n"
        )

    html += "    </div>\n    <script>\n"

    for pn in sorted(ploeg_rolling):
        data  = ploeg_rolling[pn]
        if not data:
            continue
        dates = [d['date'] for d in data]
        pcts  = [d['percentage'] for d in data]
        chart_id = f"ploegRollingChart{pn}"
        html += f"""
    new Chart(document.getElementById('{chart_id}').getContext('2d'), {{
        type: 'line',
        data: {{
            labels: {dates},
            datasets: [{{
                label: '30-Day Rolling Average (%)',
                data: {pcts},
                borderColor: '#662678',
                backgroundColor: 'rgba(102, 38, 120, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 5
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: true, position: 'top' }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{ return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%'; }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    type: 'time',
                    time: {{ unit: 'month', displayFormats: {{ month: 'MMM yyyy' }} }},
                    title: {{ display: true, text: 'Date' }}
                }},
                y: {{
                    beginAtZero: true, max: 100,
                    title: {{ display: true, text: 'Percentage In Spec (%)' }},
                    ticks: {{ callback: function(v) {{ return v + '%'; }} }}
                }}
            }}
        }}
    }});
"""
    html += "    </script>\n"
    return html
