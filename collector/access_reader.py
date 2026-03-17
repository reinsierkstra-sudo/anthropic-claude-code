"""
collector/access_reader.py
--------------------------
Reads production data from MS Access databases via pyodbc.

Provides
--------
- Low-level connection helpers (``connect_access``, ``connect_proces_db``,
  ``connect_storingen_iba``, ``connect_storingen_philips``).
- Standalone ``extract_*`` functions that accept a pyodbc connection as their
  first argument instead of ``self``, making them testable without an
  ``IsotopeDashboardGenerator`` instance.
- Module-level helpers carried over from the monolith:
  ``parse_eobhrmin``, ``parse_time_duration``, ``_to_date``, ``_fmt_bo``.
"""

import traceback
import pyodbc
from datetime import date, datetime


def _date_filter(since_date, col_name: str) -> str:
    """Return an MS Access WHERE clause for *col_name* >= *since_date*, or empty string.

    MS Access date literals use the ``#MM/DD/YYYY#`` format.
    """
    if since_date is None:
        return ""
    return f"WHERE [{col_name}] >= #{since_date.strftime('%m/%d/%Y')}#"


# ---------------------------------------------------------------------------
# Module-level helpers (originally on the class or at module level)
# ---------------------------------------------------------------------------

def _to_date(d):
    """Normalise any date/datetime/str value to a datetime.date, or None on failure."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if hasattr(d, 'year') and not isinstance(d, datetime):
        # Already a date object
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(d, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
    return None


def _fmt_bo(bo):
    """Format a BO number: strip trailing .0 and dashes, return as plain integer string.

    If the value is not numeric, return it unchanged.
    """
    if bo is None:
        return None
    if str(bo).replace('.', '').replace('-', '').isdigit():
        return str(int(float(bo)))
    return bo


def parse_eobhrmin(eobhrmin_str):
    """Parse an eobhrmin value to a ``(hours, minutes)`` tuple, or ``None`` on failure.

    Accepts time objects, numeric floats (HH.MM encoding), colon-separated
    strings, and compact integer strings (``'HHMM'``).
    """
    if eobhrmin_str is None or eobhrmin_str == '':
        return None
    if hasattr(eobhrmin_str, 'hour') and hasattr(eobhrmin_str, 'minute'):
        return (eobhrmin_str.hour, eobhrmin_str.minute)
    if isinstance(eobhrmin_str, (int, float)):
        hours = int(eobhrmin_str)
        if hours < 0 or hours > 23:
            return None
        decimal_part = eobhrmin_str - int(eobhrmin_str)
        minutes = round(decimal_part * 100)
        if minutes < 0 or minutes > 59:
            return None
        return (hours, minutes)
    try:
        eobhrmin_str = str(eobhrmin_str).strip()
        if ':' in eobhrmin_str:
            parts = eobhrmin_str.split(':')
            hours, minutes = int(parts[0]), int(parts[1])
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                return None
            return (hours, minutes)
        elif len(eobhrmin_str) >= 3:
            if len(eobhrmin_str) == 3:
                hours, minutes = int(eobhrmin_str[0]), int(eobhrmin_str[1:])
            else:
                hours, minutes = int(eobhrmin_str[:2]), int(eobhrmin_str[2:4])
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                return None
            return (hours, minutes)
    except Exception:
        pass
    return None


def parse_time_duration(duration_str, debug_bo=None):
    """Parse HH.MM format to total hours.

    Format: HH.MM where MM is actual minutes (0-59), not decimal.

    Examples::

        9.05  → 9 hours  5 minutes → 9.0833 hours
        12.30 → 12 hours 30 minutes → 12.5 hours
        10.45 → 10 hours 45 minutes → 10.75 hours

    CRITICAL: When the database stores 10.3 as a float it means 10:30
    (not 10:03).  The decimal .3 represents 30 minutes, .5 represents
    50 minutes, etc.
    """
    try:
        # Handle None or empty
        if duration_str is None or duration_str == '':
            return 0

        # Convert to string to handle both numeric and string inputs
        duration_str = str(duration_str).strip()

        # Handle colon separator (HH:MM format)
        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 2:
                hours = float(parts[0])
                minutes = float(parts[1])
                result = hours + (minutes / 60.0)
                return result

        # Handle dot separator (HH.MM format)
        if '.' in duration_str:
            parts = duration_str.split('.')
            if len(parts) == 2:
                hours = float(parts[0])
                # FIX: Pad minutes to 2 digits on the RIGHT
                # '3' → '30' (30 minutes), '05' → '05' (5 minutes)
                minute_str = parts[1].ljust(2, '0')  # Left-justify and pad with '0' on right
                minutes = float(minute_str)
                result = hours + (minutes / 60.0)
                return result

        # No separator — just hours
        result = float(duration_str)
        return result

    except Exception as e:
        print(f"Warning: Could not parse duration '{duration_str}': {e}")
        return 0


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def connect_access(db_path: str):
    """Open a read-only pyodbc connection to an MS Access database.

    Parameters
    ----------
    db_path : str
        Filesystem path to the ``.mdb`` or ``.accdb`` file.

    Returns
    -------
    pyodbc.Connection or None
        An open connection, or ``None`` if the connection failed.
    """
    try:
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={db_path};'
            r'ReadOnly=1;'
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        print(f"Error connecting to Access database {db_path!r}: {e}")
        return None


def connect_proces_db(path: str):
    """Open a read-only pyodbc connection to the ProcesGegevens Access database.

    Parameters
    ----------
    path : str
        Filesystem path to ``ProcesGegevens.accdb``.

    Returns
    -------
    pyodbc.Connection or None
    """
    conn = connect_access(path)
    if conn is None:
        print(f"Error connecting to ProcesGegevens database: {path!r}")
    return conn


def connect_storingen_iba(path: str):
    """Open a read-only pyodbc connection to the Storingen IBA Access database.

    Parameters
    ----------
    path : str
        Filesystem path to ``Storingen_IBA.accdb``.

    Returns
    -------
    pyodbc.Connection or None
    """
    conn = connect_access(path)
    if conn is None:
        print(f"Error connecting to Storingen IBA database: {path!r}")
    return conn


def connect_storingen_philips(path: str):
    """Open a read-only pyodbc connection to the Storingen Philips Access database.

    Parameters
    ----------
    path : str
        Filesystem path to ``Storingen_Philips.accdb``.

    Returns
    -------
    pyodbc.Connection or None
    """
    conn = connect_access(path)
    if conn is None:
        print(f"Error connecting to Storingen Philips database: {path!r}")
    return conn


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_gallium_data(conn, since_date=None) -> list:
    """Extract Gallium data from Access — using Targetstroom from Galliumbestralingen.

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.
    since_date : datetime.date, optional
        If given, only records with ``[EOB datum] >= since_date`` are returned.
        Pass ``None`` (default) for a full extraction.

    Returns
    -------
    list[dict]
        One dict per bestraling row.  Returns an empty list on error.
    """
    cursor = conn.cursor()

    try:
        query = f"""
            SELECT
                [EOB datum],
                [Targetstroom],
                [BO nummer],
                [Cyclotron],
                [Duur],
                [EOBhrmin],
                [Target nr + Opmerking],
                [IBA Bestralingspositie]
            FROM Galliumbestralingen
            {_date_filter(since_date, 'EOB datum')}
            ORDER BY [EOB datum] DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        gallium_data = []
        for row in rows:
            datum           = row[0]
            targetstroom    = row[1]
            bo_nummer       = row[2]
            cyclotron_col   = row[3] if row[3] else "Philips"
            duur            = row[4]
            eobhrmin        = row[5]
            opmerking       = row[6]
            iba_positie     = row[7] if len(row) > 7 else None

            # Combine Cyclotron (col 7) and IBA Bestralingspositie (col 9)
            if cyclotron_col == "Philips" or not iba_positie:
                cyclotron = "Philips"
            else:
                # IBA production — use the full position string (e.g. "IBA 2.1", "IBA 1.2")
                cyclotron = iba_positie

            # Targetstroom is already in µA
            gallium_data.append({
                'date':         datum,
                'targetstroom': targetstroom,
                'identifier':   bo_nummer,
                'cyclotron':    cyclotron,
                'duur':         duur,
                'eobhrmin':     eobhrmin,
                'opmerking':    opmerking,
            })

        return gallium_data

    except Exception as e:
        print(f"Error extracting Gallium data: {e}")
        return []


