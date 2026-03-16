"""
collector/raw_db.py
-------------------
Owns the SQLite raw database.

Responsibilities
----------------
- Define the canonical table schemas (``_TABLE_SCHEMAS``).
- Open a connection and ensure all tables exist (``connect``).
- Insert / update rows from a list of dicts (``store``).
- Load all rows from a table as a list of dicts (``load_table``).
"""

import sqlite3
from datetime import datetime


# ---------------------------------------------------------------------------
# Table schemas (verbatim from IsotopeDashboardGenerator._TABLE_SCHEMAS)
# ---------------------------------------------------------------------------

_TABLE_SCHEMAS = {
    'iodine_data': {
        'columns': [
            ('date', 'TEXT'), ('value1', 'REAL'), ('value2', 'REAL'),
            ('efficiency', 'REAL'), ('efficiency_raw', 'REAL'),
            ('identifier', 'TEXT'), ('bo_targetstroom', 'REAL'),
            ('targetstroom', 'REAL'), ('yield_percent', 'REAL'),
            ('output_percent', 'REAL'), ('cyclotron', 'TEXT'),
            ('totale_dosis', 'REAL'), ('meting_d1', 'REAL'),
            ('meting_waste', 'REAL'), ('verwacht', 'REAL'),
            ('stop_datum', 'TEXT'), ('stop_tijd', 'TEXT'),
            ('start_tijd', 'TEXT'), ('totale_bestralingstijd', 'REAL'),
            ('totale_storingstijd', 'REAL'), ('opmerking', 'TEXT'),
            ('extracted_at', 'TEXT'),
        ],
        'alter_add': [
            ('yield_percent', 'REAL'), ('output_percent', 'REAL'), ('cyclotron', 'TEXT'),
            ('totale_dosis', 'REAL'), ('meting_d1', 'REAL'), ('meting_waste', 'REAL'),
            ('verwacht', 'REAL'), ('stop_datum', 'TEXT'), ('stop_tijd', 'TEXT'),
            ('start_tijd', 'TEXT'), ('totale_bestralingstijd', 'REAL'),
            ('totale_storingstijd', 'REAL'), ('opmerking', 'TEXT'),
        ],
        'str_cols': {'stop_datum', 'stop_tijd', 'start_tijd'},
    },
    'rubidium_data': {
        'columns': [
            ('date', 'TEXT'), ('value1', 'REAL'), ('value2', 'REAL'),
            ('efficiency', 'REAL'), ('identifier', 'TEXT'),
            ('stroom', 'REAL'), ('extracted_at', 'TEXT'),
        ],
    },
    'gallium_data': {
        'columns': [
            ('date', 'TEXT'), ('targetstroom', 'REAL'),
            ('identifier', 'TEXT'), ('extracted_at', 'TEXT'),
        ],
    },
    '__default__': {
        'columns': [
            ('date', 'TEXT'), ('value1', 'REAL'), ('value2', 'REAL'),
            ('efficiency', 'REAL'), ('identifier', 'TEXT'), ('extracted_at', 'TEXT'),
        ],
    },
}

