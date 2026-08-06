"""Contract and writer tests.

`legacy_master_to_tables` lives HERE, not in the package. Its only job is to let the existing
ferndale inputs be replayed through the new path as a regression check. Once Stage F/G emits
the three tables directly it can be deleted, and nothing in the library will notice.
"""
import os
import subprocess
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from hypodd_run import tables, writers                      # noqa: E402
from hypodd_run.tables import ContractError                 # noqa: E402


# ── fixtures ───────────────────────────────────────────────────────────────────────
def _events():
    return pd.DataFrame({
        'event_id': ['a1', 'b2'],
        'origin_time': ['2022-12-19T12:37:34.477Z', '2022-12-19T13:16:26.000Z'],
        'latitude': [40.49131, 40.5], 'longitude': [-124.33816, -124.3],
        'depth': [19.072, 5.0], 'magnitude': [0.78, 1.2]})


def _arrivals():
    return pd.DataFrame({
        'event_id': ['a1', 'a1', 'b2', 'b2'],
        'station': ['KCT', 'KCT', 'KCT', 'B046'],
        'phase': ['P', 'S', 'P', 'S'],
        'travel_time': [4.396, 7.816, 4.394, 8.909]})


def _write(tmp_path, name, df):
    p = tmp_path / name
    df.to_csv(p, index=False)
    return str(p)


# ── the contract refuses what the old code silently repaired ───────────────────────
def test_missing_location_is_an_error_not_a_default(tmp_path):
    """The predecessor substituted (40.5, -124.0) and printed a warning, relocating the event
    from a fabricated origin. That must now fail loudly."""
    ev = _events()
    ev.loc[1, 'latitude'] = None
    with pytest.raises(ContractError, match='latitude'):
        tables.load_events(_write(tmp_path, 'e.csv', ev))


def test_self_pairs_rejected(tmp_path):
    """csv_to_cc emitted `# 1 1` for catalog data because it paired on template_id."""
    pairs = pd.DataFrame({'ev1': ['a1'], 'ev2': ['a1'], 'station': ['KCT'],
                          'phase': ['P'], 'dt_sec': [0.01]})
    with pytest.raises(ContractError, match='self-pairs'):
        tables.load_pairs(_write(tmp_path, 'p.csv', pairs))


def test_duplicate_arrival_rejected(tmp_path):
    arr = pd.concat([_arrivals(), _arrivals().iloc[[0]]])
    with pytest.raises(ContractError, match='duplicate'):
        tables.load_arrivals(_write(tmp_path, 'a.csv', arr))


def test_nonpositive_travel_time_rejected(tmp_path):
    arr = _arrivals()
    arr.loc[0, 'travel_time'] = -1.0
    with pytest.raises(ContractError, match='travel_time'):
        tables.load_arrivals(_write(tmp_path, 'a.csv', arr))


def test_orphan_arrival_rejected(tmp_path):
    ev = tables.load_events(_write(tmp_path, 'e.csv', _events()))
    arr = _arrivals()
    arr.loc[0, 'event_id'] = 'nope'
    with pytest.raises(ContractError, match='absent from events'):
        tables.load_arrivals(_write(tmp_path, 'a.csv', arr), ev)


def test_s_only_station_is_fine(tmp_path):
    """Long form's payoff: the old wide travel_time_p/_s shape made this awkward."""
    ev = tables.load_events(_write(tmp_path, 'e.csv', _events()))
    arr = _arrivals()[lambda d: ~((d.event_id == 'a1') & (d.phase == 'P'))]
    loaded = tables.load_arrivals(_write(tmp_path, 'a.csv', arr), ev)
    assert len(loaded) == 3
    ids = writers.assign_ids(ev)
    n_ev, n_ph = writers.write_pha(ev, loaded, ids, str(tmp_path / 'x.pha'))
    assert (n_ev, n_ph) == (2, 3)


# ── format fidelity ────────────────────────────────────────────────────────────────
def test_pha_matches_hypodd_fixed_format(tmp_path):
    ev = tables.load_events(_write(tmp_path, 'e.csv', _events()))
    arr = tables.load_arrivals(_write(tmp_path, 'a.csv', _arrivals()), ev)
    ids = writers.assign_ids(ev)
    out = str(tmp_path / 'x.pha')
    writers.write_pha(ev, arr, ids, out)
    lines = open(out).read().splitlines()
    # Header field positions must match ncsn2pha.f, which ph2dt's reader assumes.
    assert lines[0] == ('# 2022 12 19 12 37 34.48  40.4913 -124.3382   19.07  0.78  0.00'
                        '  0.00  0.00     100000')
    assert lines[1] == 'KCT        4.396  1.000 P'


def test_cc_payload_is_a_time_and_weight_is_the_cc(tmp_path):
    ev = tables.load_events(_write(tmp_path, 'e.csv', _events()))
    pairs = pd.DataFrame({'ev1': ['a1'], 'ev2': ['b2'], 'station': ['KCT'],
                          'phase': ['P'], 'dt_sec': [-0.003], 'weight': [0.871]})
    p = tables.load_pairs(_write(tmp_path, 'p.csv', pairs), ev)
    ids = writers.assign_ids(ev)
    out = str(tmp_path / 'x.cc')
    n_pair, n_obs = writers.write_cc(p, ids, out)
    assert (n_pair, n_obs) == (1, 1)
    lines = open(out).read().splitlines()
    assert lines[0] == '# 100000 100001 0.000000'
    assert lines[1] == 'KCT     -0.003000 0.871 P'


def test_ids_are_stable_across_calls(tmp_path):
    ev = tables.load_events(_write(tmp_path, 'e.csv', _events()))
    assert writers.assign_ids(ev) == writers.assign_ids(ev.sample(frac=1, random_state=1))


def test_station_gap_is_reported_not_hidden(tmp_path):
    """Arrivals at stations missing from the inventory are dropped silently by ph2dt, so
    `validate` has to say so first."""
    ev = tables.load_events(_write(tmp_path, 'e.csv', _events()))
    arr = tables.load_arrivals(_write(tmp_path, 'a.csv', _arrivals()), ev)
    stations = pd.DataFrame({'station': ['KCT'], 'latitude': [40.47], 'longitude': [-124.33]})
    st = tables.load_stations(_write(tmp_path, 's.csv', stations))
    assert tables.check_stations(arr, st) == ['B046']
    assert 'B046' in tables.summarise(ev, arr, None, st)
