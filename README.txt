Isotope Dashboard
=================

Automated production dashboard for Cyclotron isotope productions:
Ga-67 (Gallium), Rb-82 (Rubidium), In-111 (Indium), Tl-201 (Thallium), I-123 (Iodine).

Every 60 seconds the application collects raw data from MS Access databases, Excel
files and an HTTP endpoint, calculates KPIs, and writes HTML dashboards to one or
more output locations (local folder, network share, bureau screen).

-------------------------------------------------------------------------------

Contents
--------
  1. What it does
  2. Project structure
  3. Requirements
  4. Setup
  5. Running the application
  6. Data sources
  7. KPIs explained
  8. Dashboard output
  9. Configuration reference (settings.yaml)
 10. Database reference
 11. Adding a new machine / server
 12. Multiple people working on the project
 13. Troubleshooting

-------------------------------------------------------------------------------

1. What it does
---------------

The application runs a continuous loop:

    collect --> calculate --> render --> sleep 60s --> repeat

  - Collect:   reads new production records from Access databases and Excel files,
               stores them in data/raw.db (SQLite).
  - Calculate: reads raw.db, computes all KPIs, stores results in data/derived.db.
  - Render:    reads derived.db, generates two HTML files (full and truncated) and
               copies them to all configured output destinations.

The full dashboard contains:

  * Efficiency, Within-spec, and OTIF KPI tables (last 10 weeks + averages)
  * Current and previous week production tables per isotope
  * Monthly trend charts per isotope (12 months)
  * Per-isotope production efficiency (mCi/uAh)
  * Shift (ploeg) leaderboard and rolling performance charts
  * Issue / operator comment counts
  * Gantt chart of production timeline
  * Embedded planning and production schema modals

The truncated dashboard is a lightweight version with only the KPI summary,
current/previous week tables, and shift statistics -- suitable for a bureau screen.

-------------------------------------------------------------------------------

2. Project structure
--------------------

    isotope-dashboard/
    |
    +-- config/
    |   +-- settings.yaml          # All paths, thresholds, and settings
    |   +-- loader.py              # Reads settings.yaml; used by all other modules
    |
    +-- collector/                 # Reads external sources, writes to data/raw.db
    |   +-- access_reader.py       # MS Access: bestralingen, procesgegevens, storingen
    |   +-- excel_reader.py        # Excel: ploegen, planning, VSM, OTIF
    |   +-- http_reader.py         # HTTP/JSON: cyclotron production database
    |   +-- html_reader.py         # Static HTML files embedded in the dashboard
    |   +-- raw_db.py              # SQLite schema + read/write helpers for raw.db
    |   +-- derived_db.py          # SQLite schema + read/write helpers for derived.db
    |
    +-- calculator/                # Reads raw.db, computes KPIs
    |   +-- efficiency.py          # Cyclotron efficiency % (ProcesGegevens targets) +
    |   |                          #   per-isotope production efficiency (mCi/uAh)
    |   +-- within_spec.py         # % productions within quality spec per week
    |   +-- otif.py                # OTIF: actual vs nominal targetstroom per week
    |   +-- shift_stats.py         # Per-shift (ploeg) in-spec statistics
    |   +-- leaderboard.py         # Ploeg leaderboard and 6-month rolling averages
    |   +-- issues.py              # Operator comment / issue counts
    |   +-- isotope_data.py        # Shared helpers: weekly slices, monthly averages
    |
    +-- renderer/                  # Reads derived.db, generates HTML
    |   +-- assets.py              # Shared CSS and JavaScript constants
    |   +-- file_protection.py     # SHA256 hash-based read-only file protection
    |   +-- gantt.py               # Gantt chart HTML builder
    |   +-- tables.py              # Reusable HTML table builders (KPI, production, etc.)
    |   +-- dashboard_full.py      # Full dashboard renderer
    |   +-- dashboard_truncated.py # Truncated dashboard renderer
    |
    +-- data/                      # Auto-created on first run
    |   +-- raw.db                 # Raw records as collected (append-only, source of truth)
    |   +-- derived.db             # Calculated KPIs (overwritten every cycle)
    |
    +-- output/                    # Generated HTML files (local copy)
    |
    +-- run_collector.py           # Entry point: collect only
    +-- run_calculator.py          # Entry point: calculate only
    +-- run_renderer.py            # Entry point: render only
    +-- run_all.py                 # Entry point: full pipeline loop
    +-- requirements.txt

-------------------------------------------------------------------------------

