# Isotope Dashboard

Automated production dashboard for Cyclotron isotope productions (Ga-67, Rb-82, In-111, Tl-201, I-123).

Collects raw data from MS Access databases and Excel files, calculates KPIs, and generates HTML dashboards that are written to local and network locations.

---

## Project structure

```
isotope-dashboard/
│
├── config/
│   ├── settings.yaml          # All paths, thresholds, and settings — edit this for each machine
│   └── loader.py              # Loads settings.yaml and exposes it to the rest of the code
│
├── collector/                 # Reads from external sources, writes to data/raw.db
│   ├── access_reader.py       # MS Access databases (bestralingen, procesgegevens, storingen)
│   ├── excel_reader.py        # Excel files (ploegen, planning, VSM, OTIF) with SQLite cache
│   ├── http_reader.py         # Cyclotron planning page (HTTP)
│   ├── html_reader.py         # Local HTML files embedded in the dashboard
│   └── raw_db.py              # SQLite schema and read/write helpers for raw.db
│
├── calculator/                # Reads from data/raw.db, computes KPIs
│   ├── efficiency.py          # Production efficiency (mCi/µAh) per week
│   ├── within_spec.py         # % productions within quality spec per week
│   ├── otif.py                # OTIF gedraaide producties per week
│   ├── shift_stats.py         # Shift statistics and production history
│   ├── leaderboard.py         # Ploeg leaderboard and rolling averages
│   └── issues.py              # Issue counts from production_comments table
│
├── renderer/                  # Reads calculated data, generates HTML
│   ├── assets.py              # CSS and JS constants used in the dashboards
│   ├── file_protection.py     # SHA256 hashing and read-only file protection
│   ├── gantt.py               # Gantt chart HTML generation
│   ├── tables.py              # Reusable table builders (efficiency, within-spec, OTIF, etc.)
│   ├── dashboard_full.py      # Full dashboard renderer
│   └── dashboard_truncated.py # Truncated dashboard renderer (summary only)
│
├── data/
│   ├── raw.db                 # Raw isotope data as collected from sources (auto-created)
│   └── derived.db             # (reserved for future use)
│
├── output/                    # Generated HTML files land here locally
│
├── run_collector.py           # Entry point: collect data only
├── run_calculator.py          # Entry point: calculate KPIs only
├── run_renderer.py            # Entry point: render dashboards only
├── run_all.py                 # Entry point: full pipeline loop
└── requirements.txt
```

---

## Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Configure paths

Open `config/settings.yaml` and update all paths under the `paths:` section to match the machine you are deploying on. Every file path the application needs is in that one file — no Python code needs to be touched.

```yaml
paths:
  bestralingen_db: '\\SERVER\Share\...\bestralingen.mdb'
  proces_db:       'W:\Maximo\ProcesGegevens.accdb'
  # ... etc.
```

### 3. Run

**Full pipeline (normal operation):**
```
python run_all.py
```
Runs collect → calculate → render in a loop, sleeping 60 seconds between iterations.

**Run individual stages:**
```
python run_collector.py    # collect raw data only
python run_calculator.py   # recalculate KPIs from existing raw.db
python run_renderer.py     # regenerate dashboards from existing data
```
This is useful during development: you can re-render the dashboard without waiting for a full data collection cycle.

---

## How it works

```
MS Access DBs  ─┐
Excel files    ─┼─▶  collector/  ─▶  data/raw.db  ─▶  calculator/  ─▶  renderer/  ─▶  HTML files
HTTP endpoint  ─┘
```

1. **Collector** reads from all external sources and appends new records to `data/raw.db`. Raw data is never recalculated — it is the source of truth.
2. **Calculator** reads `raw.db` and computes all KPIs (efficiency, within-spec %, OTIF, shift stats, leaderboard).
3. **Renderer** takes the calculated values and produces two HTML files: a full dashboard and a truncated summary. Both are written to the paths defined in `settings.yaml`.

---

## Adding a new machine / server

1. Clone the repository.
2. Install dependencies (`pip install -r requirements.txt`).
3. Edit `config/settings.yaml` — update all paths to the correct locations on the new machine.
4. Run `python run_all.py`.

No other changes are needed.

---

## Multiple people working on the project

Each layer is independent:

| You want to… | Edit files in… |
|---|---|
| Change what data is collected or fix a query | `collector/` |
| Change how a KPI is calculated | `calculator/` |
| Change the dashboard layout or colours | `renderer/` |
| Change a threshold or file path | `config/settings.yaml` |

Changes to one layer do not require touching the others.
