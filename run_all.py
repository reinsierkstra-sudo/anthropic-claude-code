"""
run_all.py
----------
Main loop entry point — equivalent to the ``while True`` loop in the
original ``gallium_extractor.py`` ``__main__`` block.

Runs all three pipeline phases in sequence on every iteration:
  1. ``run_collector``  — data collection → SQLite
  2. ``run_calculator`` — KPI calculations (in-memory)
  3. ``run_renderer``   — HTML generation + file write

Usage::

    python run_all.py

The loop interval is read from ``config/settings.yaml`` under the key
``loop_interval_seconds`` (default: 60 s).  Press Ctrl+C to stop.
"""

import time
from datetime import datetime

from run_collector import main as collect
from run_calculator import main as calculate
from run_renderer import main as render
from config.loader import load_settings


def main() -> None:
    """Run the collection → calculation → rendering loop indefinitely."""
    cfg = load_settings()
    interval = cfg.get("loop_interval_seconds", 60)
    loop_counter = 0

    print("=" * 60)
    print("Isotope Dashboard Generator — Continuous Mode")
    print(f"Regenerating dashboard every {interval} seconds...")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    try:
        while True:
            loop_counter += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] === Loop {loop_counter} ===")

            try:
                collect()
                calculate()
                render()
                print(f"[OK] Loop {loop_counter} complete. "
                      f"Waiting {interval}s until next update...")
            except Exception as e:
                print(f"\n[ERROR] Error during loop {loop_counter}: {e}")
                print(f"Waiting {interval}s before retry...")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Dashboard generator stopped by user")
        print("=" * 60)


if __name__ == "__main__":
    main()
