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
- Store / load JSON blobs by key (``store_blob`` / ``load_blob``).
- Store / load simple JSON-serialisable lists (``store_json_list`` /
  ``load_json_list``).
"""

import json
import sqlite3
from datetime import datetime


# ---------------------------------------------------------------------------
# Table schemas
# ---------------------------------------------------------------------------

_TABLE_SCHEMAS = {
    # ------------------------------------------------------------------
    # Isotope production records
    # ------------------------------------------------------------------
    'iodine_data': {
        'columns': [
            ('date',                   'TEXT'), ('value1',                'REAL'),
            ('value2',                 'REAL'), ('efficiency',            'REAL'),
            ('efficiency_raw',         'REAL'), ('identifier',            'TEXT'),
            ('bo_targetstroom',        'REAL'), ('targetstroom',          'REAL'),
            ('yield_percent',          'REAL'), ('output_percent',        'REAL'),
            ('cyclotron',              'TEXT'), ('totale_dosis',          'REAL'),
            ('meting_d1',              'REAL'), ('meting_waste',          'REAL'),
            ('verwacht',               'REAL'), ('stop_datum',            'TEXT'),
            ('stop_tijd',              'TEXT'), ('start_tijd',            'TEXT'),
            ('totale_bestralingstijd', 'REAL'), ('totale_storingstijd',   'REAL'),
            ('opmerking',              'TEXT'), ('extracted_at',          'TEXT'),
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
            ('date',         'TEXT'), ('value1',       'REAL'),
            ('value2',       'REAL'), ('efficiency',   'REAL'),
            ('identifier',   'TEXT'), ('cyclotron',    'TEXT'),
            ('stroom',       'REAL'), ('duur',         'REAL'),
            ('eob_tijd',     'TEXT'), ('opmerking',    'TEXT'),
            ('extracted_at', 'TEXT'),
        ],
        'alter_add': [
            ('cyclotron', 'TEXT'), ('duur', 'REAL'), ('eob_tijd', 'TEXT'), ('opmerking', 'TEXT'),
        ],
    },
    'gallium_data': {
        'columns': [
            ('date',         'TEXT'), ('targetstroom', 'REAL'),
            ('identifier',   'TEXT'), ('cyclotron',    'TEXT'),
            ('duur',         'REAL'), ('eobhrmin',     'TEXT'),
            ('opmerking',    'TEXT'), ('extracted_at', 'TEXT'),
        ],
        'alter_add': [
            ('cyclotron', 'TEXT'), ('duur', 'REAL'), ('eobhrmin', 'TEXT'), ('opmerking', 'TEXT'),
        ],
    },
    'indium_data': {
        'columns': [
            ('date',              'TEXT'), ('targetstroom',        'REAL'),
            ('identifier',        'TEXT'), ('cyclotron',           'TEXT'),
            ('bestralingspositie','TEXT'), ('duur',                'REAL'),
            ('eobhrmin',          'TEXT'), ('opmerking',           'TEXT'),
            ('extracted_at',      'TEXT'),
        ],
        'alter_add': [
            ('cyclotron', 'TEXT'), ('bestralingspositie', 'TEXT'),
            ('duur', 'REAL'), ('eobhrmin', 'TEXT'), ('opmerking', 'TEXT'),
        ],
    },
    'thallium_data': {
        'columns': [
            ('date',         'TEXT'), ('targetstroom', 'REAL'),
            ('identifier',   'TEXT'), ('cyclotron',    'TEXT'),
            ('kant',         'TEXT'), ('duur',         'REAL'),
            ('eob_tijd',     'TEXT'), ('opmerking',    'TEXT'),
            ('extracted_at', 'TEXT'),
        ],
        'alter_add': [
            ('cyclotron', 'TEXT'), ('kant', 'TEXT'), ('duur', 'REAL'),
            ('eob_tijd', 'TEXT'), ('opmerking', 'TEXT'),
        ],
    },
    '__default__': {
        'columns': [
            ('date', 'TEXT'), ('value1', 'REAL'), ('value2', 'REAL'),
            ('efficiency', 'REAL'), ('identifier', 'TEXT'), ('extracted_at', 'TEXT'),
        ],
    },
}


# ---------------------------------------------------------------------------
# Schemas for auxiliary tables with date-only uniqueness
# ---------------------------------------------------------------------------

_AUX_DATE_SCHEMAS = {
    'gallium_opbrengsten': [
        ('date', 'TEXT'), ('opbrengst_mbq', 'REAL'), ('extracted_at', 'TEXT'),
    ],
    'indium_opbrengsten': [
        ('date', 'TEXT'), ('opbrengst_mbq', 'REAL'), ('extracted_at', 'TEXT'),
    ],
    'efficiency_targets': [
        ('date', 'TEXT'), ('efficiency', 'REAL'), ('extracted_at', 'TEXT'),
    ],
}

# Schemas for storingen tables with (storingsnummer, datum) uniqueness
_STORINGEN_SCHEMAS = {
    'iba_storingen': [
        ('storingsnummer', 'TEXT'), ('datum', 'TEXT'), ('storing', 'TEXT'),
        ('extracted_at', 'TEXT'),
    ],
    'philips_storingen': [
        ('storingsnummer', 'TEXT'), ('datum', 'TEXT'), ('storing', 'TEXT'),
        ('extracted_at', 'TEXT'),
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection to *db_path* and ensure all required tables exist."""
    conn = sqlite3.connect(db_path)

    # excel_cache
    conn.execute('''
        CREATE TABLE IF NOT EXISTS excel_cache (
            cache_key TEXT PRIMARY KEY,
            mtime     REAL NOT NULL,
            data_json TEXT NOT NULL,
            saved_at  TEXT NOT NULL
        )
    ''')

    # production_comments
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

    # blobs key-value store
    conn.execute('''
        CREATE TABLE IF NOT EXISTS blobs (
            key        TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # Isotope tables (UNIQUE on identifier + date)
    for table_name, schema in _TABLE_SCHEMAS.items():
        if table_name == '__default__':
            continue
        col_defs = schema['columns']
        col_sql  = ', '.join(f'{n} {t}' for n, t in col_defs)
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {col_sql},
                UNIQUE(identifier, date)
            )
        ''')
        for _col, _typ in schema.get('alter_add', []):
            try:
                conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {_col} {_typ}')
            except Exception:
                pass

    # Opbrengsten / efficiency_targets (UNIQUE on date only)
    for table_name, cols in _AUX_DATE_SCHEMAS.items():
        col_sql = ', '.join(f'{n} {t}' for n, t in cols)
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {col_sql},
                UNIQUE(date)
            )
        ''')
        for _col, _typ in cols[1:]:   # migrate any new columns
            try:
                conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {_col} {_typ}')
            except Exception:
                pass

    # Storingen (UNIQUE on storingsnummer + datum)
    for table_name, cols in _STORINGEN_SCHEMAS.items():
        col_sql = ', '.join(f'{n} {t}' for n, t in cols)
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {col_sql},
                UNIQUE(storingsnummer, datum)
            )
        ''')

    conn.commit()
    return conn


