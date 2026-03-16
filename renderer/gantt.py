"""
renderer/gantt.py
-----------------
Standalone Gantt-chart HTML generator extracted from
IsotopeDashboardGenerator.generate_gantt_chart_html() and the
companion static helper _gantt_js_html() in gallium_extractor.py.

The only external dependency within this package is renderer.assets
for the CSS constant.
"""

import json

from renderer.assets import _GANTT_CSS


# ---------------------------------------------------------------------------
# Private helper — mirrors IsotopeDashboardGenerator._gantt_js_html()
# ---------------------------------------------------------------------------

def _gantt_js_html(cyclotron_json: str) -> str:
    """Return the <script> block that drives the Gantt timeline.

    *cyclotron_json* is the JSON-serialised list of production entries
    already prepared by the caller.
    """
    return f"""\
        <script>
        // Cyclotron data from server
        const scheduleData = {cyclotron_json};

        // Isotope colors - match both formats
        const isotopeColors = {{
            'TL201': '#FFDE21',
            'Tl-201': '#FFDE21',
            'GA067': '#0000ff',
            'Ga-067': '#0000ff',
            'Ga-68': '#0000ff',
            'IN111': '#00ffff',
            'In-111': '#00ffff',
            'RB081': '#FF0000',
            'Rb-081': '#FF0000',
            'Rb-82': '#FF0000',
            'I123': '#00FF00',
            'I-123': '#00FF00',
            'Pauze': '#CCCCCC'
        }};

        // Constants
        const GANTT_ROW_LABEL_WIDTH = 120;
        const GANTT_VIEWPORT_HOURS = 26;
        let ganttHourWidth = 40;
        let ganttMinTime = null;
        let ganttMaxTime = null;
        let ganttScrollPosition = null;

        function parseDateTime(dateStr, timeStr) {{
            if (!dateStr || !timeStr) return null;

            let day, month, year;

            // Handle YYYY-MM-DD format (from database)
            if (dateStr.includes('-') && dateStr.length === 10) {{
                const parts = dateStr.split('-');
                year = parseInt(parts[0]);
                month = parseInt(parts[1]);
                day = parseInt(parts[2]);
            }}
            // Handle dd.mm format (from cyclotron interface)
            else if (dateStr.includes('.')) {{
                const parts = dateStr.split('.');
                day = parseInt(parts[0]);
                month = parseInt(parts[1]);
                year = new Date().getFullYear();
            }}
            else {{
                return null;
            }}

            const [hours, minutes] = timeStr.split(':');
            return new Date(year, month - 1, day, parseInt(hours), parseInt(minutes || 0));
        }}

        function saveGanttScrollPosition(scrollLeft) {{
            ganttScrollPosition = scrollLeft;
        }}

        function loadGanttScrollPosition() {{
            ganttScrollPosition = null;
        }}

        function renderGanttChart() {{
            const chart = document.getElementById('ganttChart');
            const wrapper = document.getElementById('ganttWrapper');
            const now = new Date();

            wrapper.style.width = '100%';

            const containerWidth = wrapper.clientWidth - 40;
            const availableWidth = containerWidth;
            ganttHourWidth = availableWidth / GANTT_VIEWPORT_HOURS;

            let minTime = null;
            let maxTime = null;

            scheduleData.forEach(entry => {{
                if (entry.type === 'Data' || entry.type === 'Pauze') {{
                    if (entry.startDate && entry.startTime) {{
                        const start = parseDateTime(entry.startDate, entry.startTime);
                        if (start && (!minTime || start < minTime)) minTime = start;
                    }}
                    if (entry.endDate && entry.endTime) {{
                        const end = parseDateTime(entry.endDate, entry.endTime);
                        if (end && (!maxTime || end > maxTime)) maxTime = end;
                    }}
                }}
            }});

            if (!minTime || !maxTime) {{
                minTime = new Date(now.getTime() - 24 * 3600000);
                maxTime = new Date(now.getTime() + 48 * 3600000);
            }}

            minTime = new Date(minTime);
            minTime.setMinutes(0, 0, 0);
            maxTime = new Date(maxTime);
            maxTime.setMinutes(0, 0, 0);
            maxTime.setHours(maxTime.getHours() + 1);

            const totalHours = (maxTime - minTime) / 3600000;
            const totalWidth = totalHours * ganttHourWidth;

            ganttMinTime = minTime;
            ganttMaxTime = maxTime;

            chart.innerHTML = '';

            const timeHeader = document.createElement('div');
            timeHeader.className = 'gantt-time-header';
            timeHeader.style.width = totalWidth + 'px';

            const timelineDiv = document.createElement('div');
            timelineDiv.style.position = 'relative';
            timelineDiv.style.width = totalWidth + 'px';
            timelineDiv.style.height = '60px';

            let currentTime = new Date(minTime);
            let lastDate = '';

            while (currentTime <= maxTime) {{
                const hour = currentTime.getHours();
                const currentDate = currentTime.toISOString().split('T')[0];

                const hoursSinceStart = (currentTime - minTime) / 3600000;
                const xPos = hoursSinceStart * ganttHourWidth;

                if (currentDate !== lastDate) {{
                    const dateLabel = document.createElement('div');
                    dateLabel.className = 'gantt-date-label';
                    dateLabel.style.position = 'absolute';
                    dateLabel.style.left = xPos + 'px';
                    dateLabel.style.top = '2px';
                    dateLabel.style.transform = 'translateX(-50%)';
                    dateLabel.textContent = currentDate;
                    timelineDiv.appendChild(dateLabel);
                    lastDate = currentDate;
                }}

                const hourLabel = document.createElement('div');
                hourLabel.className = 'gantt-hour-label';
                hourLabel.style.position = 'absolute';
                hourLabel.style.left = xPos + 'px';
                hourLabel.style.bottom = '2px';
                hourLabel.style.transform = 'translateX(-50%)';
                hourLabel.textContent = String(hour).padStart(2, '0') + ':00';
                timelineDiv.appendChild(hourLabel);

                currentTime = new Date(currentTime.getTime() + 3600000);
            }}

            timeHeader.appendChild(timelineDiv);
            chart.appendChild(timeHeader);

            const cyclotrons = ['Kant 1', 'Kant 2', 'Philips'];
            const cyclotronMap = {{
                'P1': 'Kant 1',
                'P2': 'Kant 2',
                'P0': 'Philips',
                'IBA': 'Kant 1',  // Fallback for unmapped IBA
                'Philips': 'Philips'  // Direct mapping
            }};

            const labelsContainer = document.getElementById('ganttLabels');
            labelsContainer.innerHTML = '';

            // Add spacer for time header alignment
            const headerSpacer = document.createElement('div');
            headerSpacer.style.height = '60px';
            headerSpacer.style.borderBottom = '1px solid #ddd';
            labelsContainer.appendChild(headerSpacer);

            cyclotrons.forEach(cyclotronName => {{
                // Create fixed label
                const labelDiv = document.createElement('div');
                labelDiv.className = 'gantt-label-item';
                labelDiv.textContent = cyclotronName;
                labelsContainer.appendChild(labelDiv);

                // Create timeline row (without label)
                const row = document.createElement('div');
                row.style.position = 'relative';

                const timeline = document.createElement('div');
                timeline.className = 'gantt-timeline';
                timeline.style.width = totalWidth + 'px';

                const ganttRow = document.createElement('div');
                ganttRow.className = 'gantt-row';
                ganttRow.style.width = totalWidth + 'px';

                const gridLines = document.createElement('div');
                gridLines.className = 'gantt-grid-lines';

                let gridCurrentTime = new Date(minTime);
                while (gridCurrentTime <= maxTime) {{
                    const hoursSinceStart = (gridCurrentTime - minTime) / 3600000;
                    const gridLine = document.createElement('div');
                    gridLine.className = 'gantt-grid-line';
                    gridLine.style.left = (hoursSinceStart * ganttHourWidth) + 'px';
                    gridLines.appendChild(gridLine);
                    gridCurrentTime = new Date(gridCurrentTime.getTime() + 3600000);
                }}
                ganttRow.appendChild(gridLines);

                scheduleData.forEach(entry => {{
                    const mapped = cyclotronMap[entry.cyclotron];
                    if (mapped === cyclotronName && (entry.type === 'Data' || entry.type === 'Pauze')) {{
                        if (entry.startDate && entry.endDate && entry.startTime && entry.endTime) {{
                            const start = parseDateTime(entry.startDate, entry.startTime);
                            const end = parseDateTime(entry.endDate, entry.endTime);

                            if (start && end) {{
                                const startOffset = (start - minTime) / 3600000 * ganttHourWidth;
                                const width = (end - start) / 3600000 * ganttHourWidth;

                                if (width > 0) {{
                                    const block = document.createElement('div');
                                    block.className = 'gantt-block';
                                    block.style.left = startOffset + 'px';
                                    block.style.width = width + 'px';

                                    const color = isotopeColors[entry.product] || '#CCCCCC';
                                    block.style.backgroundColor = color;

                                    const labelText = entry.bonr || entry.product;
                                    block.innerHTML = `<span class="gantt-block-label">${{labelText}}</span>`;

                                    block.addEventListener('mouseenter', (e) => {{
                                        const tooltip = document.getElementById('ganttTooltip');
                                        tooltip.style.display = 'block';
                                        tooltip.innerHTML = `
                                            <strong>BOnr:</strong> ${{entry.bonr || 'N/A'}}<br>
                                            <strong>Product:</strong> ${{entry.product}}<br>
                                            <strong>Start:</strong> ${{entry.startDate}} ${{entry.startTime}}<br>
                                            <strong>End:</strong> ${{entry.endDate}} ${{entry.endTime}}<br>
                                            <strong>Duration:</strong> ${{entry.duration || 'N/A'}} hours
                                        `;
                                    }});

                                    block.addEventListener('mousemove', (e) => {{
                                        const tooltip = document.getElementById('ganttTooltip');
                                        tooltip.style.left = (e.pageX + 10) + 'px';
                                        tooltip.style.top = (e.pageY + 10) + 'px';
                                    }});

                                    block.addEventListener('mouseleave', () => {{
                                        const tooltip = document.getElementById('ganttTooltip');
                                        tooltip.style.display = 'none';
                                    }});

                                    ganttRow.appendChild(block);
                                }}
                            }}
                        }}
                    }}
                }});

                timeline.appendChild(ganttRow);
                row.appendChild(timeline);
                chart.appendChild(row);
            }});

            updateGanttNowLine(minTime, maxTime);

            wrapper.onscroll = null;
            wrapper.onscroll = () => {{
                saveGanttScrollPosition(wrapper.scrollLeft);
                updateJumpToNowButton(minTime);
            }};

            requestAnimationFrame(() => {{
                setTimeout(() => {{
                    if (ganttScrollPosition !== null && ganttScrollPosition !== undefined) {{
                        wrapper.scrollLeft = ganttScrollPosition;
                        updateJumpToNowButton(minTime);
                    }} else {{
                        centerOnNow(minTime);
                    }}
                }}, 50);
            }});
        }}

        function centerOnNow(minTime) {{
            const wrapper = document.getElementById('ganttWrapper');
            const now = new Date();

            const nowOffset = (now - minTime) / 3600000 * ganttHourWidth;
            const viewportWidth = wrapper.clientWidth;
            const centerOffset = viewportWidth / 2;

            wrapper.scrollLeft = nowOffset - centerOffset;
            saveGanttScrollPosition(wrapper.scrollLeft);
            updateJumpToNowButton(minTime);
        }}

        function updateGanttNowLine(minTime, maxTime) {{
            const chart = document.getElementById('ganttChart');
            const now = new Date();

            const min = minTime || ganttMinTime;
            const max = maxTime || ganttMaxTime;

            if (!min || !max) return;

            const oldLine = document.getElementById('ganttNowLine');
            if (oldLine) oldLine.remove();

            if (now < min || now > max) return;

            const offset = (now - min) / 3600000 * ganttHourWidth;

            const nowLine = document.createElement('div');
            nowLine.id = 'ganttNowLine';
            nowLine.className = 'gantt-now-line';
            nowLine.style.left = offset + 'px';

            const label = document.createElement('div');
            label.className = 'gantt-now-label';
            label.textContent = 'NOW';
            nowLine.appendChild(label);

            chart.appendChild(nowLine);
        }}

        function updateJumpToNowButton(minTime) {{
            const wrapper = document.getElementById('ganttWrapper');
            const button = document.getElementById('ganttJumpNow');
            const now = new Date();

            if (!minTime) return;

            const nowOffset = (now - minTime) / 3600000 * ganttHourWidth;
            const currentScroll = wrapper.scrollLeft;
            const viewportWidth = wrapper.clientWidth;
            const centerOffset = viewportWidth / 2;
            const idealScroll = nowOffset - centerOffset;

            if (Math.abs(currentScroll - idealScroll) > 100) {{
                button.classList.remove('hidden');
            }} else {{
                button.classList.add('hidden');
            }}
        }}

        function jumpToNow() {{
            if (!ganttMinTime) return;
            centerOnNow(ganttMinTime);
        }}

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            loadGanttScrollPosition();
            renderGanttChart();
        }});
        </script>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_gantt_chart_html(cyclotron_data: list) -> str:
    """Return the full Gantt-chart HTML block for the given *cyclotron_data*.

    *cyclotron_data* is the combined list of production-planning and
    historical bestralingen entries (each a dict with keys such as
    ``bonr``, ``product``, ``startDate``, ``startTime``, ``endDate``,
    ``endTime``, ``cyclotron``, ``duration``, ``type``).

    Returns an empty string when *cyclotron_data* is falsy.
    """
    if not cyclotron_data:
        return ""
    cyclotron_json = json.dumps(cyclotron_data)
    return (
        """\
        <!-- Gantt Chart Timeline Section -->
        <div class="section" id="gantt-section">
            <h2 style="border-bottom: 3px solid; border-image: linear-gradient(to right, #662678, #E40D7E) 1; padding-bottom: 10px;">Tijdlijn Producties</h2>
            <div class="gantt-container">
                <div class="gantt-header">
                    <button class="gantt-jump-now hidden" id="ganttJumpNow" onclick="jumpToNow()">
                        ⏱️ Jump to Now
                    </button>
                </div>
                <div class="gantt-main">
                    <div class="gantt-labels" id="ganttLabels">
                        <!-- Fixed labels column - populated by JavaScript -->
                    </div>
                    <div class="gantt-wrapper" id="ganttWrapper">
                        <div class="gantt-chart" id="ganttChart">
                            <!-- Scrollable timeline - populated by JavaScript -->
                        </div>
                    </div>
                </div>
            </div>
            <div class="gantt-tooltip" id="ganttTooltip"></div>
        </div>

            """
        + _GANTT_CSS
        + _gantt_js_html(cyclotron_json)
    )
