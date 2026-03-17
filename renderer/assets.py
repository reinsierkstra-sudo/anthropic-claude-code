"""
renderer/assets.py
------------------
Module-level CSS and JavaScript constants extracted verbatim from the
monolithic gallium_extractor.py source.  All rendering modules import
from here so the raw strings live in exactly one place.
"""

# ============================================================================
# Gantt chart CSS — injected into every page that contains a timeline section.
# ============================================================================
_GANTT_CSS = """\
        <style>
        /* Gantt Chart Styles */
        .gantt-container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            position: relative;
        }

        .gantt-header {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ddd;
        }

        .gantt-jump-now {
            padding: 8px 20px;
            font-size: 14px;
            cursor: pointer;
            border: 2px solid #E40D7E;
            background-color: white;
            color: #E40D7E;
            border-radius: 5px;
            transition: all 0.3s;
            font-weight: bold;
        }

        .gantt-jump-now:hover {
            background-color: #E40D7E;
            color: white;
        }

        .gantt-jump-now.hidden {
            display: none;
        }

        .gantt-main {
            display: flex;
            position: relative;
        }

        .gantt-labels {
            width: 120px;
            flex-shrink: 0;
            z-index: 10;
            background: white;
        }

        .gantt-label-item {
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #662678, #E40D7E);
            color: white;
            font-weight: bold;
            font-size: 14px;
            border-bottom: 1px solid #ddd;
            padding: 0 10px;
        }

        .gantt-wrapper {
            overflow-x: auto;
            overflow-y: hidden;
            position: relative;
            border: 2px solid #ddd;
            border-radius: 5px;
            flex-grow: 1;
        }

        .gantt-chart {
            position: relative;
            min-height: 250px;
            background-color: #fafafa;
        }

        .gantt-time-header {
            position: sticky;
            top: 0;
            z-index: 50;
            background-color: #f5f5f5;
            border-bottom: 2px solid #333;
            display: flex;
            height: 60px;
        }

        .gantt-row-labels {
            position: sticky;
            left: 0;
            z-index: 60;
            background-color: #f5f5f5;
            flex-shrink: 0;
        }

        /* Old gantt-row-label - replaced by gantt-label-item
        .gantt-row-label {
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #662678, #E40D7E);
            color: white;
            font-weight: bold;
            font-size: 14px;
            border-bottom: 1px solid #ddd;
            padding: 0 10px;
            flex-shrink: 0;
            position: -webkit-sticky;
            position: sticky;
            left: 0;
            z-index: 70;
            align-self: flex-start;
        }
        */

        .gantt-time-label {
            position: absolute;
            bottom: 0;
            font-size: 11px;
            font-weight: bold;
            white-space: nowrap;
            padding: 2px 4px;
            transform: translateX(-50%);
        }

        .gantt-date-label {
            font-size: 11px;
            font-weight: bold;
            color: #333;
            white-space: nowrap;
        }

        .gantt-hour-label {
            font-size: 10px;
            font-weight: normal;
            color: #666;
            white-space: nowrap;
        }

        .gantt-timeline {
            position: relative;
        }

        .gantt-row {
            position: relative;
            height: 70px;
            border-bottom: 1px solid #ddd;
        }

        .gantt-grid-lines {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 1;
        }

        .gantt-grid-line {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 1px;
            background-color: #e0e0e0;
        }

        .gantt-block {
            position: absolute;
            top: 5px;
            height: 60px;
            border: 2px solid #333;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 12px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.2s;
            z-index: 10;
        }

        .gantt-block:hover {
            transform: translateY(-3px);
            z-index: 100;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }

        .gantt-block-label {
            color: #000;
            text-shadow: 1px 1px 2px rgba(255,255,255,0.8);
            padding: 0 5px;
        }

        .gantt-now-line {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 3px;
            background-color: #ff0000;
            z-index: 40;
            pointer-events: none;
        }

        .gantt-now-label {
            position: absolute;
            top: -25px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #ff0000;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            white-space: nowrap;
        }

        .gantt-tooltip {
            position: absolute;
            display: none;
            background-color: rgba(0,0,0,0.9);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 1000;
            pointer-events: none;
        }
        </style>
"""