3. Requirements
---------------

Python 3.9 or higher.

External packages (installed via pip, see requirements.txt):

    pyodbc>=4.0          MS Access / ODBC database connectivity
    requests>=2.28       HTTP requests (cyclotron planning page)
    beautifulsoup4>=4.11 HTML parsing (fallback cyclotron page scraper)
    lxml>=4.9            Fast HTML parser used by BeautifulSoup
    openpyxl>=3.0        Excel file reading (.xlsx / .xlsm)
    pyyaml>=6.0          YAML configuration file parsing

The machine must also have an ODBC driver for MS Access installed.
On Windows this is typically "Microsoft Access Driver (*.mdb, *.accdb)"
and comes with a standard Office installation or the free Access Database Engine
redistributable from Microsoft.

Install all dependencies:

    pip install -r requirements.txt

-------------------------------------------------------------------------------

4. Setup
--------

Step 1 -- Install dependencies (see section 3 above).

Step 2 -- Configure paths.

Open config/settings.yaml and update the paths: section to match the paths on
the machine you are deploying on. Every file path the application needs is in
that one file. See section 9 (Configuration reference) for a full description
of every key.

Minimum paths to update:

    paths:
      raw_db:               data/raw.db               # can leave as-is
      derived_db:           data/derived.db            # can leave as-is
      bestralingen_db:      \\SERVER\Share\bestralingen.mdb
      proces_db:            W:\Maximo\ProcesGegevens.accdb
      storingen_iba_db:     \\SERVER\Share\Storingen_IBA.accdb
      storingen_philips_db: \\SERVER\Share\Storingen_Philips.accdb
      ploegen_excel:        \\SERVER\Share\Ploegen.xlsx
      planning_excel:       \\SERVER\Share\Planning & Control Cyclotron.xlsm
      vsm_excel:            \\SERVER\Share\Targetstroom daily management VSM cyclotron.xlsx
      output_local:         output\dashboard.html
      output_network:       \\SERVER\Share\dashboard.html

Step 3 -- Run (see section 5).

-------------------------------------------------------------------------------

5. Running the application
--------------------------

Full pipeline -- normal operation:

    python run_all.py

Starts an infinite loop: collect -> calculate -> render, sleeping 60 seconds
(configurable via loop_interval_seconds in settings.yaml) between iterations.
Stop with Ctrl+C.

Run individual stages (useful during development or debugging):

    python run_collector.py    # read external sources, update raw.db only
    python run_calculator.py   # recompute all KPIs from existing raw.db
    python run_renderer.py     # regenerate HTML from existing derived.db

