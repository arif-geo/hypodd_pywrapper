"""Tables -> hypoDD fixed-format text, and .reloc -> table.

The only translation that legitimately lives here is the synthetic integer ID: hypoDD's formats
demand integer cuspids, which is a fact about hypoDD, not about the science. Producers keep
their own event_id strings; the mapping is written alongside so results can be joined back.
"""
from __future__ import annotations

import os
import pandas as pd

ID_START = 100000


def assign_ids(events, path=None):
    """event_id (str) -> synthetic int. Stable: sorted by origin_time then event_id."""
    ordered = events.sort_values(['origin_time', 'event_id'])
    mapping = pd.DataFrame({
        'event_id': ordered.event_id.values,
        'hypodd_id': range(ID_START, ID_START + len(ordered)),
    })
    if path:
        mapping.to_csv(path, index=False)
    return dict(zip(mapping.event_id, mapping.hypodd_id))


def write_station_dat(stations, path):
    """STA LAT LON ELV"""
    with open(path, 'w') as f:
        for r in stations.itertuples():
            f.write(f'{r.station:7s} {r.latitude:9.5f} {r.longitude:10.5f} {r.elevation:6.1f}\n')
    return len(stations)


def write_pha(events, arrivals, ids, path):
    """hypoDD phase format.

        # YR MO DY HR MN SC LAT LON DEP MAG EH EZ RMS ID
        STA TT WGHT PHA

    Field widths follow ncsn2pha.f, matching what ph2dt's reader expects.
    """
    by_event = {k: v for k, v in arrivals.groupby('event_id')}
    n_ev = n_ph = 0
    with open(path, 'w') as f:
        for ev in events.sort_values(['origin_time', 'event_id']).itertuples():
            picks = by_event.get(ev.event_id)
            if picks is None or picks.empty:
                continue
            t = ev.origin_time
            sec = t.second + t.microsecond / 1e6
            f.write(f'#{t.year:5d} {t.month:2d} {t.day:2d} {t.hour:2d} {t.minute:2d} {sec:5.2f} '
                    f'{ev.latitude:8.4f} {ev.longitude:9.4f} {ev.depth:7.2f}'
                    f'{ev.magnitude:6.2f}{ev.eh:6.2f}{ev.ez:6.2f}{ev.rms:6.2f} '
                    f'{ids[ev.event_id]:10d}\n')
            n_ev += 1
            for p in picks.itertuples():
                f.write(f'{p.station:7s} {p.travel_time:8.3f} {p.weight:6.3f} {p.phase}\n')
                n_ph += 1
    return n_ev, n_ph


def write_cc(pairs, ids, path, otc=0.0):
    """hypoDD cross-correlation differential-time format.

        # ID1 ID2 OTC
        STA DT WGHT PHA

    DT is a differential TIME in seconds. WGHT is where a correlation coefficient goes.
    """
    df = pairs.copy()
    df['id1'] = df.ev1.map(ids)
    df['id2'] = df.ev2.map(ids)
    df = df.dropna(subset=['id1', 'id2'])
    df['id1'] = df.id1.astype(int)
    df['id2'] = df.id2.astype(int)
    df = df.sort_values(['id1', 'id2'], kind='stable')

    n_pair = 0
    with open(path, 'w') as f:
        buf = []
        prev = None
        for r in df.itertuples():
            key = (r.id1, r.id2)
            if key != prev:
                buf.append(f'# {r.id1:d} {r.id2:d} {otc:.6f}\n')
                prev = key
                n_pair += 1
            buf.append(f'{r.station:7s} {r.dt_sec:9.6f} {r.weight:5.3f} {r.phase}\n')
            if len(buf) > 1_000_000:
                f.write(''.join(buf))
                buf.clear()
        if buf:
            f.write(''.join(buf))
    return n_pair, len(df)


RELOC_COLUMNS = ['hypodd_id', 'latitude', 'longitude', 'depth', 'x_m', 'y_m', 'z_m',
                 'ex_m', 'ey_m', 'ez_m', 'year', 'month', 'day', 'hour', 'minute', 'second',
                 'magnitude', 'n_cc_p', 'n_cc_s', 'n_cat_p', 'n_cat_s', 'rms_cc', 'rms_cat',
                 'cluster_id']


def read_reloc(path, ids=None):
    """hypoDD.reloc -> DataFrame, with event_id joined back when `ids` is given.

    Lines containing '*' or 'NaN' are events hypoDD could not constrain; they are dropped and
    counted rather than silently coerced.
    """
    rows, skipped = [], 0
    with open(path) as f:
        for line in f:
            if '*' in line or 'NaN' in line:
                skipped += 1
                continue
            parts = line.split()
            if len(parts) < len(RELOC_COLUMNS):
                continue
            try:
                rows.append([float(x) for x in parts[:len(RELOC_COLUMNS)]])
            except ValueError:
                skipped += 1
    df = pd.DataFrame(rows, columns=RELOC_COLUMNS)
    if df.empty:
        return df, skipped
    for c in ('hypodd_id', 'year', 'month', 'day', 'hour', 'minute',
              'n_cc_p', 'n_cc_s', 'n_cat_p', 'n_cat_s', 'cluster_id'):
        df[c] = df[c].astype(int)
    if ids:
        rev = {v: k for k, v in ids.items()}
        df.insert(0, 'event_id', df.hypodd_id.map(rev))
    df['origin_time'] = pd.to_datetime(
        df[['year', 'month', 'day', 'hour', 'minute']].assign(second=df.second.astype(int)),
        utc=True, errors='coerce')
    return df, skipped
