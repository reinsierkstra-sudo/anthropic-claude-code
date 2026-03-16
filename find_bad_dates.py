"""
find_bad_dates.py
-----------------
Scan all isotope tables in the SQLite database for records whose date
column has an unrealistic year (outside 1900–3000) and print the
table name, BO number (identifier), and the raw date value.
"""
import sqlite3
import sys

DB_PATH = 'isotope_data.db'

TABLES = [
    'gallium_data',
    'rubidium_data',
    'indium_data',
    'thallium_data',
    'iodine_data',
]

def main():
    conn = sqlite3.connect(DB_PATH)
    found = 0
    for table in TABLES:
        try:
            rows = conn.execute(
                f"SELECT identifier, date FROM {table} "
                f"WHERE CAST(substr(date, 1, instr(date, '-') - 1) AS INTEGER) NOT BETWEEN 1900 AND 3000"
            ).fetchall()
        except sqlite3.OperationalError as e:
            print(f"[SKIP] {table}: {e}")
            continue
        for identifier, date in rows:
            print(f"  table={table}  BO={identifier}  date={date!r}")
            found += 1
    conn.close()
    if found == 0:
        print("No bad-year records found in SQLite.")
    else:
        print(f"\nTotal: {found} bad record(s)")

if __name__ == '__main__':
    main()