# indium and thallium share the gallium schema
_TABLE_SCHEMAS['indium_data']   = _TABLE_SCHEMAS['gallium_data']
_TABLE_SCHEMAS['thallium_data'] = _TABLE_SCHEMAS['gallium_data']


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection to *db_path* and ensure all required tables exist.

    Creates the ``excel_cache`` and ``production_comments`` helper tables as
    well as every isotope data table defined in ``_TABLE_SCHEMAS``.

    Parameters
    ----------
    db_path : str
        Filesystem path to the SQLite database file.  The file is created
        automatically if it does not yet exist.

    Returns
    -------
    sqlite3.Connection
        An open connection with all schema migrations applied.
    """
    conn = sqlite3.connect(db_path)

    # --- excel_cache table (used by excel_reader caching helpers) -----------
    conn.execute('''
        CREATE TABLE IF NOT EXISTS excel_cache (
            cache_key TEXT PRIMARY KEY,
            mtime     REAL NOT NULL,
            data_json TEXT NOT NULL,
            saved_at  TEXT NOT NULL
        )
    ''')

    # --- production_comments table ------------------------------------------
    conn.execute('''
        CREATE TABLE IF NOT EXISTS production_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isotope_type TEXT,
            production_date TEXT,
            bo_number TEXT,
            comment_type TEXT,
            created_at TEXT,
            UNIQUE(isotope_type, production_date, bo_number)
        )
    ''')

    # --- isotope data tables ------------------------------------------------
    for table_name, schema in _TABLE_SCHEMAS.items():
        if table_name == '__default__':
            continue

        col_defs = schema['columns']
        col_sql = ',\n                    '.join(f'{name} {typ}' for name, typ in col_defs)
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {col_sql},
                UNIQUE(identifier, date)
            )
        ''')

        # Apply any ALTER TABLE migrations for columns added after original schema
        for _col, _typ in schema.get('alter_add', []):
            try:
                conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {_col} {_typ}')
            except Exception:
                pass  # column already exists

    conn.commit()
    return conn


def store(conn: sqlite3.Connection, table_name: str, data: list,
          *extra_col_names) -> None:
    """Insert or update rows from *data* into *table_name*.

    Uses the schema defined in ``_TABLE_SCHEMAS`` to determine which columns
    to write.  For each record the function checks whether a row with the same
    ``(identifier, date)`` pair already exists; if so it updates the non-key
    columns, otherwise it inserts a new row.

    The optional *extra_col_names* positional arguments mirror the ``col1`` /
    ``col2`` parameters of the original ``store_in_sqlite`` method and are
    accepted for call-site compatibility but are not used internally — the
    schema already enumerates all columns.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open SQLite connection (typically returned by :func:`connect`).
    table_name : str
        The target table, must be a key in ``_TABLE_SCHEMAS``.
    data : list[dict]
        Records to persist.  Each dict must contain at least ``'date'`` and
        ``'identifier'`` keys.
    *extra_col_names
        Ignored — kept for backwards-compatible call signatures.
    """
    if table_name not in _TABLE_SCHEMAS:
        raise ValueError(f"Unknown table: {table_name!r}")

    cursor = conn.cursor()

    schema = _TABLE_SCHEMAS.get(table_name, _TABLE_SCHEMAS['__default__'])
    col_defs = schema['columns']
    col_names = [c[0] for c in col_defs]
    str_cols = schema.get('str_cols', set())

    # Ensure the table and its migrations exist (idempotent)
    col_sql = ',\n                    '.join(f'{name} {typ}' for name, typ in col_defs)
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {col_sql},
            UNIQUE(identifier, date)
        )
    ''')

    for _col, _typ in schema.get('alter_add', []):
        try:
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {_col} {_typ}')
        except Exception:
            pass  # column already exists

    # Rebuild with UNIQUE constraint if missing (handles pre-constraint databases)
    try:
        idx_info = cursor.execute(f"PRAGMA index_list({table_name})").fetchall()
        if not any('uq_' in str(row) for row in idx_info):
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name}_dedup AS
                SELECT * FROM {table_name}
                WHERE id IN (SELECT MIN(id) FROM {table_name} GROUP BY identifier, date)
            ''')
            cursor.execute(f'DROP TABLE {table_name}')
            cursor.execute(f'ALTER TABLE {table_name}_dedup RENAME TO {table_name}')
            cursor.execute(f'''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_{table_name}_identifier_date
                ON {table_name} (identifier, date)
            ''')
            conn.commit()
    except Exception:
        pass  # Non-critical

    extracted_at = datetime.now().isoformat()

    def _val(record, col, date_str, identifier):
        if col == 'date':         return date_str
        if col == 'identifier':   return identifier
        if col == 'extracted_at': return extracted_at
        v = record.get(col)
        if col in str_cols:
            return str(v) if v is not None else None
        return v

    update_cols = [c for c in col_names if c not in ('date', 'identifier')]
    set_sql     = ', '.join(f'{c}=?' for c in update_cols)
    insert_sql  = (f"INSERT INTO {table_name} ({', '.join(col_names)}) "
                   f"VALUES ({', '.join('?' * len(col_names))})")

    for record in data:
        raw_date = record.get('date')
        date_str = (raw_date.strftime('%Y-%m-%d') if isinstance(raw_date, datetime)
                    else str(raw_date) if raw_date else None)
        if date_str is None:
            continue
        identifier = str(record['identifier']) if record.get('identifier') is not None else None

        existing = cursor.execute(
            f'SELECT id FROM {table_name} WHERE identifier=? AND date=?',
            (identifier, date_str)
        ).fetchone()

        if existing:
            update_vals = tuple(_val(record, c, date_str, identifier) for c in update_cols)
            cursor.execute(
                f'UPDATE {table_name} SET {set_sql} WHERE identifier=? AND date=?',
                update_vals + (identifier, date_str)
            )
        else:
            insert_vals = tuple(_val(record, c, date_str, identifier) for c in col_names)
            cursor.execute(insert_sql, insert_vals)

    conn.commit()
    cursor.close()


def get_max_date(conn: sqlite3.Connection, table_name: str) -> str | None:
    """Return the most recent ``date`` value stored in *table_name*, or ``None``.

    Used by the collector to determine the starting point for incremental
    extraction.  Returns a ``'YYYY-MM-DD'`` string, or ``None`` if the table
    is empty or does not exist.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open SQLite connection.
    table_name : str
        The name of the table to inspect.
    """
    try:
        row = conn.execute(f"SELECT MAX(date) FROM {table_name}").fetchone()
        return row[0] if row and row[0] else None
    except sqlite3.OperationalError:
        return None


def load_table(conn: sqlite3.Connection, table_name: str) -> list:
    """Return all rows from *table_name* as a list of dicts.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open SQLite connection.
    table_name : str
        The name of the table to query.

    Returns
    -------
    list[dict]
        One dict per row, keyed by column name.  Returns an empty list if the
        table does not exist or contains no rows.
    """
    try:
        cursor = conn.execute(f'SELECT * FROM {table_name}')
        col_names = [desc[0] for desc in cursor.description]
        return [dict(zip(col_names, row)) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
