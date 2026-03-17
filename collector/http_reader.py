"""
collector/http_reader.py
------------------------
Fetches cyclotron production data over HTTP.

Provides
--------
- ``fetch_cyclotron_data(url)`` — loads from the JSON database first, falls
  back to the live URL.
- ``parse_cyclotron_data(html_content)`` — parses the raw HTML table into a
  list of production dicts.
"""

import json
import os
import warnings

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

# Path to the JSON database maintained by Productieplanning.py
_PRODUCTIONS_DATABASE = (
    r"\\pett-fs01p\nucleair\Isotopen productie"
    r"\Cyclotron formulieren\productions_database.json"
)


def fetch_cyclotron_data(url: str) -> list:
    """Fetch cyclotron production data — JSON database first, live URL as fallback.

    Attempts to load data from the shared JSON database maintained by
    ``Productieplanning.py``.  If that file is absent or unreadable the
    function falls back to a live HTTP GET against *url* and delegates
    parsing to :func:`parse_cyclotron_data`.

    Parameters
    ----------
    url : str
        The URL of the cyclotron ASP page (e.g.
        ``http://pett-webw02p/procdashboard/cyclotron.asp``).

    Returns
    -------
    list[dict]
        A deduplicated list of production dicts (see
        :func:`parse_cyclotron_data` for the dict shape).  Returns ``[]`` if
        both sources fail.
    """
    # Try loading from JSON database first (maintained by Productieplanning.py)
    try:
        if os.path.exists(_PRODUCTIONS_DATABASE):
            with open(_PRODUCTIONS_DATABASE, 'r', encoding='utf-8') as f:
                database = json.load(f)
                productions = database.get('productions', {})

                if productions:
                    data = list(productions.values())
                    print(f"Fetched cyclotron production data from JSON database ({len(data)} entries)")
                    return data
    except Exception as e:
        print(f"[WARNING] Could not load from JSON database: {e}")

    # Fallback: Try fetching from URL
    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        html_content = response.text
        data = parse_cyclotron_data(html_content)
        print(f"Fetched cyclotron production data from URL ({len(data)} entries)")
        return data
    except Exception as e:
        print(f"[WARNING] Could not fetch cyclotron data from URL: {e}")
        return []


def parse_cyclotron_data(html_content: str) -> list:
    """Parse a cyclotron HTML page into a list of structured production dicts.

    Locates the ``<table id="custom_table">`` element and iterates its rows,
    extracting data rows (identified by a leading P1/P2/P0 cell) while
    skipping header rows and info-only rows that carry a ``colspan`` attribute.

    After collection the results are deduplicated by ``bonr``.

    Parameters
    ----------
    html_content : str
        The full HTML source of the cyclotron planning page.

    Returns
    -------
    list[dict]
        Each dict contains the keys: ``cyclotron``, ``bonr``, ``order``,
        ``product``, ``startDate``, ``startTime``, ``endDate``, ``endTime``,
        ``duration``, ``activity``, ``totalActivity``, ``type``.
        ``type`` is ``'Pauze'`` when the product name contains ``'Pauze'``,
        otherwise ``'Data'``.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'custom_table'})

    if not table:
        return []

    rows = table.find_all('tr')
    all_data = []

    for row in rows:
        cells = row.find_all(['td', 'th'])

        if len(cells) == 0:
            continue

        # Skip header rows
        if len(cells) == 3 and all(
            c.get_text(strip=True) in ['P1', 'P2', 'P0']
            for c in cells if c.get_text(strip=True)
        ):
            continue

        if cells[0].name == 'th' and cells[0].get_text(strip=True) == 'Cyclotron':
            continue

        i = 0
        while i < len(cells):
            cell = cells[i]

            if cell.has_attr('colspan') and cell.get_text(strip=True) == '':
                i += 1
                continue

            cyclotron = cell.get_text(strip=True)

            if cyclotron in ['P1', 'P2', 'P0']:
                remaining_cells = cells[i:]

                # Info row (skip these for gantt chart)
                if len(remaining_cells) > 1 and remaining_cells[1].has_attr('colspan'):
                    colspan = int(remaining_cells[1].get('colspan', '1'))
                    i += 1 + colspan
                    continue

                # Data row
                if len(remaining_cells) >= 11:
                    product  = remaining_cells[3].get_text(strip=True)
                    row_data = {
                        'cyclotron':     cyclotron,
                        'bonr':          remaining_cells[1].get_text(strip=True),
                        'order':         remaining_cells[2].get_text(strip=True),
                        'product':       product,
                        'startDate':     remaining_cells[4].get_text(strip=True),
                        'startTime':     remaining_cells[5].get_text(strip=True),
                        'endDate':       remaining_cells[6].get_text(strip=True),
                        'endTime':       remaining_cells[7].get_text(strip=True),
                        'duration':      remaining_cells[8].get_text(strip=True),
                        'activity':      remaining_cells[9].get_text(strip=True),
                        'totalActivity': remaining_cells[10].get_text(strip=True),
                        'type':          'Pauze' if 'Pauze' in product else 'Data',
                    }

                    all_data.append(row_data)
                    i += 11
                    break
                else:
                    i += 1
            else:
                i += 1

    # Deduplicate by BOnr
    seen_bonr   = set()
    deduplicated = []
    for item in all_data:
        if (item.get('bonr') and item['bonr'] not in seen_bonr
                and item['type'] in ['Data', 'Pauze']):
            seen_bonr.add(item['bonr'])
            deduplicated.append(item)

    return deduplicated
