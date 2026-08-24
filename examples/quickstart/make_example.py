#!/usr/bin/env python
"""Regenerate examples/quickstart/tables/ from hypoDD's own bundled Calaveras dataset.

The committed tables are the output of this script. It exists so the example data has visible
provenance instead of being four mystery CSVs: everything here comes from
`HypoDD-2.1b/examples/example2`, which hypoDD distributes and validates against.

The subset is chosen by CC connectivity, not at random. hypoDD relocates events relative to
their neighbours, so an arbitrary sample would be a set of poorly linked events that ph2dt
mostly discards — a technically valid example that demonstrates failure.

    python examples/quickstart/make_example.py [--events 40]
"""
import argparse
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from hypodd_run import readers          # noqa: E402

SOURCE = os.path.join(ROOT, 'HypoDD-2.1b', 'examples', 'example2')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', type=int, default=40)
    ap.add_argument('--out', default=os.path.join(HERE, 'tables'))
    a = ap.parse_args()

    if not os.path.exists(os.path.join(SOURCE, 'Calaveras.pha')):
        raise SystemExit(f'source dataset not found: {SOURCE}')
    os.makedirs(a.out, exist_ok=True)

    events, arrivals = readers.read_pha(os.path.join(SOURCE, 'Calaveras.pha'))
    stations = readers.read_station_dat(os.path.join(SOURCE, 'station.dat'))
    pairs, _ = readers.read_cc(os.path.join(SOURCE, 'dt.cc'))   # OTC folded into dt_sec

    # Rank by how often an event appears in the CC set, then keep only pairs internal to the
    # subset. Taking the top-N directly would still leave many with no surviving partner.
    rank = Counter(pairs.ev1) + Counter(pairs.ev2)
    keep = {e for e, _ in rank.most_common(a.events)} & set(events.event_id)

    events = events[events.event_id.isin(keep)].sort_values('event_id')
    arrivals = arrivals[arrivals.event_id.isin(keep)].sort_values(['event_id', 'station', 'phase'])
    # Calaveras' station.dat does not cover every station in its .pha. ph2dt drops those
    # arrivals silently, so drop them here instead — a producer should not hand the wrapper
    # observations it already knows are unusable.
    arrivals = arrivals[arrivals.station.isin(set(stations.station))]
    pairs = pairs[pairs.ev1.isin(keep) & pairs.ev2.isin(keep)].sort_values(['ev1', 'ev2'])
    stations = stations[stations.station.isin(set(arrivals.station))].sort_values('station')

    for name, df in (('events', events), ('arrivals', arrivals),
                     ('pairs', pairs), ('stations', stations)):
        p = os.path.join(a.out, f'{name}.csv')
        df.to_csv(p, index=False)
        print(f'  {name + ".csv":16s} {len(df):>7,} rows   {os.path.getsize(p) / 1024:>6.0f} KB')

    n_pair = pairs.groupby(['ev1', 'ev2']).ngroups
    print(f'\n{len(events)} events, {n_pair:,} linked pairs, {len(stations)} stations -> {a.out}')


if __name__ == '__main__':
    main()
