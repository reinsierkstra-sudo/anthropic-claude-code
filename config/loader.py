"""
config/loader.py
----------------
Central configuration loader.  Reads config/settings.yaml and exposes
helper functions that return the same data structures the rest of the
codebase already expects (e.g. SPEC_SETTINGS, DEFAULT_PATHS).
"""

import os
import yaml

# Path to the YAML file, resolved relative to this file's location so the
# module works regardless of the current working directory.
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'settings.yaml')


def load_settings(config_path: str = _CONFIG_PATH) -> dict:
    """Load and return the full settings dict from settings.yaml.

    Parameters
    ----------
    config_path : str, optional
        Absolute or relative path to the YAML file.  Defaults to the
        ``settings.yaml`` file that lives alongside this module.

    Returns
    -------
    dict
        The parsed YAML document as a plain Python dict.
    """
    with open(config_path, 'r', encoding='utf-8') as fh:
        return yaml.safe_load(fh)


def get_spec_settings(cfg: dict) -> dict:
    """Convert ``cfg['spec']`` into the nested dict structure used by the
    dashboard rendering code (identical layout to the old ``SPEC_SETTINGS``
    module-level constant).

    Parameters
    ----------
    cfg : dict
        The full settings dict returned by :func:`load_settings`.

    Returns
    -------
    dict
        Spec settings keyed by isotope name (``'gallium'``, ``'rubidium'``,
        ``'indium'``, ``'thallium'``, ``'iodine'``).
    """
    return cfg['spec']


def get_paths(cfg: dict) -> dict:
    """Return the ``paths`` section of the settings dict.

    Parameters
    ----------
    cfg : dict
        The full settings dict returned by :func:`load_settings`.

    Returns
    -------
    dict
        A flat mapping of logical path names to filesystem paths (strings).
    """
    return cfg['paths']