def _extract_opbrengsten(conn, table_name: str) -> list:
    """Extract opbrengsten (yield) data from the named Access table.

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.
    table_name : str
        The Access table to query (e.g. ``'Galliumopbrengsten'``).

    Returns
    -------
    list[dict]
        One dict per row with keys ``'date'`` and ``'opbrengst_mbq'``.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT [Datum Tweede Scheiding], [Opbrengst (MBq)]
            FROM {table_name}
            ORDER BY [Datum Tweede Scheiding] ASC
        """)
        result = []
        for row in cursor.fetchall():
            if row[0] is not None and row[1] is not None:
                result.append({'date': row[0], 'opbrengst_mbq': row[1]})
        return result
    except Exception as e:
        print(f"Error extracting {table_name} data: {e}")
        return []


def extract_gallium_opbrengsten_data(conn) -> list:
    """Extract Gallium opbrengsten (yield) data from Galliumopbrengsten.

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.

    Returns
    -------
    list[dict]
        One dict per row with keys ``'date'`` and ``'opbrengst_mbq'``.
    """
    return _extract_opbrengsten(conn, 'Galliumopbrengsten')


def extract_indium_opbrengsten_data(conn) -> list:
    """Extract Indium opbrengsten (yield) data from Indiumopbrengsten.

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.

    Returns
    -------
    list[dict]
        One dict per row with keys ``'date'`` and ``'opbrengst_mbq'``.
    """
    return _extract_opbrengsten(conn, 'Indiumopbrengsten')


