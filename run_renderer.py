"""
run_renderer.py
---------------
Entry point that generates the HTML dashboards from derived/calculated data.

This is phase 3 of the refactored pipeline:
  run_collector  →  run_calculator  →  **run_renderer**

Usage::

    python run_renderer.py

The script:
1. Loads configuration to discover output paths.
2. Reads all calculated KPIs from ``data/derived.db`` (written by run_calculator).
3. Fetches live cyclotron / gantt data.
4. Renders both the full dashboard and the truncated dashboard.
5. Writes the HTML files to their respective output paths.
6. Applies file-protection (read-only + SHA-256 hash) to each output.

Prints ``✓`` / ``⚠`` / ``✗`` status lines for each stage.
"""

import os
import traceback
from datetime import datetime

from config.loader import load_settings
from renderer import dashboard_full, dashboard_truncated, file_protection


def main() -> bool:
    """Render both dashboards and write them to the configured output paths.

    Returns ``True`` on success, ``False`` if a critical step fails.
    """
    cfg = load_settings()
    paths = cfg.get("paths", {})
    urls  = cfg.get("urls",  {})

    print("=" * 60)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] run_renderer — HTML generation")
    print("=" * 60)

    # ── Phase 1: load calculated data from derived.db ────────────────────
    from collector.derived_db import connect as connect_derived, load_kpis
    derived_db_path = paths.get("derived_db", "data/derived.db")
    try:
        derived_conn = connect_derived(derived_db_path)
        data = load_kpis(derived_conn)
        derived_conn.close()
    except Exception as e:
        print(f"✗ Could not open derived.db: {e}")
        return False
    if not data:
        print("✗ derived.db is empty — run run_calculator.py first.")
        return False
    print(f"✓ Loaded {len(data)} KPIs from derived.db")

    # ── Phase 2: fetch cyclotron / gantt data ─────────────────────────────
    from collector.http_reader import fetch_cyclotron_data
    from renderer.gantt import convert_bestralingen_to_gantt_format

    cyclotron_url = urls.get("cyclotron_planning",
                             "http://pett-webw02p/procdashboard/cyclotron.asp")
    try:
        cyclotron_data = fetch_cyclotron_data(cyclotron_url)
        print(f"✓ Fetched cyclotron data ({len(cyclotron_data)} entries)")
    except Exception as e:
        print(f"⚠ Could not fetch cyclotron data: {e}")
        cyclotron_data = []

    try:
        bestralingen_gantt = convert_bestralingen_to_gantt_format(
            data.get("ga_all", []),
            data.get("rb_all", []),
            data.get("in_all", []),
            data.get("tl_all", []),
            data.get("io_all", []),
        )
        print(f"✓ Converted bestralingen to gantt format ({len(bestralingen_gantt)} entries)")
    except Exception as e:
        print(f"⚠ Could not convert bestralingen to gantt format: {e}")
        bestralingen_gantt = []

    # Deduplicate: prefer historical data over planning data for same BO.
    historical_bonrs = {
        item["bonr"]: item["startDate"]
        for item in bestralingen_gantt
        if item.get("bonr")
    }
    deduplicated_planning = [
        p for p in cyclotron_data
        if not p.get("bonr")
        or p["bonr"] not in historical_bonrs
        or historical_bonrs[p["bonr"]] != p.get("startDate")
    ]
    combined_gantt_data = bestralingen_gantt + deduplicated_planning
    data["cyclotron_data"] = combined_gantt_data

    # ── Phase 4: render full dashboard ───────────────────────────────────
    local_path      = paths.get("output_local",  "isotope_dashboard.html")
    local_hash_path = local_path + ".hash"

    # Check integrity before overwriting.
    tampering_warning = None
    ok, msg = file_protection.check_file_integrity(local_path, local_hash_path)
    if not ok:
        tampering_warning = msg
        print("⚠ LOCAL FILE TAMPERED — regenerating with warning banner")
    data["tampering_warning"] = tampering_warning

    try:
        html_full = dashboard_full.create_html_dashboard(data)
    except Exception as e:
        print(f"✗ Full dashboard rendering failed: {e}")
        traceback.print_exc()
        return False

    # ── Phase 5: render truncated dashboard ───────────────────────────────
    try:
        html_truncated = dashboard_truncated.create_truncated_dashboard(data)
    except Exception as e:
        print(f"✗ Truncated dashboard rendering failed: {e}")
        traceback.print_exc()
        return False

    # ── Phase 6: write full dashboard (local) ────────────────────────────
    if os.path.exists(local_path):
        file_protection.remove_readonly(local_path)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html_full)

    file_protection.set_readonly(local_path)
    file_protection.save_file_hash(local_path, local_hash_path)
    print("✓ Full dashboard written (local)")

    # ── Phase 7: write truncated dashboard (network) ─────────────────────
    network_path      = paths.get("output_network", r"\\TUPETT-FI01\Data$\Malshare\Cyclotron\Dashboard Cyclotron\isotope_dashboard.html")
    network_hash_path = network_path + ".hash"
    try:
        net_dir = os.path.dirname(network_path)
        if net_dir and not os.path.exists(net_dir):
            os.makedirs(net_dir, exist_ok=True)
        if os.path.exists(network_path):
            file_protection.remove_readonly(network_path)
        with open(network_path, "w", encoding="utf-8") as f:
            f.write(html_truncated)
        file_protection.set_readonly(network_path)
        file_protection.save_file_hash(network_path, network_hash_path)
        print("✓ Truncated dashboard written (network)")
    except Exception as e:
        print(f"⚠ Could not write network dashboard: {e}")

    # ── Phase 8: write full dashboard (bureau) ────────────────────────────
    bureau_path      = paths.get("output_bureau", r"X:\Cyclotron Bureau\Productie dashboard.html")
    bureau_hash_path = bureau_path + ".hash"
    try:
        bureau_dir = os.path.dirname(bureau_path)
        if bureau_dir and not os.path.exists(bureau_dir):
            raise FileNotFoundError(f"Bureau directory does not exist: {bureau_dir}")
        if os.path.exists(bureau_path):
            file_protection.remove_readonly(bureau_path)
        with open(bureau_path, "w", encoding="utf-8") as f:
            f.write(html_full)
        file_protection.set_readonly(bureau_path)
        file_protection.save_file_hash(bureau_path, bureau_hash_path)
        print("✓ Full dashboard written (bureau)")
    except Exception as e:
        print(f"✗ ERROR writing bureau dashboard: {e}")
        raise

    return True


if __name__ == "__main__":
    main()
