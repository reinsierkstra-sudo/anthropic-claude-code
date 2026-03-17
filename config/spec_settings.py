"""
config/spec_settings.py
-----------------------
Canonical within-spec thresholds for all five isotopes, plus the
colour-coding helpers used by the renderer.

Importing this module instead of gallium_extractor guarantees that
threshold changes only need to be made in one place.
"""

# ============================================================================
# WITHIN-SPEC SETTINGS
# ============================================================================

SPEC_SETTINGS = {
    'gallium': {
        'metric': 'targetstroom',
        'unit': 'µA',
        'philips': {'min': 75,  'max': 85},
        'iba':     {'min': 130, 'max': 140},
    },
    'rubidium': {
        'metric': 'efficiency',
        'unit': '%',
        'min': 95,
        'max': 105,
    },
    'indium': {
        'metric': 'targetstroom',
        'unit': 'µA',
        'philips': {'min': 75,  'max': 85},
        'iba':     {'min': 130, 'max': 140},
    },
    'thallium': {
        'metric': 'targetstroom',
        'unit': 'µA',
        'min': 166,
        'max': 174,
    },
    'iodine': {
        'within_spec': {
            'output': {
                'metric': 'output_percent',
                'unit': '%',
                'min': 78,
                'max': 114.9,
            },
            'targetstroom': {
                'metric': 'targetstroom',
                'unit': 'µA',
                'min': 96,
                'max': 124,
            },
        },
        'chart_colors': {
            'yield': {
                'metric': 'yield_percent',
                'unit': '%',
                'min': 80,
                'max': None,
            },
        },
    },
}

# ============================================================================
# Colour helpers (mirror the @staticmethod helpers on IsotopeDashboardGenerator)
# ============================================================================

def get_targetstroom_color(targetstroom, isotope_type, cyclotron=None) -> str:
    if targetstroom is None:
        return '#000000'
    ts = round(targetstroom)
    if isotope_type == 'thallium':
        spec = SPEC_SETTINGS['thallium']
    elif isotope_type in ('gallium', 'indium'):
        key = 'iba' if (cyclotron and str(cyclotron).upper().startswith('IBA')) else 'philips'
        spec = SPEC_SETTINGS[isotope_type][key]
    else:
        return '#000000'
    return '#3BB143' if spec['min'] <= ts <= spec['max'] else '#FF2400'


def get_efficiency_color(efficiency) -> str:
    if efficiency is None:
        return '#000000'
    spec = SPEC_SETTINGS['rubidium']
    return '#3BB143' if spec['min'] <= round(efficiency) <= spec['max'] else '#FF2400'


def get_rb_stroom_color(stroom) -> str:
    return '#3BB143' if stroom is not None and 67 <= stroom <= 72 else '#FF2400'


def get_iodine_yield_color(yield_percent) -> str:
    if yield_percent is None:
        return '#000000'
    threshold = SPEC_SETTINGS['iodine']['chart_colors']['yield']['min']
    return '#3BB143' if yield_percent >= threshold else '#FF2400'


def get_iodine_output_color(output_percent) -> str:
    if output_percent is None:
        return '#000000'
    spec = SPEC_SETTINGS['iodine']['within_spec']['output']
    return '#3BB143' if spec['min'] <= output_percent <= spec['max'] else '#FF2400'


def get_iodine_targetstroom_color(targetstroom) -> str:
    if targetstroom is None:
        return '#000000'
    spec = SPEC_SETTINGS['iodine']['within_spec']['targetstroom']
    return '#3BB143' if spec['min'] <= targetstroom <= spec['max'] else '#FF2400'


def get_iodine_color(record) -> str:
    output      = record.get('output_percent')
    yield_pct   = record.get('yield_percent')
    targetstroom = record.get('targetstroom')
    spec         = SPEC_SETTINGS['iodine']['within_spec']
    output_ok    = (spec['output']['min'] <= output <= spec['output']['max']
                    if output is not None else False)
    ts_spec      = spec['targetstroom']
    ts_ok        = (ts_spec['min'] <= targetstroom <= ts_spec['max']
                    if targetstroom is not None else False)
    yield_good   = (yield_pct >= SPEC_SETTINGS['iodine']['chart_colors']['yield']['min']
                    if yield_pct is not None else False)
    if output_ok and ts_ok:
        return '#3BB143' if yield_good else '#FFA500'
    return '#FF2400'


def get_ploeg_color(value, average) -> str:
    if abs(value - average) <= 2.0:
        return '#000000'
    return '#3BB143' if value > average else '#FF2400'


def is_production_in_spec(production: dict, isotope_type: str) -> bool:
    """Return True when *production* passes the within-spec criteria."""
    if isotope_type in ('gallium', 'indium'):
        ts = production.get('targetstroom')
        if ts is None:
            return False
        cyclotron = production.get('cyclotron', 'Philips')
        key = 'iba' if str(cyclotron).upper().startswith('IBA') else 'philips'
        spec = SPEC_SETTINGS[isotope_type][key]
        return spec['min'] <= round(ts) <= spec['max']

    if isotope_type == 'rubidium':
        eff = production.get('efficiency')
        if eff is None:
            return False
        spec = SPEC_SETTINGS['rubidium']
        return spec['min'] <= round(eff) <= spec['max']

    if isotope_type == 'thallium':
        ts = production.get('targetstroom')
        if ts is None:
            return False
        spec = SPEC_SETTINGS['thallium']
        return spec['min'] <= round(ts) <= spec['max']

    if isotope_type == 'iodine':
        output = production.get('output_percent')
        ts     = production.get('targetstroom')
        if output is None or ts is None:
            return False
        out_spec = SPEC_SETTINGS['iodine']['within_spec']['output']
        ts_spec  = SPEC_SETTINGS['iodine']['within_spec']['targetstroom']
        return (out_spec['min'] <= output <= out_spec['max'] and
                ts_spec['min'] <= ts     <= ts_spec['max'])

    return False
