"""
collector/html_reader.py
------------------------
Reads local HTML files from disk for embedding in dashboard modals.

Provides
--------
- ``load_planning_html(path)`` — reads ``planning.html``.
- ``load_productieschema_html(path)`` — reads the productieschema HTML file.
"""


def load_planning_html(path: str):
    """Read *planning.html* from disk and return its contents as a string.

    Parameters
    ----------
    path : str
        Filesystem path to ``planning.html``.

    Returns
    -------
    str or None
        The full file contents, or ``None`` if *path* is falsy, the file is
        not found, or any other read error occurs.
    """
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        print(f"Loaded planning.html ({len(content):,} chars)")
        return content
    except FileNotFoundError:
        print(f"Warning: planning.html not found at {path}")
        return None
    except Exception as e:
        print(f"Warning: Could not read planning.html: {e}")
        return None


def load_productieschema_html(path: str):
    """Read the productieschema HTML file from disk and return its contents.

    Parameters
    ----------
    path : str
        Filesystem path to the productieschema HTML file.

    Returns
    -------
    str or None
        The full file contents, or ``None`` if *path* is falsy, the file is
        not found, or any other read error occurs.
    """
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        print(f"Loaded productieschema HTML ({len(content):,} chars)")
        return content
    except FileNotFoundError:
        print(f"Warning: productieschema HTML not found at {path}")
        return None
    except Exception as e:
        print(f"Warning: Could not read productieschema HTML: {e}")
        return None
