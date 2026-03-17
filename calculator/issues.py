"""
calculator/issues.py
---------------------
Standalone functions for reading issue / comment counts from the SQLite database.

The production_comments table records operator-entered comments for each
production batch, categorised by comment_type and isotope_type.
"""

from datetime import datetime, timedelta, date


def _get_last_friday():
    """Return the date of the most recent past Friday (not today if today is Friday)."""
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0:
        days_since_friday = 7
    return today - timedelta(days=days_since_friday)


def get_issue_counts(sqlite_conn):
    """Return counts of each comment_type from the production_comments table.

    Splits results into three windows:
      - this_week  : from last Friday through today
      - last_week  : from the Friday before last through last Thursday
      - all_time   : every non-empty comment_type in the table

    Args:
        sqlite_conn: An open sqlite3 connection.

    Returns:
        dict with keys 'this_week', 'last_week', 'all_time', each mapping
        comment_type strings to integer counts.
    """
    if not sqlite_conn:
        return {'this_week': {}, 'last_week': {}, 'all_time': {}}

    cursor = sqlite_conn.cursor()

    last_friday = _get_last_friday()
    previous_friday = last_friday - timedelta(days=7)
    last_thursday = last_friday - timedelta(days=1)
    today = datetime.now().date()

    # This week
    cursor.execute(
        '''
        SELECT comment_type, COUNT(*) as count
        FROM production_comments
        WHERE production_date >= ? AND production_date <= ?
        GROUP BY comment_type
        ''',
        (last_friday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
    )
    this_week = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

    # Last week
    cursor.execute(
        '''
        SELECT comment_type, COUNT(*) as count
        FROM production_comments
        WHERE production_date >= ? AND production_date <= ?
        GROUP BY comment_type
        ''',
        (previous_friday.strftime('%Y-%m-%d'), last_thursday.strftime('%Y-%m-%d'))
    )
    last_week = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

    # All time
    cursor.execute(
        '''
        SELECT comment_type, COUNT(*) as count
        FROM production_comments
        WHERE comment_type IS NOT NULL AND comment_type != ''
        GROUP BY comment_type
        '''
    )
    all_time = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

    return {
        'this_week': this_week,
        'last_week': last_week,
        'all_time': all_time
    }


def get_isotope_issue_counts(sqlite_conn):
    """Return the total number of non-empty comments per isotope_type.

    Args:
        sqlite_conn: An open sqlite3 connection.

    Returns:
        dict mapping isotope_type strings to integer counts,
        or an empty dict when no connection is provided.
    """
    if not sqlite_conn:
        return {}

    cursor = sqlite_conn.cursor()

    cursor.execute(
        '''
        SELECT isotope_type, COUNT(*) as count
        FROM production_comments
        WHERE comment_type IS NOT NULL AND comment_type != ''
        GROUP BY isotope_type
        '''
    )

    return {row[0]: row[1] for row in cursor.fetchall()}