def extract_rubidium_data(conn, since_date=None) -> list:
    """Extract Rubidium data from Access.

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.
    since_date : datetime.date, optional
        If given, only records with ``[EOB datum] >= since_date`` are returned.
        Pass ``None`` (default) for a full extraction.

    Returns
    -------
    list[dict]
        One dict per bestraling row.  Returns an empty list on error.
    """
    cursor = conn.cursor()

    try:
        query = f"""
            SELECT
                [EOB datum],
                [Activiteit MBq],
                [Benodigde activiteit volgens BO],
                [BO nummer],
                [stroom],
                [duur],
                [EOB tijd],
                [Opmerking]
            FROM Rubidiumbestralingen
            {_date_filter(since_date, 'EOB datum')}
            ORDER BY [EOB datum] DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        rubidium_data = []
        for row in rows:
            datum           = row[0]
            activiteit_mbq  = row[1]
            benodigde_mci   = row[2]
            bo_nummer       = row[3]
            stroom          = row[4]
            duur            = row[5]
            eob_tijd        = row[6]
            opmerking       = row[7]

            if benodigde_mci is not None and benodigde_mci != 0 and activiteit_mbq is not None:
                benodigde_mbq = benodigde_mci * 37
                efficiency = (activiteit_mbq / benodigde_mbq) * 100
            else:
                efficiency = None

            # Rubidium is ALWAYS produced on Kant 2 (side 2)
            cyclotron = 'P2'

            rubidium_data.append({
                'date':       datum,
                'value1':     activiteit_mbq,
                'value2':     benodigde_mci,
                'efficiency': efficiency,
                'identifier': bo_nummer,
                'cyclotron':  cyclotron,
                'stroom':     stroom,
                'duur':       duur,
                'eob_tijd':   eob_tijd,
                'opmerking':  opmerking,
            })

        return rubidium_data

    except Exception as e:
        print(f"Error extracting Rubidium data: {e}")
        return []


def extract_indium_data(conn, since_date=None) -> list:
    """Extract Indium data from Access — using Targetstroom from Indiumbestralingen.

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.
    since_date : datetime.date, optional
        If given, only records with ``[EOB datum] >= since_date`` are returned.
        Pass ``None`` (default) for a full extraction.

    Returns
    -------
    list[dict]
        One dict per bestraling row.  Returns an empty list on error.
    """
    cursor = conn.cursor()

    try:
        query = f"""
            SELECT
                [EOB datum],
                [Targetstroom],
                [BO nummer],
                [Bestralingspositie],
                [Duur],
                [EOBhrmin],
                [Opmerking]
            FROM Indiumbestralingen
            {_date_filter(since_date, 'EOB datum')}
            ORDER BY [EOB datum] DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        indium_data = []
        for row in rows:
            datum               = row[0]
            targetstroom        = row[1]
            bo_nummer           = row[2]
            bestralingspositie  = row[3] if row[3] else "Philips"
            duur                = row[4]
            eobhrmin            = row[5]
            opmerking           = row[6]

            # Keep the full bestralingspositie value (e.g. "IBA 2.1", "IBA 1.2", "Philips")
            # This will be parsed by map_cyclotron_name() during gantt conversion
            cyclotron = bestralingspositie

            # Targetstroom is already in µA
            indium_data.append({
                'date':                datum,
                'targetstroom':        targetstroom,
                'identifier':          bo_nummer,
                'cyclotron':           cyclotron,
                'bestralingspositie':  bestralingspositie,
                'duur':                duur,
                'eobhrmin':            eobhrmin,
                'opmerking':           opmerking,
            })

        return indium_data

    except Exception as e:
        print(f"Error extracting Indium data: {e}")
        return []


