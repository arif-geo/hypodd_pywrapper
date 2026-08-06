"""The three-table input contract, and its validation.

Producers emit these; nothing here knows what a template or a daughter detection is.

    events.csv    event_id, origin_time, latitude, longitude, depth[, magnitude, eh, ez, rms]
    arrivals.csv  event_id, station, phase, travel_time[, weight]
    pairs.csv     ev1, ev2, station, phase, dt_sec[, weight]        (optional -> dt.cc)

`arrivals` is LONG form — one row per event/station/phase. The old wide form
(`travel_time_p` + `travel_time_s` on one row) forced every phase into a P/S pair and made an
S-only station awkward; long form handles P-only, S-only, and any future phase identically.

Validation is strict on purpose. The predecessor silently substituted hardcoded coordinates
(40.5, -124.0) for events it could not resolve, which relocates an event from a fabricated
starting point and reports success. Here a missing location is an error.
"""
from __future__ import annotations

import pandas as pd

EVENT_REQUIRED = ['event_id', 'origin_time', 'latitude', 'longitude', 'depth']
EVENT_OPTIONAL = {'magnitude': 0.0, 'eh': 0.0, 'ez': 0.0, 'rms': 0.0}
ARRIVAL_REQUIRED = ['event_id', 'station', 'phase', 'travel_time']
PAIR_REQUIRED = ['ev1', 'ev2', 'station', 'phase', 'dt_sec']

VALID_PHASES = {'P', 'S'}


class ContractError(ValueError):
    """Raised when an input table violates the contract. Never silently repaired."""


def _require_columns(df, required, name):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ContractError(f'{name}: missing required column(s) {missing}. '
                            f'Got: {list(df.columns)}')


def load_events(path):
    """One row per event. event_id is the producer's own identifier (string, any format)."""
    df = pd.read_csv(path, dtype={'event_id': str})
    _require_columns(df, EVENT_REQUIRED, 'events')

    dup = df.event_id.duplicated()
    if dup.any():
        raise ContractError(f'events: {dup.sum()} duplicate event_id '
                            f'(first: {df.loc[dup, "event_id"].iloc[0]})')

    df['origin_time'] = pd.to_datetime(df['origin_time'], format='mixed', utc=True,
                                       errors='coerce')
    bad = df['origin_time'].isna()
    if bad.any():
        raise ContractError(f'events: {bad.sum()} unparseable origin_time '
                            f'(first event_id: {df.loc[bad, "event_id"].iloc[0]})')

    for c in ('latitude', 'longitude', 'depth'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
        bad = df[c].isna()
        if bad.any():
            raise ContractError(
                f'events: {bad.sum()} rows with missing/non-numeric {c} '
                f'(first event_id: {df.loc[bad, "event_id"].iloc[0]}). '
                f'Fix this in the producer — a fabricated location silently corrupts the run.')

    for c, default in EVENT_OPTIONAL.items():
        if c not in df.columns:
            df[c] = default
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(default)
    return df


def load_arrivals(path, events=None):
    """Long form: one row per event/station/phase. `weight` defaults to 1.0."""
    df = pd.read_csv(path, dtype={'event_id': str, 'station': str, 'phase': str})
    _require_columns(df, ARRIVAL_REQUIRED, 'arrivals')

    df['phase'] = df['phase'].str.strip().str.upper()
    bad = ~df.phase.isin(VALID_PHASES)
    if bad.any():
        raise ContractError(f'arrivals: {bad.sum()} rows with phase not in {sorted(VALID_PHASES)} '
                            f'(saw: {sorted(df.loc[bad, "phase"].unique())[:5]})')

    df['travel_time'] = pd.to_numeric(df['travel_time'], errors='coerce')
    bad = df.travel_time.isna() | (df.travel_time <= 0)
    if bad.any():
        raise ContractError(
            f'arrivals: {bad.sum()} rows with non-positive or missing travel_time. '
            f'A pick preceding its own origin time poisons ph2dt silently.')

    dup = df.duplicated(subset=['event_id', 'station', 'phase'])
    if dup.any():
        raise ContractError(f'arrivals: {dup.sum()} duplicate event_id+station+phase. '
                            f'hypoDD would treat these as independent observations.')

    if 'weight' not in df.columns:
        df['weight'] = 1.0
    df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(1.0)

    if events is not None:
        known = set(events.event_id)
        orphan = ~df.event_id.isin(known)
        if orphan.any():
            raise ContractError(f'arrivals: {orphan.sum()} rows reference event_id absent from '
                                f'events (first: {df.loc[orphan, "event_id"].iloc[0]})')
    return df


def load_pairs(path, events=None):
    """Differential times measured between event pairs -> dt.cc.

    NOTE the payload is `dt_sec`, a TIME. If these came from cross-correlation, the correlation
    coefficient belongs in `weight`, not in dt_sec.
    """
    df = pd.read_csv(path, dtype={'ev1': str, 'ev2': str, 'station': str, 'phase': str})
    _require_columns(df, PAIR_REQUIRED, 'pairs')

    df['phase'] = df['phase'].str.strip().str.upper()
    bad = ~df.phase.isin(VALID_PHASES)
    if bad.any():
        raise ContractError(f'pairs: {bad.sum()} rows with phase not in {sorted(VALID_PHASES)}')

    df['dt_sec'] = pd.to_numeric(df['dt_sec'], errors='coerce')
    bad = df.dt_sec.isna()
    if bad.any():
        raise ContractError(f'pairs: {bad.sum()} rows with missing dt_sec')

    self_pair = df.ev1 == df.ev2
    if self_pair.any():
        raise ContractError(
            f'pairs: {self_pair.sum()} self-pairs (ev1 == ev2). An event differenced against '
            f'itself carries no information; this usually means the producer paired on the '
            f'wrong key.')

    if 'weight' not in df.columns:
        df['weight'] = 1.0
    df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(1.0)

    if events is not None:
        known = set(events.event_id)
        orphan = ~(df.ev1.isin(known) & df.ev2.isin(known))
        if orphan.any():
            raise ContractError(f'pairs: {orphan.sum()} rows reference an event_id absent from '
                                f'events')
    return df


def load_stations(path):
    """station, latitude, longitude[, elevation]. Extra columns are ignored."""
    df = pd.read_csv(path)
    _require_columns(df, ['station', 'latitude', 'longitude'], 'stations')
    if 'elevation' not in df.columns:
        df['elevation'] = 0.0
    dup = df.station.duplicated()
    if dup.any():
        raise ContractError(f'stations: {dup.sum()} duplicate station code '
                            f'(first: {df.loc[dup, "station"].iloc[0]}). Resolve location codes '
                            f'in the producer.')
    return df


def summarise(events, arrivals, pairs=None):
    """One-line-per-table summary, printed by `validate`."""
    out = [f'events   : {len(events):>9,}',
           f'arrivals : {len(arrivals):>9,}  '
           f'({(arrivals.phase == "P").sum():,} P / {(arrivals.phase == "S").sum():,} S) '
           f'across {arrivals.station.nunique()} stations']
    if pairs is not None:
        n_pair = pairs.groupby(['ev1', 'ev2']).ngroups
        out.append(f'pairs    : {len(pairs):>9,}  over {n_pair:,} event pairs')
    return '\n'.join(out)