def store(conn: sqlite3.Connection, table_name: str, data: list,
          *extra_col_names) -> None:
    """Insert or update rows from *data* into *table_name*.

    Uses the schema defined in ``_TABLE_SCHEMAS`` to determine which columns
    to write.  For each record the function checks whether a row with the same
    ``(identifier, date)`` pair already exists; if so it updates the non-key
    columns, otherwise it inserts a new row.
    """
    if table_name not in _TABLE_SCHEMAS:
        raise ValueError(f"Unknown table: {table_name!r}")

    cursor = conn.cursor()

    schema    = _TABLE_SCHEMAS.get(table_name, _TABLE_SCHEMAS['__default__'])
    col_defs  = schema['columns']
    col_names = [c[0] for c in col_defs]
    str_cols  = schema.get('str_cols', set())

    col_sql = ', '.join(f'{n} {t}' for n, t in col_defs)
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
            pass

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
            vals = tuple(_val(record, c, date_str, identifier) for c in update_cols)
            cursor.execute(
                f'UPDATE {table_name} SET {set_sql} WHERE identifier=? AND date=?',
                vals + (identifier, date_str)
            )
        else:
            vals = tuple(_val(record, c, date_str, identifier) for c in col_names)
            cursor.execute(insert_sql, vals)

    conn.commit()
    cursor.close()


def store_opbrengsten(conn: sqlite3.Connection, table_name: str, data: list) -> None:
    """Insert or update opbrengsten / efficiency_targets rows (UNIQUE on date only)."""
    if table_name not in _AUX_DATE_SCHEMAS:
        raise ValueError(f"Not an aux-date table: {table_name!r}")
    cols = [c[0] for c in _AUX_DATE_SCHEMAS[table_name]]
    extracted_at = datetime.now().isoformat()
    cursor = conn.cursor()
    for record in data:
        raw_date = record.get('date')
        date_str = (raw_date.strftime('%Y-%m-%d') if isinstance(raw_date, datetime)
                    else str(raw_date) if raw_date else None)
        if not date_str:
            continue
        row = {c: record.get(c) for c in cols}
        row['date']         = date_str
        row['extracted_at'] = extracted_at
        cursor.execute(
            f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})",
            tuple(row[c] for c in cols)
        )
    conn.commit()
    cursor.close()


def store_storingen(conn: sqlite3.Connection, table_name: str, data: list) -> None:
    """Insert or update storingen rows (UNIQUE on storingsnummer + datum)."""
    if table_name not in _STORINGEN_SCHEMAS:
        raise ValueError(f"Not a storingen table: {table_name!r}")
    cols = [c[0] for c in _STORINGEN_SCHEMAS[table_name]]
    extracted_at = datetime.now().isoformat()
    cursor = conn.cursor()
    for record in data:
        row = {c: record.get(c) for c in cols}
        row['extracted_at'] = extracted_at
        cursor.execute(
            f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})",
            tuple(row[c] for c in cols)
        )
    conn.commit()
    cursor.close()


def store_blob(conn: sqlite3.Connection, key: str, value) -> None:
    """Serialise *value* as JSON and upsert under *key* in the blobs table."""
    conn.execute(
        'INSERT OR REPLACE INTO blobs (key, value_json, updated_at) VALUES (?, ?, ?)',
        (key, json.dumps(value, default=str), datetime.now().isoformat())
    )
    conn.commit()


def load_blob(conn: sqlite3.Connection, key: str, default=None):
    """Return the deserialised value stored under *key*, or *default* if absent."""
    try:
        row = conn.execute('SELECT value_json FROM blobs WHERE key=?', (key,)).fetchone()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return default


def get_max_date(conn: sqlite3.Connection, table_name: str) -> str | None:
    """Return the most recent ``date`` value stored in *table_name*, or ``None``."""
    try:
        row = conn.execute(f"SELECT MAX(date) FROM {table_name}").fetchone()
        return row[0] if row and row[0] else None
    except sqlite3.OperationalError:
        return None


def load_table(conn: sqlite3.Connection, table_name: str) -> list:
    """Return all rows from *table_name* as a list of dicts."""
    try:
        cursor = conn.execute(f'SELECT * FROM {table_name}')
        col_names = [desc[0] for desc in cursor.description]
        return [dict(zip(col_names, row)) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