def extract_thallium_data(conn, since_date=None) -> list:
    """Extract Thallium data from Access — using Targetstroom from Thalliumbestralingen.

    Kant (cyclotron side) is derived from the first digit of the BO number:
    ``1`` → kant 1.2 (P1), ``2`` → kant 2.1 (P2), otherwise unknown (defaults P1).

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.
    since_date : datetime.date, optional
        If given, only records with ``[EOB datum] >= since_date`` are returned.
        Pass ``None`` (default) for a full extraction.

    Returns
    -------
    list[dict]
        One dict per bestraling row.  Returns an empty list on error.
    """
    cursor = conn.cursor()

    try:
        print("Using BO number first digit to determine kant (1→1.2, 2→2.1)")

        query = f"""
            SELECT
                [EOB datum],
                [Targetstroom],
                [BO nummer],
                [Duur],
                [EOB tijd],
                [Opmerking]
            FROM Thalliumbestralingen
            {_date_filter(since_date, 'EOB datum')}
            ORDER BY [EOB datum] DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        thallium_data = []
        for row in rows:
            datum        = row[0]
            targetstroom = row[1]
            bo_nummer    = row[2]
            duur         = row[3]
            eob_tijd     = row[4]
            opmerking    = row[5]

            # Determine kant from first digit of BO number (Thallium only)
            if bo_nummer is not None:
                bo_str = str(bo_nummer)
                if bo_str.startswith('1'):
                    kant      = '1.2'
                    cyclotron = 'P1'
                elif bo_str.startswith('2'):
                    kant      = '2.1'
                    cyclotron = 'P2'
                else:
                    kant      = 'Unknown'
                    cyclotron = 'P1'  # Default to P1 for unknown
            else:
                kant      = 'Unknown'
                cyclotron = 'P1'

            # Targetstroom is already in µA
            thallium_data.append({
                'date':         datum,
                'targetstroom': targetstroom,
                'identifier':   bo_nummer,
                'cyclotron':    cyclotron,
                'kant':         kant,
                'duur':         duur,
                'eob_tijd':     eob_tijd,
                'opmerking':    opmerking,
            })

        return thallium_data

    except Exception as e:
        print(f"Error extracting Thallium data: {e}")
        return []


def extract_iodine_data(conn, since_date=None) -> list:
    """Extract Iodine-123 data from Access.

    Computes ``yield_percent`` and ``output_percent`` from the raw measurement
    columns:

    * ``yield_percent  = Meting D1 / (Meting D1 + Meting Waste) × 100``
    * ``output_percent = (Meting D1 + Meting Waste) × 75 / verwacht opbrengst``

    Parameters
    ----------
    conn : pyodbc.Connection
        An open connection to the bestralingen Access database.
    since_date : datetime.date, optional
        If given, only records with ``[BO ingroei tot datum] >= since_date`` are
        returned.  Pass ``None`` (default) for a full extraction.

    Returns
    -------
    list[dict]
        One dict per production row.  Returns an empty list on error.
    """
    cursor = conn.cursor()

    try:
        query = f"""
            SELECT
                [BO ingroei tot datum],
                [*Meting D1 opbrengst I-123],
                [*Meting Waste],
                [*verwacht opbrengst I-123 bij 120 uAh],
                [BO nummer],
                [BO Targetstroom],
                [@Gemiddelde targetstroom],
                [@Totale dosis],
                [@Stop datum bestraling],
                [@Stop tijd bestraling],
                [BO starttijd bestraling],
                [@Totale bestralingstijd],
                [@Totale storingstijd],
                [@Opmerkingen tijdens bestraling]
            FROM [Iodine 123]
            {_date_filter(since_date, 'BO ingroei tot datum')}
            ORDER BY [BO ingroei tot datum] DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        iodine_data = []
        for row in rows:
            datum                   = row[0]
            meting_d1               = row[1]
            meting_waste            = row[2]
            verwacht                = row[3]
            bo_nummer               = row[4]
            bo_targetstroom         = row[5]
            targetstroom            = row[6]
            totale_dosis            = row[7]
            stop_datum              = row[8]
            stop_tijd               = row[9]
            start_tijd              = row[10]
            totale_bestralingstijd  = row[11]
            totale_storingstijd     = row[12]
            opmerking               = row[13]

            # Calculate Yield% = Meting D1 / (Meting D1 + Meting waste) × 100
            if meting_d1 is not None and meting_waste is not None and (meting_d1 + meting_waste) != 0:
                yield_percent = (meting_d1 / (meting_d1 + meting_waste)) * 100
            else:
                yield_percent = None

            # Calculate Output% = (Meting D1 + Meting waste) × 75 / verwacht opbrengst
            if (meting_d1 is not None and meting_waste is not None
                    and verwacht is not None and verwacht != 0):
                output_percent = ((meting_d1 + meting_waste) * 75) / verwacht
            else:
                output_percent = None

            # For backwards compatibility, keep old efficiency field (use yield%)
            efficiency_net = yield_percent

            # Iodine is ALWAYS produced on Kant 1 (side 1)
            cyclotron = 'P1'

            iodine_data.append({
                'date':                    datum,
                'value1':                  meting_d1,
                'value2':                  meting_waste,
                'efficiency':              efficiency_net,
                'yield_percent':           yield_percent,
                'output_percent':          output_percent,
                'identifier':              bo_nummer if bo_nummer is not None else 'TEST_NONE',
                'cyclotron':               cyclotron,
                'bo_targetstroom':         bo_targetstroom,
                'targetstroom':            targetstroom,
                'totale_dosis':            totale_dosis,
                'meting_d1':               meting_d1,
                'meting_waste':            meting_waste,
                'verwacht':                verwacht,
                'stop_datum':              stop_datum,
                'stop_tijd':               stop_tijd,
                'start_tijd':              start_tijd,
                'totale_bestralingstijd':  totale_bestralingstijd,
                'totale_storingstijd':     totale_storingstijd,
                'opmerking':               opmerking,
            })

        return iodine_data

    except Exception as e:
        print(f"Error extracting Iodine data: {e}")
        traceback.print_exc()
        return []


