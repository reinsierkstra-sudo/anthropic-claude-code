"""
run_collector.py
----------------
Entry point that runs **data collection only** and stores raw records to
the SQLite database (raw.db / isotope_data.db).

This is phase 1 of the refactored pipeline:
  run_collector  →  run_calculator  →  run_renderer

Usage::

    python run_collector.py

The script mirrors the database-connection and data-extraction logic from
``IsotopeDashboardGenerator.run()`` in gallium_extractor.py, reporting
success (✓) or warnings (⚠) for each data source.
"""

import traceback
from datetime import date, datetime, timedelta

from config.loader import load_settings


def main() -> bool:
    """Connect to all data sources, extract records, and persist to raw DB.

    Returns ``True`` on success, ``False`` if the primary Access database
    cannot be reached.
    """
    cfg = load_settings()
    paths = cfg.get("paths", {})

    # Import here so the module can be loaded without pyodbc installed
    from gallium_extractor import IsotopeDashboardGenerator
    from collector import access_reader
    from collector.raw_db import connect as raw_connect, get_max_date, store as raw_store

    raw_db_path = paths.get("raw_db", "data/raw.db")
    lookback_days = cfg.get("collection_lookback_days", 30)

    generator = IsotopeDashboardGenerator(
        access_db_path             = paths.get("access_db"),
        sqlite_db_path             = raw_db_path,
        proces_db_path             = paths.get("proces_db"),
        storingen_db_path          = paths.get("storingen_db"),
        philips_storingen_db_path  = paths.get("philips_storingen_db"),
        ploegen_excel_path         = paths.get("ploegen_excel"),
        planning_excel_path        = paths.get("planning_excel"),
        vsm_excel_path             = paths.get("vsm_excel"),
        planning_html_path         = paths.get("planning_html"),
        productieschema_html_path  = paths.get("productieschema_html"),
    )

    print("=" * 60)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] run_collector — data collection")
    print("=" * 60)

    # ── Primary bestralingen database ─────────────────────────────────────
    if not generator.connect_access():
        print("✗ Could not connect to Access database — aborting.")
        return False
    print("✓ Connected to bestralingen (Access) database")

    # ── ProcesGegevens (efficiency data) ──────────────────────────────────
    if not generator.connect_proces_db():
        print("⚠ Could not connect to ProcesGegevens — efficiency data skipped")
    else:
        if generator.extract_efficiency_data():
            print("✓ Extracted efficiency data")
        else:
            print("⚠ Could not extract efficiency data")

    # ── IBA storingen ─────────────────────────────────────────────────────
    if not generator.connect_storingen_db():
        print("⚠ Could not connect to Storingen IBA database")
    else:
        if generator.extract_iba_storingen_data():
            print("✓ Extracted IBA storingen data")
        else:
            print("⚠ Could not extract IBA storingen data")

    # ── Philips storingen ─────────────────────────────────────────────────
    if not generator.connect_philips_storingen_db():
        print("⚠ Could not connect to Storingen Philips database")
    else:
        if generator.extract_philips_storingen_data():
            print("✓ Extracted Philips storingen data")
        else:
            print("⚠ Could not extract Philips storingen data")

    # ── SQLite (must connect before Excel loaders so mtime cache works) ───
    raw_conn = raw_connect(raw_db_path)
    if not generator.connect_sqlite():
        print("✗ Could not connect to SQLite database — aborting.")
        return False

    # Determine incremental since-dates per table.
    # On first run max_date is None → full extraction.
    # On subsequent runs extract from (max_date - lookback_days) to catch edits.
    def _since(table: str):
        max_str = get_max_date(raw_conn, table)
        if max_str:
            return date.fromisoformat(max_str) - timedelta(days=lookback_days)
        return None  # full extraction

    # ── OTIF Excel ────────────────────────────────────────────────────────
    try:
        generator.load_otif_data()
        print("✓ Loaded OTIF Excel data")
    except Exception as e:
        print(f"⚠ Could not load OTIF data: {e}")
        generator.otif_kpi_data = []
        generator.otif_table_data = {}

    # ── VSM Excel ─────────────────────────────────────────────────────────
    try:
        generator.load_vsm_data()
        print("✓ Loaded VSM Excel data")
    except Exception as e:
        print(f"⚠ Could not load VSM data: {e}")
        generator.vsm_data = []

    # ── Planning HTML ─────────────────────────────────────────────────────
    try:
        generator.load_planning_html()
        print("✓ Loaded planning.html")
    except Exception as e:
        print(f"⚠ Could not load planning.html: {e}")
        generator.planning_html_content = None

    # ── Productieschema HTML ──────────────────────────────────────────────
    try:
        generator.load_productieschema_html()
        print("✓ Loaded productieschema HTML")
    except Exception as e:
        print(f"⚠ Could not load productieschema HTML: {e}")
        generator.productieschema_html_content = None

    # ── Isotope data from bestralingen (incremental) ──────────────────────
    # Open a second read-only Access connection for the standalone extractors
    # so we can pass since_date without touching the generator's internals.
    access_conn = access_reader.connect_access(paths.get("access_db", ""))
    if access_conn is None:
        print("✗ Could not open Access connection for isotope extraction — aborting.")
        return False

    isotopes = [
        ("gallium_data",  access_reader.extract_gallium_data,  "EOB datum"),
        ("rubidium_data", access_reader.extract_rubidium_data, "EOB datum"),
        ("indium_data",   access_reader.extract_indium_data,   "EOB datum"),
        ("thallium_data", access_reader.extract_thallium_data, "EOB datum"),
        ("iodine_data",   access_reader.extract_iodine_data,   "BO ingroei tot datum"),
    ]

    for table, extractor, _date_col in isotopes:
        since = _since(table)
        label = f"since {since}" if since else "full extraction"
        try:
            records = extractor(access_conn, since_date=since)
            raw_store(raw_conn, table, records)
            print(f"✓ {table}: {len(records)} records ({label})")
        except Exception as e:
            print(f"✗ {table}: extraction failed — {e}")
            traceback.print_exc()
            return False

    # Opbrengsten data (not persisted to raw.db, used only during calculation)
    generator.extract_gallium_opbrengsten_data()
    generator.extract_indium_opbrengsten_data()

    access_conn.close()
    raw_conn.close()
    print("✓ All isotope records stored to raw.db")

    generator.close()
    return True


if __name__ == "__main__":
    main()
