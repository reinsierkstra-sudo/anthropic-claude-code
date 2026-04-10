"""
run_collector.py
----------------
Entry point that runs **data collection only** and stores raw records to
the SQLite database (raw.db / isotope_data.db).

This is phase 1 of the refactored pipeline:
  run_collector  →  run_calculator  →  run_renderer

Usage::

    python run_collector.py

The script uses the standalone collector/* modules.
No dependency on gallium_extractor.IsotopeDashboardGenerator.
"""

import traceback
from datetime import datetime

from config.loader import load_settings


def main() -> bool:
    """Connect to all data sources, extract records, and persist to raw DB.

    Returns ``True`` on success, ``False`` if the primary Access database
    cannot be reached.
    """
    cfg   = load_settings()
    paths = cfg.get("paths", {})

    from collector import access_reader
    from collector import raw_db
    from collector import excel_reader
    from collector import html_reader

    raw_db_path = paths.get("raw_db", "data/raw.db")

    print("=" * 60)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] run_collector — data collection")
    print("=" * 60)

    # ── SQLite connection (must be open before Excel loaders) ────────────────
    raw_conn = raw_db.connect(raw_db_path)
    print(f"✓ SQLite database: {raw_db_path}")

    # ── Primary bestralingen database ─────────────────────────────────────
    access_conn = access_reader.connect_access(paths.get("bestralingen_db", ""))
    if access_conn is None:
        print("✗ Could not connect to bestralingen Access database — aborting.")
        raw_conn.close()
        return False
    print("✓ Connected to bestralingen (Access) database")

    # ── Isotope records ────────────────────────────────────────────────────
    isotopes = [
        ("gallium_data",  access_reader.extract_gallium_data),
        ("rubidium_data", access_reader.extract_rubidium_data),
        ("indium_data",   access_reader.extract_indium_data),
        ("thallium_data", access_reader.extract_thallium_data),
        ("iodine_data",   access_reader.extract_iodine_data),
    ]

    for table, extractor in isotopes:
        try:
            records = extractor(access_conn)
            raw_db.store(raw_conn, table, records)
            print(f"✓ {table}: {len(records)} records stored")
        except Exception as e:
            print(f"✗ {table}: extraction failed — {e}")
            traceback.print_exc()
            access_conn.close()
            raw_conn.close()
            return False

    # ── Opbrengsten ────────────────────────────────────────────────────────
    try:
        ga_opb = access_reader.extract_gallium_opbrengsten_data(access_conn)
        raw_db.store_opbrengsten(raw_conn, 'gallium_opbrengsten', ga_opb)
        print(f"✓ gallium_opbrengsten: {len(ga_opb)} records stored")
    except Exception as e:
        print(f"⚠ Could not extract gallium opbrengsten: {e}")

    try:
        in_opb = access_reader.extract_indium_opbrengsten_data(access_conn)
        raw_db.store_opbrengsten(raw_conn, 'indium_opbrengsten', in_opb)
        print(f"✓ indium_opbrengsten: {len(in_opb)} records stored")
    except Exception as e:
        print(f"⚠ Could not extract indium opbrengsten: {e}")

    access_conn.close()

    # ── ProcesGegevens (efficiency targets) ────────────────────────────────
    proces_path = paths.get("proces_db", "")
    if proces_path:
        proces_conn = access_reader.connect_proces_db(proces_path)
        if proces_conn:
            try:
                eff_data = access_reader.extract_efficiency_data(proces_conn)
                raw_db.store_opbrengsten(raw_conn, 'efficiency_targets', eff_data)
                print(f"✓ efficiency_targets: {len(eff_data)} records stored")
            except Exception as e:
                print(f"⚠ Could not extract efficiency data: {e}")
            finally:
                proces_conn.close()
        else:
            print("⚠ Could not connect to ProcesGegevens — efficiency data skipped")

    # ── IBA storingen ─────────────────────────────────────────────────────
    stor_iba_path = paths.get("storingen_iba_db", "")
    if stor_iba_path:
        iba_conn = access_reader.connect_storingen_iba(stor_iba_path)
        if iba_conn:
            try:
                iba_data = access_reader.extract_iba_storingen_data(iba_conn)
                raw_db.store_storingen(raw_conn, 'iba_storingen', iba_data)
                print(f"✓ iba_storingen: {len(iba_data)} records stored")
            except Exception as e:
                print(f"⚠ Could not extract IBA storingen: {e}")
            finally:
                iba_conn.close()
        else:
            print("⚠ Could not connect to Storingen IBA database")

    # ── Philips storingen ─────────────────────────────────────────────────
    stor_ph_path = paths.get("storingen_philips_db", "")
    if stor_ph_path:
        ph_conn = access_reader.connect_storingen_philips(stor_ph_path)
        if ph_conn:
            try:
                ph_data = access_reader.extract_philips_storingen_data(ph_conn)
                raw_db.store_storingen(raw_conn, 'philips_storingen', ph_data)
                print(f"✓ philips_storingen: {len(ph_data)} records stored")
            except Exception as e:
                print(f"⚠ Could not extract Philips storingen: {e}")
            finally:
                ph_conn.close()
        else:
            print("⚠ Could not connect to Storingen Philips database")

    # ── OTIF Excel ────────────────────────────────────────────────────────
    otif_path = paths.get("otif_excel", "")
    if otif_path:
        try:
            otif_kpi, otif_table = excel_reader.load_otif_data(otif_path, raw_conn)
            raw_db.store_blob(raw_conn, 'otif_kpi_data',   otif_kpi)
            raw_db.store_blob(raw_conn, 'otif_table_data', otif_table)
            print("✓ OTIF data stored to blobs")
        except Exception as e:
            print(f"⚠ Could not load OTIF data: {e}")

    # ── VSM Excel ─────────────────────────────────────────────────────────
    vsm_path = paths.get("vsm_excel", "")
    if vsm_path:
        try:
            vsm_data = excel_reader.load_vsm_data(vsm_path, raw_conn)
            raw_db.store_blob(raw_conn, 'vsm_data', vsm_data)
            print("✓ VSM data stored to blobs")
        except Exception as e:
            print(f"⚠ Could not load VSM data: {e}")

    # ── Planning HTML ─────────────────────────────────────────────────────
    planning_html_path = paths.get("planning_html", "")
    if planning_html_path:
        try:
            html_content = html_reader.load_planning_html(planning_html_path)
            raw_db.store_blob(raw_conn, 'planning_html', html_content)
            print("✓ planning_html stored to blobs")
        except Exception as e:
            print(f"⚠ Could not load planning.html: {e}")

    # ── Productieschema HTML ──────────────────────────────────────────────
    prod_html_path = paths.get("productieschema_html", "")
    if prod_html_path:
        try:
            html_content = html_reader.load_productieschema_html(prod_html_path)
            raw_db.store_blob(raw_conn, 'productieschema_html', html_content)
            print("✓ productieschema_html stored to blobs")
        except Exception as e:
            print(f"⚠ Could not load productieschema HTML: {e}")

    # ── Dosissen HTML ─────────────────────────────────────────────────────
    dosissen_html_path = paths.get("dosissen_html", "")
    if dosissen_html_path:
        try:
            with open(dosissen_html_path, 'r', encoding='utf-8') as fh:
                dosissen_content = fh.read()
            raw_db.store_blob(raw_conn, 'dosissen_html', dosissen_content)
            print("✓ dosissen_html stored to blobs")
        except Exception as e:
            print(f"⚠ Could not load dosissen HTML: {e}")

    raw_conn.close()
    print("=" * 60)
    print("✓ Collection complete")
    return True


if __name__ == "__main__":
    main()