def extract_efficiency_data(proces_conn) -> list:
    """Extract efficiency targets from the ProcesGegevens database.

    Parameters
    ----------
    proces_conn : pyodbc.Connection
        An open connection to ``ProcesGegevens.accdb``.

    Returns
    -------
    list[dict]
        One dict per record with keys ``'date'`` and ``'efficiency'``.
        Zero-value efficiency rows are skipped.  Returns an empty list on error.
    """
    cursor = proces_conn.cursor()

    try:
        query = """
            SELECT [Datum], [Efficiency targets]
            FROM [Output_EfficiencyTargets]
            ORDER BY [Datum] DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        efficiency_data = []
        for row in rows:
            datum      = row[0]
            efficiency = row[1]

            # Skip zeros
            if efficiency is None or efficiency == 0:
                continue

            efficiency_data.append({
                'date':       datum,
                'efficiency': efficiency,
            })

        print(f"Extracted {len(efficiency_data)} efficiency records")
        return efficiency_data

    except Exception as e:
        print(f"Error extracting efficiency data: {e}")
        traceback.print_exc()
        return []


def extract_iba_storingen_data(storingen_conn) -> list:
    """Extract IBA storingen (malfunctions) data from the Storingen IBA database.

    Parameters
    ----------
    storingen_conn : pyodbc.Connection
        An open connection to ``Storingen_IBA.accdb``.

    Returns
    -------
    list[dict]
        One dict per storing with keys ``'storingsnummer'``, ``'datum'``,
        and ``'storing'``.  Returns an empty list if the connection is ``None``
        or on error.
    """
    if storingen_conn is None:
        print("No connection to Storingen IBA database")
        return []

    cursor = storingen_conn.cursor()

    try:
        query = """
            SELECT *
            FROM [001MTO Niet opgeloste storingen voor onderhoudsplanning]
            ORDER BY Datum DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        iba_storingen_data = []
        col_names = [desc[0].lower() for desc in cursor.description]
        print(f"  IBA storingen columns: {col_names}")
        for row in rows:
            row_dict = dict(zip(col_names, row))
            storingsnummer = next((row_dict[k] for k in col_names if 'storingsnummer' in k), row[0])
            datum_raw      = next((row_dict[k] for k in col_names if 'datum' in k), row[1])
            storing        = next((row_dict[k] for k in col_names if k == 'storing'), row[2])

            # Format date as YYYY-MM-DD
            if datum_raw:
                if isinstance(datum_raw, str):
                    datum_str = datum_raw
                else:
                    datum_str = datum_raw.strftime('%Y-%m-%d')
            else:
                datum_str = ''

            iba_storingen_data.append({
                'storingsnummer': storingsnummer,
                'datum':          datum_str,
                'storing':        storing,
            })

        print(f"Extracted {len(iba_storingen_data)} IBA storingen records")
        return iba_storingen_data

    except Exception as e:
        print(f"Error extracting IBA storingen data: {e}")
        traceback.print_exc()
        return []


