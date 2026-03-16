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
from datetime import datetime

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

    generator = IsotopeDashboardGenerator(
        access_db_path             = paths.get("access_db"),
        sqlite_db_path             = paths.get("sqlite_db", "isotope_data.db"),
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
    if not generator.connect_sqlite():
        print("✗ Could not connect to SQLite database — aborting.")
        return False

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

    # ── Isotope data from bestralingen ────────────────────────────────────
    if not generator.extract_gallium_data():
        print("✗ Could not extract Gallium data — aborting.")
        return False
    generator.extract_gallium_opbrengsten_data()

    if not generator.extract_rubidium_data():
        print("✗ Could not extract Rubidium data — aborting.")
        return False

    if not generator.extract_indium_data():
        print("✗ Could not extract Indium data — aborting.")
        return False
    generator.extract_indium_opbrengsten_data()

    if not generator.extract_thallium_data():
        print("✗ Could not extract Thallium data — aborting.")
        return False

    if not generator.extract_iodine_data():
        print("✗ Could not extract Iodine data — aborting.")
        return False

    print("✓ Extracted all isotope records from bestralingen database")

    # ── Persist to SQLite ─────────────────────────────────────────────────
    generator.store_in_sqlite("gallium_data",  generator.gallium_data,  "opbrengst",       "theoretisch")
    generator.store_in_sqlite("rubidium_data", generator.rubidium_data, "activiteit_mbq",  "benodigde_mci")
    generator.store_in_sqlite("indium_data",   generator.indium_data,   "opbrengst",       "theoretisch")
    generator.store_in_sqlite("thallium_data", generator.thallium_data, "opbrengst",       "theoretisch")
    generator.store_in_sqlite("iodine_data",   generator.iodine_data,   "meting",          "verwacht")
    print("✓ Stored all records to SQLite")

    generator.close()
    return True


if __name__ == "__main__":
    main()
