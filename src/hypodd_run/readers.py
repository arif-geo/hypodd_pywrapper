"""hypoDD fixed-format text -> the three tables. The inverse of `writers`.

Producers normally emit tables directly, so this is not on the main path. It exists for the two
cases where the text files came first:

  * an existing hypoDD dataset you want to re-run or re-analyse through this package
  * testing — `HypoDD-2.1b/examples/example2` is a real 308-event Calaveras dataset that hypoDD
    itself ships and validates against, which makes it the one fixture nobody can argue with

Both directions being present is also what makes a round-trip assertion possible: read a .pha
that hypoDD accepts, write it back, and require the bytes to match.
"""
from __future__ import annotations

import pandas as pd

EVENT_FIELDS = 14      # YR MO DY HR MN SC LAT LON DEP MAG EH EZ RMS ID


def read_pha(path):
    """hypoDD phase file -> (events, arrivals).

    `event_id` is the file's own cuspid as a string. Seconds are folded into the timestamp via
    a timedelta rather than the `second=` argument, because hypoDD phase files in the wild carry
    60.00 (and occasionally negative) seconds that `datetime` refuses outright.
    """
    events, arrivals = [], []
    eid = None
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            if line.lstrip().startswith('#'):
                p = line.lstrip()[1:].split()
                if len(p) < EVENT_FIELDS:
                    raise ValueError(f'{path}: event line has {len(p)} fields, '
                                     f'expected {EVENT_FIELDS}: {line.rstrip()!r}')
                eid = p[13]
                base = pd.Timestamp(year=int(p[0]), month=int(p[1]), day=int(p[2]),
                                    hour=int(p[3]), minute=int(p[4]), tz='UTC')
                events.append({
                    'event_id': eid,
                    'origin_time': base + pd.Timedelta(seconds=float(p[5])),
                    'latitude': float(p[6]), 'longitude': float(p[7]), 'depth': float(p[8]),
                    'magnitude': float(p[9]), 'eh': float(p[10]), 'ez': float(p[11]),
                    'rms': float(p[12]),
                })
            else:
                p = line.split()
                if len(p) < 4:
                    raise ValueError(f'{path}: phase line has {len(p)} fields, expected 4: '
                                     f'{line.rstrip()!r}')
                if eid is None:
                    raise ValueError(f'{path}: phase line before any event header')
                arrivals.append({'event_id': eid, 'station': p[0], 'phase': p[3].upper(),
                                 'travel_time': float(p[1]), 'weight': float(p[2])})
    return pd.DataFrame(events), pd.DataFrame(arrivals)


def read_station_dat(path):
    """STA LAT LON [ELV]. Elevation is optional in the wild — hypoDD defaults it to 0."""
    rows = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) < 3:
                continue
            rows.append({'station': p[0], 'latitude': float(p[1]), 'longitude': float(p[2]),
                         'elevation': float(p[3]) if len(p) > 3 else 0.0})
    return pd.DataFrame(rows)


def read_cc(path, fold_otc=True):
    """dt.cc -> (pairs, otc).

    hypoDD applies the header's origin-time correction itself, in getdata.f:

        dt_dt(i) = dt_dt(i) - otc

    With `fold_otc` (the default) that subtraction happens here instead, so `dt_sec` comes back
    ready for the pairs contract, which has no OTC column. Identical arithmetic — hypoDD then
    subtracts a zero — so nothing is lost and nothing is approximated. Producers that measure
    differential travel times directly from their own picks already have OTC = 0 and are
    unaffected.

    The raw per-pair values are returned either way, so a caller can see what a file carried.

    OTC = -999 is a sentinel meaning "no correction available"; hypoDD skips those pairs
    outright ("No OTC for ... Pair skiped"). They are dropped here for the same reason, rather
    than folded as if -999 were a measurement.
    """
    rows, otc = [], {}
    ev1 = ev2 = None
    for line in open(path):
        if line.lstrip().startswith('#'):
            p = line.lstrip()[1:].split()
            ev1, ev2 = p[0], p[1]
            otc[(ev1, ev2)] = float(p[2]) if len(p) > 2 else 0.0
        else:
            p = line.split()
            if len(p) < 4 or ev1 is None:
                continue
            rows.append({'ev1': ev1, 'ev2': ev2, 'station': p[0], 'phase': p[3].upper(),
                         'dt_sec': float(p[1]), 'weight': float(p[2])})
    df = pd.DataFrame(rows)
    if df.empty:
        return df, otc

    idx = pd.MultiIndex.from_frame(df[['ev1', 'ev2']])
    skip = {k for k, v in otc.items() if abs(v + 999) < 0.001}
    if skip:
        df = df[~idx.isin(skip)].reset_index(drop=True)
        idx = pd.MultiIndex.from_frame(df[['ev1', 'ev2']])
    if fold_otc:
        df['dt_sec'] = df.dt_sec - pd.Series(idx.map(otc), index=df.index).fillna(0.0)
    return df, otc