Typical development workflow:

    1. Collect once:      python run_collector.py
    2. Tweak calculator:  edit calculator/*.py
    3. Recalculate:       python run_calculator.py
    4. Re-render:         python run_renderer.py
    -- repeat 2-4 until satisfied, without waiting for new data each time.

-------------------------------------------------------------------------------

6. Data sources
---------------

The application reads from five types of source:

6a. MS Access databases (collector/access_reader.py)

    bestralingen.mdb
        The main production database. Contains one record per production run
        for each isotope (date, cyclotron, beam current, duration, activity, etc.).

    ProcesGegevens.accdb
        Process data. Contains efficiency targets (Output_EfficiencyTargets table)
        and yield/opbrengst data (gallium and indium).

    Storingen_IBA.accdb
        Downtime records for the IBA cyclotron.

    Storingen_Philips.accdb
        Downtime records for the Philips cyclotron.

    All Access databases are read via pyodbc using the MS Access ODBC driver.
    The collector fetches only new or recently edited records on each cycle
    (incremental import) to avoid re-processing the full history every minute.

6b. Excel files (collector/excel_reader.py)

    Ploegen.xlsx
        Shift team definitions: team names, codes, and member lists.

    Planning & Control Cyclotron.xlsm
        Daily shift planning: which team leads each shift on each day.
        Used to assign individual production runs to a ploeg for leaderboard scoring.

    Targetstroom daily management VSM cyclotron.xlsx
        VSM (value stream management) daily target beam currents.

    Excel files are parsed with openpyxl and cached in raw.db (excel_cache table).
    On each cycle the file modification time is checked; if unchanged the cached
    version is used instead of re-parsing the file.

6c. HTTP / JSON (collector/http_reader.py)

    Primary source:
        \\pett-fs01p\nucleair\...\productions_database.json
        A JSON file written by the cyclotron control system.

    Fallback source:
        http://pett-webw02p/procdashboard/cyclotron.asp
        A live ASP page showing the current production schedule, scraped with
        BeautifulSoup when the JSON file is not available.

6d. Static HTML files (collector/html_reader.py)

    planning.html and productieschema.html are local HTML files that are
    embedded as modal dialogs in the dashboard (planning overview and
    production schema). Their paths are configured in settings.yaml.

6e. Automatic deduplication

    Every record written to raw.db is upserted (INSERT OR REPLACE) on a
    composite natural key (date + identifier + isotope type). Re-running
    the collector never creates duplicate records.

-------------------------------------------------------------------------------

7. KPIs explained
-----------------

7a. Efficiency (%)

    Source: efficiency_targets table (from ProcesGegevens Output_EfficiencyTargets).
    Formula: (actual_mbq / target_mbq) * 100
    The values in the source table are decimal fractions (e.g. 0.25 = 25%).
    Thresholds: configured per isotope in spec_settings in settings.yaml.
    Displayed: last 10 weeks, 1-year average, 3-month average, all-time quarterly.

7b. Within-spec (%)

    Percentage of production runs where the beam current (targetstroom) fell
    within the configured min/max range for that isotope and cyclotron.
    Thresholds (examples from settings.yaml):
        Gallium  -- Philips: 75-85 uA, IBA: 130-140 uA
        Thallium -- 166-174 uA
        Iodine   -- targetstroom: 96-124 uA AND output: 78-114.9%
    Displayed: last 10 weeks, 1-year average, 3-month average, all-time quarterly.

7c. OTIF -- gedraaide producties (%)

    On Time In Full for actual beam current vs the nominal (planned) value.
    A production scores as "in" if targetstroom / nominal_targetstroom >= the
    configured OTIF threshold (default 97%).
    Displayed: last 10 weeks, 1-year average, 3-month average.

7d. Production efficiency (mCi/uAh)

    Per-isotope yield: how much activity (mCi) was produced per unit of beam
    charge (micro-ampere-hour). Calculated separately for Ga-67, In-111, Rb-82,
    and I-123. Rb-82 uses only runs between 3 and 6 beam-hours; I-123 uses only
    runs >= 10 beam-hours, to exclude outlier short runs.

7e. Shift / ploeg leaderboard

    Each production run is assigned to the ploeg (shift team) that was on duty
    at the time, using the Planning & Control Excel file. The leaderboard ranks
    teams by their within-spec percentage over the past 30 days.
    Rolling 30-day averages are tracked for the past 6 months per team.

7f. Issues / operator comments

    Operators can log comments (issues) against individual production runs.
    The dashboard shows comment counts by type for this week, last week, and
    all time, broken down by isotope.

-------------------------------------------------------------------------------

8. Dashboard output
-------------------

Two HTML files are generated each cycle:

    Full dashboard   -- all sections (KPI tables, production detail, charts,
                        leaderboard, Gantt, planning modals).
    Truncated dashboard -- KPI summary + current/previous week tables +
                        shift statistics only; intended for a bureau screen.

Each file is written to all destinations configured under paths: in settings.yaml
(local output folder, network share, bureau screen share, etc.). The renderer uses
SHA256 hashing to skip writing files that have not changed, reducing unnecessary
network I/O.

-------------------------------------------------------------------------------

9. Configuration reference (settings.yaml)
-------------------------------------------

All configuration lives in config/settings.yaml. No Python code needs editing
when deploying to a new machine or adjusting thresholds.

paths:
    raw_db               Path to the raw SQLite database (auto-created).
    derived_db           Path to the derived SQLite database (auto-created).
    bestralingen_db      UNC/local path to bestralingen.mdb (MS Access).
    proces_db            UNC/local path to ProcesGegevens.accdb (MS Access).
    storingen_iba_db     UNC/local path to Storingen_IBA.accdb (MS Access).
    storingen_philips_db UNC/local path to Storingen_Philips.accdb (MS Access).
    ploegen_excel        Path to Ploegen.xlsx.
    planning_excel       Path to Planning & Control Cyclotron.xlsm.
    vsm_excel            Path to the VSM targetstroom Excel file.
    planning_html        Path to planning.html (embedded modal).
    productieschema_html Path to productieschema.html (embedded modal).
    output_local         Output path for the full dashboard HTML (local).
    output_network       Output path for the full dashboard HTML (network share).
    output_bureau        Output path for the truncated dashboard HTML.
    (additional output destinations can be added as needed)

loop_interval_seconds:
    How many seconds to sleep between pipeline cycles. Default: 60.

spec_settings:
    Per-isotope quality thresholds. Example:
        gallium:
          philips:
            min_targetstroom: 75
            max_targetstroom: 85
          iba:
            min_targetstroom: 130
            max_targetstroom: 140
    Thresholds are used by the within-spec and OTIF calculators.
    Change these when production specifications change -- no code edits needed.

otif_threshold:
    Minimum targetstroom ratio (0-100) for a production to count as "in" for OTIF.
    Default: 97.

-------------------------------------------------------------------------------

10. Database reference
----------------------

data/raw.db -- source of truth, never recalculated.

    gallium_data       One row per Ga-67 production run.
    rubidium_data      One row per Rb-82 production run.
    indium_data        One row per In-111 production run.
    thallium_data      One row per Tl-201 production run.
    iodine_data        One row per I-123 production run.
    gallium_opbrengsten   Daily Ga-67 yield totals (MBq).
    indium_opbrengsten    Daily In-111 yield totals (MBq).
    efficiency_targets    Daily efficiency targets from ProcesGegevens.
    iba_storingen         IBA cyclotron downtime records.
    philips_storingen     Philips cyclotron downtime records.
    production_comments   Operator comments per production batch.
    excel_cache           Cached parsed Excel file data (keyed by filename).
    blobs                 JSON key-value store for other data (OTIF, VSM, planning).

data/derived.db -- recalculated every cycle, safe to delete.

    kpis    Key-value store. Each row: key (TEXT), value (JSON TEXT), computed_at.
            All calculated metrics are stored here as JSON-serialised values.
            Because it is a key-value store, new KPIs can be added without any
            schema migration.

-------------------------------------------------------------------------------

11. Adding a new machine / server
----------------------------------

1. Clone the repository.
2. Install dependencies:  pip install -r requirements.txt
3. Install MS Access ODBC driver if not already present.
4. Copy config/settings.yaml from an existing machine and update all paths
   under paths: to the correct locations on the new machine.
5. Run:  python run_all.py

No other changes are needed. The data/ folder and databases are created
automatically on first run.

-------------------------------------------------------------------------------

12. Multiple people working on the project
-------------------------------------------

Each layer is independent. Changes to one layer do not require touching the others.

    You want to...                                    Edit files in...
    -----------------------------------------------------------------------
    Change what data is collected or fix a query      collector/
    Change how a KPI is calculated                    calculator/
    Change the dashboard layout or colours            renderer/
    Change a threshold, path, or file location        config/settings.yaml

Typical examples:

    "The Gallium within-spec range has changed from 75-85 to 78-88 uA"
    --> Edit spec_settings in config/settings.yaml only.

    "We need to add a new KPI: average beam duration per isotope"
    --> Add a function in the relevant calculator/*.py file.
    --> Store the result in derived.db via run_calculator.py.
    --> Add a table/section in the relevant renderer/*.py file.
    --> No changes to collector/ or config/ needed.

    "The column name in bestralingen.mdb has changed"
    --> Edit the relevant extract_*() function in collector/access_reader.py only.

-------------------------------------------------------------------------------

13. Troubleshooting
-------------------

Dashboard shows no data / empty tables
    - Check that config/settings.yaml paths are correct and accessible.
    - Run python run_collector.py and check the console output for errors.
    - Verify the MS Access ODBC driver is installed (see section 3).
    - Check that raw.db is being created in the data/ folder.

"pyodbc.Error: ('IM002', ...)" -- ODBC driver not found
    - Install "Microsoft Access Database Engine 2016 Redistributable" from Microsoft.
    - Make sure you install the same bitness (32 or 64-bit) as your Python installation.

Dashboard shows stale data
    - Check that run_all.py is still running (it may have crashed).
    - Run python run_collector.py manually to verify data collection works.
    - Check network access to the UNC paths in settings.yaml.

"KeyError" in calculator or renderer
    - A KPI key expected in derived.db is missing; this usually means
      run_calculator.py failed on a previous cycle.
    - Run python run_calculator.py manually and read the error output.

To recompute everything from scratch:
    - Delete data/derived.db (safe -- it is fully regenerated each cycle).
    - Run python run_calculator.py, then python run_renderer.py.

To recollect all historical data:
    - Delete data/raw.db (this will trigger a full re-import on next collect cycle).
    - Run python run_collector.py. This may take longer than usual on first run.
