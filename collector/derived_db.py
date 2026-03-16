"""
collector/derived_db.py
-----------------------
Owns the SQLite derived database (data/derived.db).

Responsibilities
----------------
- Define the schema (a simple JSON key-value store).
- Open a connection and ensure the table exists (``connect``).
- Serialise and upsert all KPI values at once (``save_kpis``).
- Load and deserialise all KPI values at once (``load_kpis``).

Design note
-----------
All values are stored as JSON strings so the schema never needs to change
when new KPIs are added.  Date / datetime objects are serialised to ISO
strings.  Defaultdicts are serialised as plain dicts.
"""

import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

class _DateEncoder(json.JSONEncoder):
    """Encode date/datetime objects as ISO strings during serialisation."""

    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        # Convert defaultdicts to plain dicts so json can handle them.
        if isinstance(obj, defaultdict):
            return dict(obj)
        return super().default(obj)


def _encode(value) -> str:
    """Serialise *value* to a JSON string."""
    return json.dumps(value, cls=_DateEncoder)


def _decode(text: str):
    """Deserialise a JSON string back to a Python object."""
    return json.loads(text)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kpis (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    computed_at TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def connect(db_path: str) -> sqlite3.Connection:
    """Open (and initialise) the derived database at *db_path*.

    Creates the file and the ``kpis`` table automatically if they do not
    exist yet.

    Parameters
    ----------
    db_path : str
        Filesystem path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        An open connection with the schema applied.
    """
    import os
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def save_kpis(conn: sqlite3.Connection, data: dict) -> None:
    """Serialise every key in *data* and upsert into the ``kpis`` table.

    Existing rows are replaced so the table always reflects the latest
    calculation run.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open connection to the derived database.
    data : dict
        The full results dict produced by ``run_calculator.main()``.
    """
    now = datetime.now().isoformat()
    rows = []
    for key, value in data.items():
        try:
            rows.append((key, _encode(value), now))
        except (TypeError, ValueError) as exc:
            # Skip keys that cannot be serialised rather than aborting.
            print(f"⚠ derived_db: could not serialise key {key!r}: {exc}")
    conn.executemany(
        "INSERT OR REPLACE INTO kpis (key, value, computed_at) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()


def load_kpis(conn: sqlite3.Connection) -> dict:
    """Load and deserialise all KPIs from the ``kpis`` table.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open connection to the derived database.

    Returns
    -------
    dict
        A flat dict of all stored KPI values, ready to be passed to the
        renderer.  Returns an empty dict if the table is empty.
    """
    rows = conn.execute("SELECT key, value FROM kpis").fetchall()
    result = {}
    for key, value in rows:
        try:
            result[key] = _decode(value)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"⚠ derived_db: could not deserialise key {key!r}: {exc}")
    return result
