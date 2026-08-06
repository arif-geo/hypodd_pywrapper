"""Tests against hypoDD's own bundled Calaveras dataset (`HypoDD-2.1b/examples/example2`).

308 events, 13,769 arrivals, 1,961 stations — shipped and validated by hypoDD itself, and about
as far from this project's seismology as it is possible to get, which is the point: a
domain-agnostic tool should be tested on data it knows nothing about.

Two levels:

  * `test_pha_round_trip` — read a .pha hypoDD accepts, write it back, require every value to
    survive. No binaries, milliseconds. Field WIDTHS are not asserted: the example came from
    `ncsn2pha` and pads differently to `write_pha`, but ph2dt reads both (list-directed Fortran
    input ignores column positions), so pinning the spacing would test the wrong thing.

  * `test_end_to_end_matches_hypodd` — the whole chain, prepare -> ph2dt -> hypoDD -> convert,
    compared against the `hypoDD.reloc` hypoDD ships. Skipped when the binaries are not built.

The end-to-end run is IDAT=2 (catalog only) while the shipped answer used catalog + CC. They
therefore should NOT agree exactly; ~36 m is the honest expectation, and the tolerance below is
set from that, not from wishful thinking. Catalog-only also sidesteps this example's non-zero
per-pair OTC, which the pairs contract has no column for (see `readers.read_cc`).
"""
import os
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from hypodd_run import readers, writers, tables, runner        # noqa: E402
from hypodd_run.cli import cmd_prepare, cmd_ph2dt, cmd_hypodd, cmd_convert   # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
EXAMPLE = os.path.join(ROOT, 'HypoDD-2.1b', 'examples', 'example2')
FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures', 'calaveras')
HYPODD_ROOT = os.path.join(ROOT, 'HypoDD-2.1b')

has_example = pytest.mark.skipif(
    not os.path.exists(os.path.join(EXAMPLE, 'Calaveras.pha')),
    reason='HypoDD-2.1b/examples/example2 not present')
has_binaries = pytest.mark.skipif(
    not all(os.path.exists(os.path.join(HYPODD_ROOT, 'src', n, n)) for n in ('ph2dt', 'hypoDD')),
    reason='ph2dt/hypoDD not built — run `make` in HypoDD-2.1b/src')


@has_example
def test_pha_round_trip(tmp_path):
    ev, arr = readers.read_pha(os.path.join(EXAMPLE, 'Calaveras.pha'))
    assert len(ev) == 308 and len(arr) == 13769
    assert set(arr.phase) == {'P', 'S'}
    # hypoDD phase files carry negative pick weights; they must survive untouched.
    assert arr.weight.min() < 0

    ids = {e: int(e) for e in ev.event_id}          # identity: keep the file's own cuspids
    out = str(tmp_path / 'rt.pha')
    n_ev, n_ph = writers.write_pha(ev, arr, ids, out)
    assert (n_ev, n_ph) == (308, 13769)

    ev2, arr2 = readers.read_pha(out)
    for col in ('latitude', 'longitude', 'depth', 'magnitude'):
        assert np.allclose(ev.sort_values('event_id')[col].values,
                           ev2.sort_values('event_id')[col].values, atol=1e-4)
    key = ['event_id', 'station', 'phase']
    a1 = arr.sort_values(key).reset_index(drop=True)
    a2 = arr2.sort_values(key).reset_index(drop=True)
    assert np.allclose(a1.travel_time, a2.travel_time, atol=1e-3)
    assert np.allclose(a1.weight, a2.weight, atol=1e-3)


@has_example
def test_station_dat_without_elevation(tmp_path):
    """This example's station.dat has three columns. Elevation must default, not crash."""
    st = readers.read_station_dat(os.path.join(EXAMPLE, 'station.dat'))
    assert len(st) == 1961
    assert (st.elevation == 0.0).all()
    tables.load_stations(_csv(tmp_path, 'stations.csv', st))


@has_example
def test_cc_otc_is_surfaced_not_dropped():
    """This example relies on a per-pair origin-time correction the pairs contract cannot carry.
    `read_cc` must hand it back so a caller can notice, rather than silently returning zeros."""
    pairs, otc = readers.read_cc(os.path.join(EXAMPLE, 'dt.cc'))
    assert len(pairs) == 99774
    assert sum(1 for v in otc.values() if v != 0.0) > 0.9 * len(otc)


def _csv(tmp_path, name, df):
    p = tmp_path / name
    df.to_csv(p, index=False)
    return str(p)


class _Args:
    run = 'cat'


@has_example
@has_binaries
def test_end_to_end_matches_hypodd(tmp_path):
    ev, arr = readers.read_pha(os.path.join(EXAMPLE, 'Calaveras.pha'))
    st = readers.read_station_dat(os.path.join(EXAMPLE, 'station.dat'))
    run_dir = tmp_path / 'run'
    cfg = {
        'run_dir': str(run_dir),
        'results_dir': str(run_dir / 'results'),
        'hypodd_root': HYPODD_ROOT,
        'inputs': {'events': _csv(tmp_path, 'events.csv', ev),
                   'arrivals': _csv(tmp_path, 'arrivals.csv', arr),
                   'stations': _csv(tmp_path, 'stations.csv', st)},
        'inp_dir': FIXTURES,
        'outputs': {'pha': 'calaveras.pha', 'cc': 'dt.cc'},
        'ph2dt_inp': 'ph2dt.inp',
        'runs': [{'name': 'cat', 'inp': 'hypoDD.inp'}],
    }
    cmd_prepare(cfg, _Args); cmd_ph2dt(cfg, _Args)
    cmd_hypodd(cfg, _Args);  cmd_convert(cfg, _Args)

    ours = pd.read_csv(run_dir / 'results' / 'hypoDD_cat.csv', dtype={'event_id': str})
    assert len(ours) > 290, 'hypoDD discarded an implausible number of events'
    assert ours[['latitude', 'longitude', 'depth']].notna().all().all()

    theirs, _ = writers.read_reloc(os.path.join(EXAMPLE, 'hypoDD.reloc'))
    theirs['event_id'] = theirs.hypodd_id.astype(str)
    m = ours.merge(theirs, on='event_id', suffixes=('_o', '_t'))
    assert len(m) > 290

    lon_km = 111.19 * np.cos(np.radians(m.latitude_o.mean()))
    off = np.hypot((m.longitude_o - m.longitude_t) * lon_km,
                   (m.latitude_o - m.latitude_t) * 111.19)
    # 36 m observed. 200 m leaves room for LSQR ordering noise without admitting a real break.
    assert off.median() < 0.2, f'median offset {off.median() * 1000:.0f} m from hypoDD.reloc'

    # And it must actually have relocated: identical output would also pass the check above.
    moved = np.hypot((ours.set_index('event_id').longitude
                      - ev.set_index('event_id').longitude) * lon_km,
                     (ours.set_index('event_id').latitude
                      - ev.set_index('event_id').latitude) * 111.19).dropna()
    assert moved.median() > 0.01, 'events did not move — did hypoDD actually invert?'