def extract_philips_storingen_data(philips_conn) -> list:
    """Extract Philips storingen (malfunctions) data from the Storingen Philips database.

    Parameters
    ----------
    philips_conn : pyodbc.Connection
        An open connection to ``Storingen_Philips.accdb``.

    Returns
    -------
    list[dict]
        One dict per storing with keys ``'storingsnummer'``, ``'datum'``,
        and ``'storing'``.  Returns an empty list if the connection is ``None``
        or on error.
    """
    if philips_conn is None:
        print("No connection to Storingen Philips database")
        return []

    cursor = philips_conn.cursor()

    try:
        query = """
            SELECT
                Storingsnummer,
                Datum,
                Storing
            FROM [001MTO Niet opgeloste storingen voor onderhoudsplanning]
            ORDER BY Datum DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        philips_storingen_data = []
        for row in rows:
            storingsnummer = row[0]
            datum          = row[1]
            storing        = row[2]

            # Format date as YYYY-MM-DD
            if datum:
                if isinstance(datum, str):
                    datum_str = datum
                else:
                    datum_str = datum.strftime('%Y-%m-%d')
            else:
                datum_str = ''

            philips_storingen_data.append({
                'storingsnummer': storingsnummer,
                'datum':          datum_str,
                'storing':        storing,
            })

        print(f"Extracted {len(philips_storingen_data)} Philips storingen records")
        return philips_storingen_data

    except Exception as e:
        print(f"Error extracting Philips storingen data: {e}")
        traceback.print_exc()
        return []
